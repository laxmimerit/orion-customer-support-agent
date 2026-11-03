"""/api/reports against a fake store, and the SQL files themselves: no network, no database."""
import re

import pytest

from orion_api.main import REPORT_ROUTES
from orion_api.store import REPORTS, REPORTS_DIR

from .conftest import ADMIN, AGENT, BACKLOG_ALL, FIRST_REPLY_ALL, auth

ROUTES = [(path, name) for path, name, _, _ in REPORT_ROUTES]


def statements(text):
    body = "\n".join(line.split("--", 1)[0] for line in text.splitlines())
    return [part for part in body.split(";") if part.strip()]


def test_every_sql_file_has_a_route_and_every_route_a_file():
    assert sorted(path.stem for path in REPORTS_DIR.glob("*.sql")) == sorted(name for _, name in ROUTES)
    assert sorted(REPORTS) == sorted(name for _, name in ROUTES)


@pytest.mark.parametrize("name", sorted(REPORTS))
def test_each_report_is_one_read_only_query(name):
    [query] = statements(REPORTS[name])
    assert re.match(r"\s*(SELECT|WITH)\b", query, re.IGNORECASE)
    assert not re.search(r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|GRANT|COPY|CALL|SET)\b",
                         query, re.IGNORECASE)
    assert "%" not in query  # run without parameters; nothing from a request reaches the SQL


@pytest.mark.parametrize("name", sorted(REPORTS))
def test_each_report_has_no_zero_filled_values(name):
    # Missing values are left out of averages and counted, never replaced (M07).
    assert not re.search(r"\b(COALESCE|NULLIF|IFNULL)\b", REPORTS[name], re.IGNORECASE)


@pytest.mark.parametrize("path, name", ROUTES)
def test_each_report_is_served_under_api_reports(client, fake_store, path, name):
    response = client.get(f"/api/reports/{path}", headers=auth(AGENT))
    assert response.status_code == 200
    assert response.json()["report"] == name
    assert fake_store.calls == [("report", name)]


def test_reports_need_a_token_but_not_the_admin_one(client):
    assert client.get("/api/reports/volume").status_code == 401
    assert client.get("/api/reports/volume", headers=auth(ADMIN)).status_code == 200


def test_first_reply_report_keeps_exact_averages_and_counts(client):
    rows = client.get("/api/reports/first-reply", headers=auth(AGENT)).json()["rows"]
    assert rows[1] == {**FIRST_REPLY_ALL, "avg_csat_met": "4.40", "avg_csat_missed": "2.90"}


def test_an_average_over_nothing_stays_null(client):
    unrated = client.get("/api/reports/first-reply", headers=auth(AGENT)).json()["rows"][0]
    assert unrated["priority"] is None
    assert (unrated["avg_csat_met"], unrated["csat_met_counted"], unrated["csat_met_missing"]) == (None, 0, 1)


def test_backlog_dates_are_utc(client):
    [row] = client.get("/api/reports/backlog", headers=auth(AGENT)).json()["rows"]
    assert row["oldest_created_at"] == "2026-01-01T01:53:00Z"
    assert row["avg_age_hours"] == "1953.37"
    assert row["tickets"] == BACKLOG_ALL["tickets"]


def test_docs_show_each_reports_definitions(client):
    paths = client.get("/openapi.json").json()["paths"]
    description = paths["/api/reports/first-reply"]["get"]["description"]
    assert "Met:    first_response_hours <= sla_response_hours" in description
    assert "never counted as zero (M07)" in description
