"""Offline portability and behaviour checks; NOT a MySQL/TiDB runtime pass."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
COURSE = ROOT.parent
sys.path.insert(0, str(ROOT))
from app.store import Store
from app import views


def load_dump(connection):
    sql = (ROOT / "database/orion-baseline.sql").read_text()
    sql = re.sub(r"^--.*$", "", sql, flags=re.M)
    sql = re.sub(r"SET (?:NAMES|time_zone)[^;]*;", "", sql)
    sql = sql.replace(" CHARACTER SET utf8mb4 COLLATE utf8mb4_bin", "")
    sql = re.sub(r"CONVERT\((X'[0-9a-f]*') USING utf8mb4\)", r"CAST(\1 AS TEXT)", sql)
    connection.executescript(sql)


class Cursor:
    def __init__(self, connection):
        self.cursor = connection.cursor()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.cursor.close()
    def execute(self, sql, args):
        self.cursor.execute(sql.replace("%s", "?"), args)
    def fetchall(self):
        return [dict(row) for row in self.cursor.fetchall()]


class Connection:
    def __init__(self, raw):
        self.raw = raw
    def cursor(self):
        return Cursor(self.raw)


class BaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = sqlite3.connect(":memory:")
        cls.raw.row_factory = sqlite3.Row
        load_dump(cls.raw)
        cls.store = Store(Connection(cls.raw))

    @classmethod
    def tearDownClass(cls):
        cls.raw.close()

    def test_package_hash_and_counts(self):
        manifest = json.loads((ROOT / "database/manifest.json").read_text())
        sql = ROOT / "database/orion-baseline.sql"
        self.assertEqual(hashlib.sha256(sql.read_bytes()).hexdigest(), manifest["sql_sha256"])
        for name, count in manifest["table_counts"].items():
            self.assertEqual(self.raw.execute('SELECT COUNT(*) FROM "' + name + '"').fetchone()[0], count, name)

    def test_original_source_hashes_unchanged(self):
        if not (COURSE / "orion-course-resources/data").exists():
            self.skipTest("Original instructor provenance package is not part of this source repository")
        manifest = json.loads((ROOT / "database/manifest.json").read_text())
        for name, digest in manifest["source_sha256"].items():
            self.assertEqual(hashlib.sha256((COURSE / name).read_bytes()).hexdigest(), digest)

    def test_ticket_customer_conversation_join(self):
        ticket = self.store.ticket("T00727")
        self.assertEqual(ticket["customer_id"], "C0086")
        self.assertEqual(ticket["subject"], "Invite link expired")
        self.assertEqual(ticket["company"], "Fern Platform 086")
        messages = self.store.messages("T00727")
        self.assertEqual(len(messages), 5)
        self.assertEqual([m["message_id"] for m in messages], ["M007386", "M007387", "M007388", "M007389", "M007390"])

    def test_missing_score_remains_null_and_visible(self):
        ticket = self.store.ticket("T00001")
        self.assertIsNone(ticket["csat"])
        html = views.detail(ticket, self.store.messages("T00001"))
        self.assertIn("Not recorded", html)
        self.assertNotIn("0 / 5", html)

    def test_keyword_search_and_empty_state(self):
        rows, total = self.store.tickets("Invite link expired")
        self.assertGreater(total, 0)
        self.assertTrue(all("invite link expired" in r["subject"].lower() for r in rows))
        rows, total = self.store.tickets("zzzz-no-such-subject-zzzz")
        self.assertEqual(total, 0)
        self.assertIn("No matching tickets", views.queue(rows, total, "", "", 1))

    def test_search_does_not_become_sql_or_wildcard(self):
        for text in ["%' OR 1=1 --", "%", "_", "<script>alert(1)</script>"]:
            rows, total = self.store.tickets(text)
            self.assertEqual(total, 0, text)
        self.assertEqual(self.raw.execute("SELECT COUNT(*) FROM tickets").fetchone()[0], 4000)

    def test_pagination_and_status(self):
        first, total = self.store.tickets()
        second, _ = self.store.tickets(page=2)
        self.assertEqual(total, 4000)
        self.assertEqual(len(first), 40)
        self.assertFalse(set(r["ticket_id"] for r in first) & set(r["ticket_id"] for r in second))
        rows, _ = self.store.tickets(status="resolved")
        self.assertTrue(rows)
        self.assertTrue(all(r["status"] == "resolved" for r in rows))
        rows, total = self.store.tickets(status="in progress")
        self.assertEqual(total, 147)
        self.assertTrue(all(r["status"] == "in progress" for r in rows))

    def test_html_escapes_untrusted_records(self):
        record = dict(self.store.ticket("T00727"))
        record["company"] = '<img src=x onerror="alert(1)">'
        self.assertNotIn('<img src=x', views.detail(record, []))
        self.assertIn("&lt;img", views.detail(record, []))

    def test_combined_filters_sort_and_preserved_page_links(self):
        rows, total = self.store.tickets(status="open", priority="P2", owner="A03")
        self.assertEqual(total, 4)
        self.assertTrue(all(r["status"] == "open" and r["priority"] == "P2" and r["name"] == "Clara" for r in rows))
        oldest, _ = self.store.tickets(sort="oldest")
        self.assertEqual([r["created_at"] for r in oldest], sorted(r["created_at"] for r in oldest))
        ranked, _ = self.store.tickets(sort="priority")
        self.assertTrue(all(r["priority"] == "P1" for r in ranked))
        rows, total = self.store.tickets(status="resolved", priority="P2", owner="A03")
        html = views.queue(rows, total, "", "resolved", 1, {}, self.store.agents(), "P2", "A03", "oldest")
        self.assertIn("priority=P2", html)
        self.assertIn("owner=A03", html)
        self.assertIn("sort=oldest", html)

    def test_customer_context_and_article_drilldown(self):
        customer = self.store.customer("C0086")
        cases = self.store.customer_tickets("C0086")
        invoices = self.store.invoices("C0086")
        subscription = self.store.subscription("C0086")
        self.assertEqual(len(invoices), 6)
        self.assertEqual(subscription["seats"], customer["seats"])
        directory = self.store.customers()
        self.assertEqual(sum(r["case_count"] for r in directory), 4000)
        self.assertEqual(sum(r["active_count"] for r in directory), 475)
        html = views.customer_detail(customer, cases, invoices, subscription)
        self.assertIn("Invoice history", html)
        self.assertIn("T00727", html)
        article = self.store.articles()[0]
        self.assertEqual(self.store.article(article["article_id"]), article)
        self.assertIn(views.e(article["title"]), views.knowledge([article]))
        self.assertIn(views.e(article["body"]), views.knowledge_article(article))
        self.assertIsNone(self.store.article("unknown"))

    def test_company_context_and_evaluation_boundary(self):
        content = views.documents(self.store.documents(), self.store.requests())
        self.assertIn("original application source is outside your access", content)
        self.assertIn("a person must review and approve", content)
        tables = {r[0] for r in self.raw.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn("evaluation_labels", tables)
        self.assertEqual(len(self.store.articles()), 40)

    def test_reports_reconcile_and_no_fabricated_metrics(self):
        counts = self.store.counts()
        self.assertEqual(sum(row["total"] for row in counts), 4000)
        report = views.reports(counts, self.store.metadata()["snapshot_utc"])
        self.assertIn("no date, channel or customer-segment filters", report)
        self.assertNotIn("median", report.lower())

    def test_full_message_bodies_survive_dump_encoding(self):
        if not (COURSE / "orion-course-resources/data/messages.csv").exists():
            self.skipTest("Original instructor provenance data is retained outside this repository")
        import csv
        with (COURSE / "orion-course-resources/data/messages.csv").open() as handle:
            for original in csv.DictReader(handle):
                restored = self.raw.execute("SELECT body FROM messages WHERE message_id=?", (original["message_id"],)).fetchone()[0]
                self.assertEqual(restored, original["body"])


if __name__ == "__main__":
    unittest.main()
