"""Probe actual PostgreSQL-compatible TiDB, isolated from the reference database.

Tiny vectors are labelled capability fixtures, not generated ticket embeddings.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import ssl
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("env_loader", ROOT / "tools/run_tidb_mcp.py")
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)


def connect(database=None):
    import psycopg
    env = loader.load_env(ROOT / ".env.pg")
    if not env.get("PGPASSWORD"):
        raise ValueError("PostgreSQL password is not configured")
    return psycopg.connect(host=env["PGHOST"], port=int(env.get("PGPORT", "5432")),
        user=env["PGUSER"], password=env["PGPASSWORD"], dbname=database or env["PGDATABASE"],
        sslmode="verify-full", sslrootcert="/etc/ssl/cert.pem", autocommit=True, connect_timeout=20)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("connect", "vector"))
    args = parser.parse_args()
    with connect() as db:
        version = db.execute("SELECT version()").fetchone()[0]
        print(json.dumps({"postgres_connection": "pass", "version": version}), flush=True)
        if args.action == "connect":
            return
        row = db.execute("SELECT vector_dims('[1,0,0]'::vector), '[1,0,0]'::vector <=> '[1,0,0]'::vector").fetchone()
        assert row[0] == 3 and abs(float(row[1])) < 1e-9
        # Dedicated, clearly named fixture table. Refuse any pre-existing object.
        db.execute("CREATE TABLE orion_vector_capability_probe (id TEXT PRIMARY KEY, embedding VECTOR(3))")
        db.execute("INSERT INTO orion_vector_capability_probe VALUES ('fixture-a','[1,0,0]'),('fixture-b','[0,1,0]'),('fixture-c','[0.9,0.1,0]')")
        db.execute("CREATE INDEX orion_vector_capability_hnsw ON orion_vector_capability_probe USING hnsw (embedding vector_cosine_ops)")
        found = db.execute("SELECT id FROM orion_vector_capability_probe ORDER BY embedding <=> '[1,0,0]'::vector LIMIT 1").fetchone()[0]
        assert found == "fixture-a"
        plans = {}
        plans["constant"] = [r[0] for r in db.execute("EXPLAIN SELECT id FROM orion_vector_capability_probe ORDER BY embedding <=> '[1,0,0]'::vector LIMIT 2")]
        plans["parameter"] = [r[0] for r in db.execute("EXPLAIN SELECT id FROM orion_vector_capability_probe ORDER BY embedding <=> %s::vector LIMIT 2", ("[1,0,0]",))]
        plans["filtered"] = [r[0] for r in db.execute("EXPLAIN SELECT id FROM orion_vector_capability_probe WHERE id <> 'fixture-b' ORDER BY embedding <=> '[1,0,0]'::vector LIMIT 2")]
        result = {"version": version, "vector_type": "pass", "cosine_operator": "pass", "dimensions": 3,
                  "hnsw_created": True, "nearest_fixture": found, "plans": plans,
                  "scope": "Capability fixtures only; no ticket embeddings or business result claimed"}
        (ROOT / "review/postgres-vector-check.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # PostgreSQL diagnostics can contain usernames/connection details.
        state = getattr(error, "sqlstate", None)
        print(json.dumps({"postgres_check": "failed", "error_class": type(error).__name__, "sqlstate": state}), file=sys.stderr)
        sys.exit(1)
