# 0001. Database for the replacement desk

- **Status:** Proposed
- **Date:** 2026-11-02
- **Decision:** Build the replacement on its own PostgreSQL-compatible TiDB Cloud Starter instance, as the separate development database. Leave the legacy MySQL-compatible TiDB database as it is. Do not move production onto it while the service is in preview.

## Context

The handbook asks for two things before any change to the backend or database (backlog M06):

- Keep the existing operational records. Engineering work happens on a separate development database.
- Give a reason and a migration plan. Check identifiers, relationships, dates, nulls and record totals.

The replacement needs a database of its own anyway. The question is which kind:

- **A.** A new PostgreSQL-compatible TiDB instance (the proposal).
- **B.** Stay on the MySQL-compatible TiDB we use today, in a separate database.
- **C.** PostgreSQL somewhere else, on a managed PostgreSQL service outside TiDB Cloud.

## Today's setup

Sources: [`../investigation.md`](../investigation.md) and `../orion-legacy/app/store.py`, plus the table list in `../orion-legacy/database/manifest.json`. No `.env` file was opened, so host, region, plan and credentials are not recorded here.

| Area | Today | Source |
|---|---|---|
| Engine | TiDB with MySQL compatibility. Database `orion_lab`, which the investigation reached through the TiDB connector | investigation.md, Method |
| Driver | `pymysql`. Port from `TIDB_PORT`, default `4000`. `charset="utf8mb4"`, `autocommit=True`, rows as dicts (`DictCursor`) | store.py:9, 15-22 |
| Settings | Environment variables `TIDB_HOST`, `TIDB_USERNAME`, `TIDB_PASSWORD`, `TIDB_DATABASE` (all required), plus optional `TIDB_PORT`, `TIDB_SSL_CA` and `TIDB_TLS` | store.py:10-20 |
| TLS | Verified by default ("TLS verification is enabled for TiDB Cloud"). `TIDB_TLS=off` turns it off for local Docker | store.py:13-14, 20 |
| Timeouts | Connect 10 s, read 15 s, write 15 s | store.py:19 |
| Connections | A new connection for each `with database()` block, closed at the end. No pool | store.py:7-26 |
| Access pattern | Read-only. Every `Store` method is a `SELECT`, and there is "No generic SQL execution endpoint" | store.py:1, 42-114 |
| Tables in `orion_lab` | 15. The app reads 11 of them: `tickets`, `customers`, `agents`, `messages`, `invoices`, `subscriptions`, `plans`, `knowledge_articles`, `company_documents`, `staff_requests`, `lab_metadata`. It never reads the other 4: `ticket_events`, `releases`, `incidents`, `sla_policy` | store.py:42-114; `../orion-legacy/database/manifest.json` (`table_counts`) |
| SQL used | `%s` parameters, `LIMIT … OFFSET`, `JOIN`/`LEFT JOIN`, `COALESCE`, `SUM(CASE …)`, `GROUP BY`, `SELECT *` and `t.*`, `LOWER(…) LIKE LOWER(%s) ESCAPE '!'` | store.py:42-114 |
| Order-sensitive queries | Queue: `created_at DESC, ticket_id`. Priority sort uses the text order of `'P1'`, `'P2'`, …. Customers: `ORDER BY c.company LIMIT 300`. Messages: `created_at, message_id` | store.py:59, 78, 81 |
| Search | Literal substring match on the subject only. The code says this is intended: "Literal, subject-only substring matching is the intended limitation." | store.py:44-50 |
| Data shape | Hours stored to 4 decimals (`3.0000`). Timestamps to the second (`11:31:36`). No nulls among the target and duration columns of the 3525 resolved tickets. `escalated` stored as `0` | investigation.md, F1 and F3 |
| MySQL-only SQL in our checks | The investigation's checks use `TIMESTAMPDIFF(SECOND, …)` | investigation.md, F1 |

Open points from the investigation that also matter here:

- Whether the live desk reads this same data (Unknown 4).
- Whether the connector account is read-only (Unknown 5). Answered: the chat connection uses the SELECT-only reader user; see investigation.md.
- Whether `orion_lab` is a fixed snapshot or still changing (Unknown 7).

## Preview status of PostgreSQL-compatible TiDB

Checked in TiDB's official docs on 2026-11-02 (links under Sources).

- **Public preview.** It started on 2026-10-15 on AWS ([release notes](https://docs.pingcap.com/tidbcloud/tidb-cloud-release-notes/)). No GA date is given.
- **Not for production yet.** "The preview is intended for development and evaluation and is not recommended for production workloads" ([release notes](https://docs.pingcap.com/tidbcloud/tidb-cloud-release-notes/)). The FAQ says "No service-level agreement (SLA) commitment is provided during public preview" and recommends waiting for GA before running production on it ([PG FAQ](https://docs.pingcap.com/tidbcloud/pg-faq/)).
- **Starter only.** Essential, Premium and BYOC don't offer it yet.
- **One region:** AWS `us-east-1`.
- **No private endpoints.** Connections use the public endpoint only.
- **Free during the preview.** The first 10 instances per organisation get 50 GiB of row storage and 500 million RUs a month each. Above the quota, TiDB Cloud "might restrict further usage or suspend service" ([Select a plan](https://docs.pingcap.com/tidbcloud/select-cluster-tier/), [PG FAQ](https://docs.pingcap.com/tidbcloud/pg-faq/)).
- **Not identical to PostgreSQL** ([PostgreSQL compatibility](https://docs.pingcap.com/tidbcloud/postgresql-compatibility/), [Limits](https://docs.pingcap.com/tidbcloud/pg-limits-constraints/)). The differences that touch us:
  - Text without an explicit collation sorts bytewise.
  - No true `SERIALIZABLE`. Requests for it are downgraded to `REPEATABLE READ`.
  - Deferred foreign keys are accepted but checked immediately.
  - `SMALLINT` ranges aren't enforced, and `CHAR(n)` isn't blank-padded.
  - Enums sort by label text.
  - Statements time out after 60 s by default. `NUMERIC` keeps at most 28 fractional digits. Text must be UTF-8.
  - `COPY` supports text and CSV only.
  - The catalog surface is incomplete, and `information_schema.views` is missing.
- **Migration paths.** The only documented ways in are `pg_dump`, `psql` and `\copy` from a PostgreSQL source ([Migrate from PostgreSQL](https://docs.pingcap.com/tidbcloud/import-with-psql/)). The docs give no path from MySQL-compatible TiDB, and backups can't be restored across protocols. We would export CSV from `orion_lab` ourselves and load it with `\copy`.
- **Vectors and full-text.** pgvector-compatible vector search (HNSW only) and full-text search are available. Full-text silently ignores `:*` prefix matching and weight modifiers.

## Options compared

| | A. PostgreSQL-compatible TiDB (separate) | B. Stay on MySQL-compatible TiDB | C. PostgreSQL elsewhere |
|---|---|---|---|
| Readiness | Public preview, no SLA, not for production | What we run today | Depends on the provider. Standard PostgreSQL is mature |
| Keeps legacy records untouched (M06) | Yes, a separate instance | Yes, if we use a separate database or instance | Yes, separate everywhere |
| Driver and SQL changes | `pymysql` → a PostgreSQL driver. Rewrite MySQL-only SQL (`TIMESTAMPDIFF` and others) | None | Same as A |
| Moving the data | MySQL → CSV → `\copy`, which we write and check ourselves | Copy within TiDB (no protocol change) | Same as A, with standard PostgreSQL tooling on the target |
| PostgreSQL fidelity | Partial (see the preview list above) | Not applicable | Full |
| Vendor, console, operations | One vendor (TiDB Cloud) for legacy and replacement | One vendor | A second vendor and account to run |
| Region and network | `us-east-1` only, public endpoint only | Today's region and options (not checked here) | Whatever the provider offers |
| Cost | Free inside the preview quota. Price after GA unknown | Today's plan (not checked here) | Provider pricing |
| Way out | Same wire protocol as C, so moving to C later is mostly connection settings plus re-proving the gaps | Not applicable | Not applicable |

## Decision

Take **A** as the development database for the replacement:

- Create a separate PostgreSQL-compatible TiDB Starter instance in `us-east-1`.
- Load it from a read-only export of `orion_lab`.
- Leave the legacy MySQL-compatible database and the live desk unchanged.

Reasons:

- M06 already requires a separate development database. Making it PostgreSQL-compatible now means we convert the SQL and driver once, while the stakes are low.
- It stays with the vendor we already use, and it's free within the preview quota.
- The PostgreSQL wire protocol leaves **C** open as a fallback with little rework. **B** would keep us on MySQL SQL.

Limits on this decision:

- **No production on A while it's in preview.** Production needs an SLA, and the docs say not to use the preview for production. The replacement's production database gets its own decision record. Revisit when PostgreSQL-compatible TiDB reaches GA. If GA hasn't come when we need production, choose **C**.
- **Fall back to B** if the migration checks below fail in ways we can't work around, such as order, nulls or dates that won't round-trip.

## Consequences

- The replacement uses a PostgreSQL driver and PostgreSQL SQL. `store.py` stays as legacy reference and isn't ported line for line.
- The investigation's check queries need PostgreSQL versions before we can run them against the new database (for example, `TIMESTAMPDIFF(SECOND, a, b)` becomes `EXTRACT(EPOCH FROM b - a)`).
- No pooled or private network path to the database during the preview. The 60 s statement timeout and the free quota become limits we have to watch.
- The vector and full-text features (useful for related cases, B08) are available, but this record doesn't choose a search design. Vector support on the MySQL-compatible side wasn't compared here.

## Unknowns

1. The live desk's region and the latency from it to `us-east-1`. Not checked, because `.env` was out of scope.
2. The exact column types in `orion_lab` (`DATETIME` or `TIMESTAMP`, `DECIMAL` precision, how `escalated` is typed, collations). Only the table counts in `database/manifest.json` were read. The schema in `database/orion-baseline.sql` wasn't.
3. The live row counts. Answered: all 15 tables were counted in `orion_lab` with `COUNT(*)` through the TiDB connector, and every count matches the manifest of baseline `orion-legacy-v1`.
4. Price and limits after GA, and when GA will be.

## What the migration must prove

Each item compares the new PostgreSQL-compatible database with `orion_lab` as exported. It must pass before the replacement relies on the new database.

1. **The source wasn't touched.** Only `SELECT` ran against `orion_lab`. The export used a read-only account, or the account's permissions were checked first (investigation Unknown 5). Record when the export was taken (Unknown 7).
2. **Totals match for all 15 tables in `orion_lab`,** including the 4 the app doesn't read today. At export time, read each table's count from `orion_lab` with `SELECT COUNT(*)` and write it in the table below. Then count each table again in the new database. The two counts must be equal.

   The manifest column holds the counts recorded for baseline `orion-legacy-v1`. They are **not yet confirmed against the database**. If a live count differs from the manifest, the live count is the one the new database must match, and the difference is noted here with its reason.

   | Table | Manifest (`orion-legacy-v1`) | `orion_lab` at export | New database |
   |---|---:|---:|---:|
   | `plans` | 3 | | |
   | `agents` | 9 | | |
   | `customers` | 300 | | |
   | `subscriptions` | 300 | | |
   | `tickets` | 4000 | | |
   | `messages` | 36694 | | |
   | `invoices` | 1800 | | |
   | `ticket_events` | 7525 | | |
   | `releases` | 12 | | |
   | `incidents` | 1 | | |
   | `sla_policy` | 12 | | |
   | `knowledge_articles` | 40 | | |
   | `company_documents` | 5 | | |
   | `staff_requests` | 4 | | |
   | `lab_metadata` | 1 | | |

   Also check that `orion_lab` holds exactly these 15 tables and no others, and check the subtotals the investigation relied on: 3525 resolved tickets, 483 that missed the resolution target, 226 that missed both targets.
3. **Identifiers are unchanged.** Every `ticket_id`, `customer_id`, `agent_id` and `message_id` is present, with the same text, case and no added padding. `T00727` opens exactly T00727 (M01).
4. **Relationships hold.** Every ticket's customer exists. Every message's ticket exists. Every `agent_id` that isn't null exists in `agents`. T00727 still shows customer C0086, agent Clara (A03) and its 5 messages, M007386 to M007390 (M02).
5. **Dates are the same UTC values to the second.** T00727 shows created 2026-06-28 03:34:00, first response 11:31:36 and resolved 2026-06-29 05:08:48. No time-zone shift during export or import, whatever the column type.
6. **Nulls stay null.** Per-column null counts match for every table, and the CSV round trip doesn't turn `NULL` into `''` or `0`. In particular, a missing satisfaction score or first-response time stays not recorded (M07; for example, T01841's satisfaction).
7. **Numbers keep their precision.** Hours keep 4 decimals: 7.9600 and 25.5800 for T00727, and the 3.0000 and 24.0000 targets. Money columns in `invoices` match exactly. The ported checks give the same results: the timestamp-based durations equal the stored hours.
8. **Ordering matches.** The queue (`created_at DESC, ticket_id`), the priority sort, messages (`created_at, message_id`) and especially the customer list (`ORDER BY company`, where Fern Platform 086 is row 163) come back in the same order under the new database's bytewise default. Any difference needs an explicit collation or sort key.
9. **Filters and search behave the same.** Status, priority and owner filters give the same counts. That needs case-sensitive `=` to match today's results. The legacy subject search still finds 265 tickets for "invite" and 0 for "invitation". The `!` escape works for subjects that contain `%`, `_` and `!`.
10. **Types read back correctly.** `escalated`, `reopened_count`, enums or status text, and the `SUM(CASE …)` counts render in the app as they do today (for example, "Escalated No", "Reopened 0").
11. **Text is intact.** All text is valid UTF-8 and byte-for-byte equal to the source, including ticket bodies and message text.
12. **The connection is safe.** It uses TLS with certificate checks, and credentials live outside the repo, as in `store.py` today.
13. **It fits the preview's limits.** Every replacement query finishes inside the 60 s statement timeout, and the data and RU use stay inside the free quota with headroom.
14. **It can be done again.** The export, load and every check above run from a script, so the migration can be repeated end to end from a fresh `orion_lab` export and give the same results.

## Sources

- [`../investigation.md`](../investigation.md), [`../backlog.md`](../backlog.md) (M01, M02, M06, M07, B08), [`../observations.md`](../observations.md)
- `../orion-legacy/app/store.py`
- `../orion-legacy/database/manifest.json` (`table_counts` for baseline `orion-legacy-v1`)
- TiDB Cloud release notes, 2026-10-15 entry: https://docs.pingcap.com/tidbcloud/tidb-cloud-release-notes/
- Select a plan, PostgreSQL-compatible Starter: https://docs.pingcap.com/tidbcloud/select-cluster-tier/
- PostgreSQL-compatible Starter FAQs: https://docs.pingcap.com/tidbcloud/pg-faq/
- PostgreSQL compatibility: https://docs.pingcap.com/tidbcloud/postgresql-compatibility/
- PostgreSQL limits and constraints: https://docs.pingcap.com/tidbcloud/pg-limits-constraints/
- PostgreSQL transactions and COPY: https://docs.pingcap.com/tidbcloud/pg-transactions-copy/
- Migrate from PostgreSQL: https://docs.pingcap.com/tidbcloud/import-with-psql/
