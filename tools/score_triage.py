"""Score the desk's triage against what orion_desk stores, on two models. Run from api/, after the desk's tests pass:

    uv run --locked python ../tools/score_triage.py --out ../notes/evidence/triage-score.json

Reads the database and calls OpenRouter, and writes only the output file. The second model is paid: under a cent a run.

The ten tickets come from a fixed hash order, so the choice depends on no result and both models get the same ones. A
ticket is taken unless its category already has 2 or its priority 3, which spreads them over the labels. Each triage
runs once, through the same code as the Triage button. An answer outside the form counts as a miss on every field; only
a busy or failed call is tried again, because that says nothing about the model's answer.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from orion_api.assistant import TRIAGE_ENFORCED, TRIAGE_FREE, Assistant, ModelFailed, case_text  # noqa: E402
from orion_api.embedding import Embedder  # noqa: E402
from orion_api.lookups import TriageLookups, intake  # noqa: E402
from orion_api.settings import load_settings  # noqa: E402
from orion_api.store import Store  # noqa: E402

SAMPLE = 10
MAX_PER_CATEGORY, MAX_PER_PRIORITY = 2, 3
SEED = "orion-triage-1"
FIELDS = ("category", "priority", "team")
# The tickets' team is the assigned agent's, so this is a question about who got the ticket. skills_team below asks who
# should have: the team whose agents list the stored category.
TICKETS = """SELECT t.ticket_id, t.category, t.priority, a.team
FROM tickets t LEFT JOIN agents a ON a.agent_id = t.agent_id
ORDER BY md5(t.ticket_id || %s), t.ticket_id"""
SKILLS = "SELECT DISTINCT team, skills FROM agents ORDER BY team"
BUSY = {"model_busy", "model_unavailable"}
TRIES = 6
WAIT_SECONDS = 30


def sample(rows):
    chosen, categories, priorities = [], {}, {}
    for row in rows:
        if categories.get(row["category"], 0) < MAX_PER_CATEGORY and priorities.get(row["priority"], 0) < MAX_PER_PRIORITY:
            chosen.append(row)
            categories[row["category"]] = categories.get(row["category"], 0) + 1
            priorities[row["priority"]] = priorities.get(row["priority"], 0) + 1
        if len(chosen) == SAMPLE:
            break
    return chosen


class Watched(TriageLookups):
    """Records each tool call and whether a result named the open ticket, which only read_ticket should."""

    def __init__(self, *args):
        super().__init__(*args)
        self.calls, self.exposed = [], []

    def run(self, name, arguments):
        text, failed = super().run(name, arguments)
        self.calls.append(name)
        if self.db.ticket_id in text and name != "read_ticket":
            self.exposed.append(name)
        return text, failed


async def one(assistant, store, embedder, row, choice):
    detail = await asyncio.to_thread(store.ticket, row["ticket_id"])
    started = time.monotonic()
    for attempt in range(1, TRIES + 1):
        lookups = Watched(store, embedder, detail)
        try:
            result = await assistant.triage(case_text(intake(detail)), lookups, choice)
            error = None
            break
        except ModelFailed as failed:
            result, error = None, failed.body["code"]
            if error not in BUSY or attempt == TRIES:
                break
            await asyncio.sleep(WAIT_SECONDS)
    return {"ticket_id": row["ticket_id"], "result": result, "error": error, "attempts": attempt,
            "seconds": round(time.monotonic() - started, 1), "tool_calls": lookups.calls, "exposed": lookups.exposed}


async def run_model(assistant, store, embedder, rows, choice):
    runs = []
    for row in rows:
        runs.append(await one(assistant, store, embedder, row, choice))
        print(choice.model, row["ticket_id"], runs[-1]["error"] or "ok", runs[-1]["seconds"], flush=True)
    return runs


def score(rows, runs, skills_team):
    hits = dict.fromkeys(FIELDS, 0)
    skills_hits = 0
    for row, run in zip(rows, runs):
        result = run["result"]
        if result is None:
            continue
        for name in FIELDS:
            hits[name] += result[name] == row[name]
        skills_hits += result["team"] == skills_team[row["category"]]
    return {"tickets": len(rows), "valid": sum(run["result"] is not None for run in runs), **hits,
            "team_by_skills": skills_hits, "dropped_ids": sum(run["result"]["dropped_ids"] for run in runs if run["result"]),
            "tool_calls": sum(len(run["tool_calls"]) for run in runs),
            "exposed": sum(len(run["exposed"]) for run in runs),
            "seconds": round(sum(run["seconds"] for run in runs), 1)}


async def main(out):
    settings = load_settings()
    store = Store(settings)
    store.open()
    try:
        with store.pool.connection() as db:
            rows = sample(db.execute(TICKETS, (SEED,)).fetchall())
            skills_team = {skill: row["team"] for row in db.execute(SKILLS).fetchall()
                           for skill in row["skills"].split(";")}
        assistant, embedder = Assistant(settings.openrouter_api_key), Embedder()
        print("tickets:", [row["ticket_id"] for row in rows], flush=True)
        free, enforced = await asyncio.gather(run_model(assistant, store, embedder, rows, TRIAGE_FREE),
                                              run_model(assistant, store, embedder, rows, TRIAGE_ENFORCED))
    finally:
        store.close()
    report = {"seed": SEED, "tickets": rows, "runs": {TRIAGE_FREE.model: free, TRIAGE_ENFORCED.model: enforced},
              "scores": {TRIAGE_FREE.model: score(rows, free, skills_team),
                         TRIAGE_ENFORCED.model: score(rows, enforced, skills_team)}}
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["scores"], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    asyncio.run(main(parser.parse_args().out))
