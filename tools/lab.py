"""Restore/check/reset one learner's MySQL-compatible lab. No Python dependencies.

Uses an existing mysql client, or an existing Docker installation. Does not install tools.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import ssl

ROOT = Path(__file__).resolve().parents[1]


def settings():
    env = os.environ.copy()
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith("#"):
                key, sep, value = line.partition("=")
                if not sep or not re.fullmatch(r"[A-Z_]+", key.strip()):
                    raise ValueError("Invalid .env line")
                env.setdefault(key.strip(), value.strip().strip('\"').strip("'"))
    for target, source in {"MYSQL_HOST": "TIDB_HOST", "MYSQL_TCP_PORT": "TIDB_PORT", "MYSQL_USER": "TIDB_USERNAME", "MYSQL_PWD": "TIDB_PASSWORD", "MYSQL_DATABASE": "TIDB_DATABASE"}.items():
        if env.get(source):
            env.setdefault(target, env[source])
    for key in ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PWD", "MYSQL_DATABASE"):
        if not env.get(key) or env[key].startswith("replace-with-"):
            raise ValueError("Configure " + key + " in your private .env")
    if not re.fullmatch(r"[A-Za-z0-9_]+", env["MYSQL_DATABASE"]):
        raise ValueError("Use an alphanumeric/underscore lab database name")
    return env


def client(env):
    args = ["--no-defaults", "--host=" + env["MYSQL_HOST"], "--port=" + env.get("MYSQL_TCP_PORT", "4000"), "--user=" + env["MYSQL_USER"], "--ssl-mode=VERIFY_IDENTITY", "--default-character-set=utf8mb4", "--batch", "--skip-column-names", env["MYSQL_DATABASE"]]
    if shutil.which("mysql"):
        return ["mysql"] + args
    if shutil.which("docker"):
        # Only env variable names appear in argv; credentials are inherited privately.
        return ["docker", "run", "--rm", "-i"] + [part for key in ("MYSQL_HOST", "MYSQL_TCP_PORT", "MYSQL_USER", "MYSQL_PWD") for part in ("--env", key)] + ["mysql:8.4", "mysql"] + args
    raise RuntimeError("MySQL client or Docker is required; neither is installed. No installation was attempted.")


def execute(env, sql):
    try:
        import pymysql
    except ImportError:
        pymysql = None
    if pymysql is not None:
        try:
            connection = pymysql.connect(host=env["MYSQL_HOST"], port=int(env.get("MYSQL_TCP_PORT", "4000")),
                user=env["MYSQL_USER"], password=env["MYSQL_PWD"], database=env["MYSQL_DATABASE"],
                ssl=ssl.create_default_context(), charset="utf8mb4", autocommit=True,
                connect_timeout=15, read_timeout=90, write_timeout=90)
            result = []
            with connection:
                with connection.cursor() as cursor:
                    # This helper executes our fixed SQL and generated hex-literal seed.
                    # It is not an arbitrary SQL script parser or a public query endpoint.
                    source = re.sub(r"^--.*$", "", sql, flags=re.M)
                    for statement in source.split(";"):
                        if statement.strip():
                            cursor.execute(statement)
                            if cursor.description:
                                result = cursor.fetchall()
            return "\n".join("\t".join(str(value) for value in row) for row in result)
        except Exception:
            raise RuntimeError("Database command failed. Check your private connection settings and database access.") from None
    result = subprocess.run(client(env), input=sql, text=True, capture_output=True, env=env)
    if result.returncode:
        # Do not print database error text, which can contain hosts, usernames or credentials.
        raise RuntimeError("Database command failed. Check your private connection settings and database access.")
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("restore", "check", "reset", "verify-package"))
    parser.add_argument("--confirm", default="")
    options = parser.parse_args()
    manifest = json.loads((ROOT / "database/manifest.json").read_text())
    sql = ROOT / "database/orion-baseline.sql"
    if hashlib.sha256(sql.read_bytes()).hexdigest() != manifest["sql_sha256"]:
        raise ValueError("Baseline SQL checksum mismatch")
    if options.action == "verify-package":
        print("SQL checksum verified. No database connection attempted.")
        return
    env = settings()
    tables = list(manifest["table_counts"])
    if options.action == "restore":
        existing = execute(env, "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE();")
        if existing != "0":
            raise RuntimeError("Restore requires an empty lab database. Nothing was changed.")
        execute(env, sql.read_text())
    if options.action == "reset":
        expected = "RESET_" + env["MYSQL_DATABASE"]
        if options.confirm != expected:
            raise ValueError("Reset requires --confirm " + expected + ". It removes changes from your lab.")
        marker = execute(env, "SELECT baseline_id FROM lab_metadata WHERE baseline_id='orion-legacy-v1';")
        if marker != "orion-legacy-v1":
            raise RuntimeError("Lab identity check failed; nothing was changed")
        names = execute(env, "SELECT table_name FROM information_schema.tables WHERE table_schema=DATABASE();").splitlines()
        if set(names) != set(tables):
            raise RuntimeError("Unexpected tables found. Reset refused; preserve your additional work separately.")
        execute(env, ";\n".join("DROP TABLE `" + t + "`" for t in reversed(tables)) + ";")
        execute(env, sql.read_text())
    for table, expected in manifest["table_counts"].items():
        actual = execute(env, "SELECT COUNT(*) FROM `" + table + "`;")
        if actual != str(expected):
            raise RuntimeError("Record count mismatch: " + table)
    orphan_check = execute(env, "SELECT COUNT(*) FROM messages m LEFT JOIN tickets t ON t.ticket_id=m.ticket_id WHERE t.ticket_id IS NULL;")
    if orphan_check != "0":
        raise RuntimeError("Conversation relationship check failed")
    print("Baseline identity, table counts and conversation relationships verified.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
