"""/api/search against a fake store and embedder: no network, no model."""
import pytest

from orion_api.embedding import DIMENSIONS, as_vector
from orion_api.store import nearest_query

from .conftest import AGENT, auth


def search(client, query):
    return client.get("/api/search?" + query, headers=auth(AGENT))


@pytest.mark.parametrize("q", ["T00727", "%20T00727%20"])
def test_exact_ticket_id_returns_only_that_ticket(client, fake_store, fake_embedder, q):
    response = search(client, "q=" + q)
    assert response.status_code == 200
    body = response.json()
    assert (body["query"], body["match"]) == ("T00727", "exact_id")
    assert [(item["kind"], item["id"]) for item in body["items"]] == [("ticket", "T00727")]
    assert body["items"][0]["similarity"] is None
    assert fake_embedder.queries == []  # no embedding, no vector search
    assert fake_store.calls == [("exact_ticket", "T00727")]


def test_exact_ticket_id_ignores_the_priority_filter(client, fake_embedder):
    body = search(client, "q=T00727&priority=P1").json()
    assert body["match"] == "exact_id"
    assert [item["id"] for item in body["items"]] == ["T00727"]
    assert fake_embedder.queries == []


@pytest.mark.parametrize("q", ["t00727", "T0072", "T99999"])
def test_inexact_or_unknown_id_falls_back_to_semantic(client, fake_embedder, q):
    body = search(client, "q=" + q).json()
    assert body["match"] == "semantic"
    assert fake_embedder.queries == [q]


def test_semantic_search_embeds_the_query_and_returns_nearest(client, fake_store, fake_embedder):
    body = search(client, "q=invitation%20expired&limit=5").json()
    assert body["match"] == "semantic"
    assert [(item["kind"], item["id"]) for item in body["items"]] == [("ticket", "T00727"), ("article", "KB004")]
    assert body["items"][0]["similarity"] == 0.81
    assert fake_embedder.queries == ["invitation expired"]
    name, vector, priority, limit = fake_store.calls[-1]
    assert (name, len(vector), priority, limit) == ("nearest", DIMENSIONS, None, 5)


def test_priority_filter_reaches_the_store(client, fake_store):
    body = search(client, "q=invitation&priority=P2").json()
    assert [item["id"] for item in body["items"]] == ["T00727"]
    assert fake_store.calls[-1][2:] == ("P2", 10)


@pytest.mark.parametrize("query", ["q=", "q=%20%20", "q=x&priority=P9", "q=x&priority=p1", "q=x&limit=0",
                                   "q=x&limit=51", "q=" + "x" * 501, "priority=P1"])
def test_bad_search_is_a_json_422(client, fake_embedder, query):
    response = search(client, query)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert fake_embedder.queries == []


def test_nearest_query_keeps_the_hnsw_shape():
    plain, filtered = nearest_query(None), nearest_query("P1")
    for text in (plain, filtered):
        assert f"ORDER BY embedding <=> %(vector)s::vector({DIMENSIONS})\n    LIMIT %(limit)s" in text
    assert "WHERE" not in plain.split("LIMIT")[0]
    assert "WHERE priority = %(priority)s" in filtered


def test_vectors_have_the_model_dimension():
    assert as_vector([0.5] * DIMENSIONS).count(",") == DIMENSIONS - 1
    with pytest.raises(ValueError):
        as_vector([0.5] * 3)
