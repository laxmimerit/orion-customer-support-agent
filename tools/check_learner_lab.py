"""Test restore/reset using the actual learner helper on an isolated database."""
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from live_database import connection, helper

env = helper.load_env(ROOT / ".env")
name = "orion_lab_validation"
with connection(env, select=False) as db:
    with db.cursor() as cursor:
        cursor.execute("CREATE DATABASE IF NOT EXISTS `orion_lab_validation` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin")
        cursor.execute("SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema=%s", (name,))
        if cursor.fetchone()["n"]:
            raise SystemExit("Validation database is not empty; refusing to overwrite")
os.environ.update(env)
os.environ["TIDB_DATABASE"] = name
spec = importlib.util.spec_from_file_location("learner_lab", ROOT.parent / "orion-environment/tools/lab.py")
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)
sys.argv = ["lab.py", "restore"]
lab.main()
print("Isolated learner restore passed", flush=True)
sys.argv = ["lab.py", "reset", "--confirm", "WRONG_DATABASE"]
try:
    lab.main()
    raise AssertionError("Wrong confirmation was accepted")
except ValueError:
    print("Wrong reset confirmation refused", flush=True)
values = dict(env, TIDB_DATABASE=name)
with connection(values) as db:
    with db.cursor() as cursor:
        cursor.execute("UPDATE tickets SET subject=%s WHERE ticket_id='T00727'", ("Temporary reset-test change",))
sys.argv = ["lab.py", "reset", "--confirm", "RESET_" + name]
lab.main()
with connection(values) as db:
    with db.cursor() as cursor:
        cursor.execute("SELECT subject FROM tickets WHERE ticket_id='T00727'")
        assert cursor.fetchone()["subject"] == "Invite link expired"
report = {"database": name, "isolated": True, "learner_restore": "pass", "wrong_confirmation": "refused", "reset_restores_changed_record": "pass", "shared_reference_modified": False}
(ROOT / "review/learner-lab-check.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report), flush=True)
