"""Shared connections for the ADR 0001 migration tools.

Settings come from the repository's .env (never committed). Both connections
verify TLS certificates. Nothing here prints hosts, users or passwords.
"""
import os
from pathlib import Path
import re
import ssl

import certifi

ROOT = Path(__file__).resolve().parents[1]
SECRET_KEYS = ("TIDB_HOST", "TIDB_USERNAME", "TIDB_PASSWORD", "PG_HOST", "PG_USER", "PG_PASSWORD")


def load_env(path=ROOT / ".env"):
    """Read KEY=VALUE lines. Values already in the environment win."""
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    values.update({key: os.environ[key] for key in values if key in os.environ})
    return values


def redact(text, env):
    """Remove connection details from an error message before it is shown."""
    for key in SECRET_KEYS:
        if env.get(key):
            text = text.replace(env[key], "<" + key.lower() + ">")
    return re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "<address>", text)


def source(env):
    """orion_lab on MySQL-compatible TiDB, through the SELECT-only reader."""
    import pymysql
    context = ssl.create_default_context(cafile=env.get("TIDB_SSL_CA") or certifi.where())
    connection = pymysql.connect(
        host=env["TIDB_HOST"], port=int(env.get("TIDB_PORT", "4000")),
        user=env["TIDB_USERNAME"], password=env["TIDB_PASSWORD"],
        database=env["TIDB_DATABASE"], charset="utf8mb4", autocommit=True,
        connect_timeout=10, read_timeout=120, write_timeout=15, ssl=context,
    )
    with connection.cursor() as cursor:
        # orion_lab's DATETIME values are UTC; pin the session so nothing shifts.
        cursor.execute("SET SESSION time_zone = '+00:00'")
    return connection


def target(env, database=None):
    """The PostgreSQL-compatible TiDB instance (orion_desk unless told otherwise)."""
    import psycopg
    return psycopg.connect(
        host=env["PG_HOST"], port=int(env.get("PG_PORT", "5432")),
        user=env["PG_USER"], password=env["PG_PASSWORD"],
        dbname=database or env["PG_DATABASE"],
        sslmode="verify-full", sslrootcert=env.get("PG_SSL_ROOT_CERT") or certifi.where(),
        connect_timeout=20, options="-c TimeZone=UTC",
    )
