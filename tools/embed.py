# /// script
# requires-python = ">=3.12"
# dependencies = ["fastembed>=0.9.1", "psycopg[binary]==3.2.10", "certifi>=2025.1.31"]
# ///
"""Embed every ticket and knowledge article into orion_desk.search_embeddings (plan increment 8).

Embeddings are made locally by api/orion_api/embedding.py (fastembed,
nomic-embed-text-v1.5-Q, 768 dimensions). Ticket text is subject and body;
article text is title and body. Each row keeps the ticket's priority so a
filtered search reads one table. The HNSW index (cosine) is built after the load.

    uv run tools/embed.py             # first build
    uv run tools/embed.py --replace   # drop and rebuild search_embeddings (rerun after a migrate --replace)
"""
import argparse
from pathlib import Path
import sys
import time

from orion_db import load_env, redact, target

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from orion_api.embedding import DIMENSIONS, MODEL, Embedder, as_vector  # noqa: E402

CHUNK = 500
SOURCES = (
    ("ticket", "SELECT ticket_id, priority, subject, body FROM tickets ORDER BY ticket_id"),
    ("article", "SELECT article_id, NULL, title, body FROM knowledge_articles ORDER BY article_id"),
)
CREATE = f"""CREATE TABLE search_embeddings (
    doc_id VARCHAR(80) PRIMARY KEY,
    kind VARCHAR(16) NOT NULL,
    source_id VARCHAR(64) NOT NULL,
    priority VARCHAR(512),
    model VARCHAR(64) NOT NULL,
    embedding VECTOR({DIMENSIONS}) NOT NULL
)"""
INDEXES = (
    "CREATE INDEX search_embeddings_hnsw ON search_embeddings USING hnsw (embedding vector_cosine_ops)",
    "CREATE INDEX search_embeddings_priority ON search_embeddings (priority)",
)


def text(title, body):
    return "\n\n".join(part for part in (title, body) if part)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--replace", action="store_true", help="drop and rebuild search_embeddings if it exists")
    args = parser.parse_args()
    env = load_env()
    with target(env) as db:
        documents = []
        for kind, query in SOURCES:
            for source_id, priority, title, body in db.execute(query).fetchall():
                documents.append((f"{kind}:{source_id}", kind, source_id, priority, text(title, body)))
        expected = {kind: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    for kind, table in (("ticket", "tickets"), ("article", "knowledge_articles"))}
        if db.execute("SELECT to_regclass('search_embeddings')").fetchone()[0]:
            if not args.replace:
                raise FileExistsError("search_embeddings already exists; rerun with --replace to rebuild it")
            db.execute("DROP TABLE search_embeddings")
        db.execute(CREATE)
        db.commit()

        started = time.monotonic()
        embedder = Embedder()
        with db.cursor() as cursor:
            for start in range(0, len(documents), CHUNK):
                batch = documents[start:start + CHUNK]
                vectors = embedder.documents([doc[4] for doc in batch])
                with cursor.copy("COPY search_embeddings (doc_id, kind, source_id, priority, model, embedding) "
                                 "FROM STDIN") as copy:
                    for (doc_id, kind, source_id, priority, _), vector in zip(batch, vectors):
                        copy.write_row((doc_id, kind, source_id, priority, MODEL, as_vector(vector)))
                db.commit()
                print(f"embedded {start + len(batch):>5} / {len(documents)}  ({time.monotonic() - started:.0f} s)",
                      flush=True)
        for statement in INDEXES:
            db.execute(statement)
        db.execute("ANALYZE search_embeddings")
        db.commit()

        counts = dict(db.execute("SELECT kind, COUNT(*) FROM search_embeddings GROUP BY kind").fetchall())
        print(f"\n{'kind':<8} {'source':>7} {'embedded':>9}")
        for kind, total in expected.items():
            print(f"{kind:<8} {total:>7} {counts.get(kind, 0):>9}")
        if counts != expected:
            raise ValueError("Embedded rows do not match the source tables")
        print(f"\nsearch_embeddings ready: {sum(counts.values())} rows, {MODEL}, HNSW (cosine)")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        env = load_env()
        print(f"embedding failed: {type(error).__name__}: {redact(str(error), env)}", file=sys.stderr)
        sys.exit(1)
