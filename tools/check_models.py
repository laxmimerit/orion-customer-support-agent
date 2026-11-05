"""Run the same checks on every model the desk has run, and break a model ID on purpose. Run from api/:

    uv run --locked python ../tools/check_models.py checks --out ../notes/evidence/model-check.json
    uv run --locked python ../tools/check_models.py broken --out ../notes/evidence/model-broken.json

Purpose: show that switching a line of the allow-list keeps the desk working, and what a dead model looks like.
Needs the database settings and OPENROUTER_API_KEY in the repository's .env. Writes only the output file.

`checks` goes through Assistant.answer and Assistant.triage, the code behind the Ask panel and the Triage button, with
each line's own settings. Luna is paid: about a cent a run. Lines marked Not run are skipped, so they are never called.
Each right answer comes from the rows, not from a model. The change in the key's usage is recorded but proves nothing: it
trails the calls, other callers share the key, and it once fell. Use each call's own cost in the Ask trace instead.
A busy or failed call is tried again, because that says nothing about the model's answer.

`broken` sends a question and a triage to two IDs that do not work, and spends nothing: one OpenRouter never had, and a
`:free` slug for a paid model, where OpenRouter's 404 points at the paid slug. Each must end in `model_not_found` after
one call to that ID and no other.
"""
import argparse
import asyncio
import contextlib
import io
import json
from pathlib import Path
import re
import sys
import time

import httpx2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from orion_api.assistant import BASE_URL, MODELS, Assistant, ModelChoice, ModelFailed, case_text  # noqa: E402
from orion_api.embedding import Embedder  # noqa: E402
from orion_api.lookups import Lookups, TriageLookups, intake  # noqa: E402
from orion_api.server_tools import ServerTools  # noqa: E402
from orion_api.settings import load_settings  # noqa: E402
from orion_api.store import Store  # noqa: E402
from measure_long_thread import WHOLE_THREAD, graded, truth  # noqa: E402
from score_triage import BUSY, SEED, SKILLS, TICKETS, TRIES, WAIT_SECONDS, one, sample, score  # noqa: E402

ROUNDS = 3
SETTLE_SECONDS = 30  # OpenRouter's usage figure trails the call.
SHORT_CASE, LONG_CASE = "T00727", "T00360"
ON_TIME = "Was the first reply within its target? Begin your answer with Yes or No."
NOT_HELD = "What is the customer's phone number?"
NEEDS_LOOKUP = "Which help article best fits this case? Name its ID."
BROKEN_IDS = ("nvidia/nemotron-3-ultra-550b-a55b-BROKEN:free", "openai/gpt-6-luna:free")


def ask_checks(short, long):
    """Each check as (name, case, question, test). A test takes the finished answer and says if it passed."""
    ticket = short["ticket"]
    on_time = float(ticket["first_response_hours"]) <= float(ticket["sla_response_hours"])
    facts = truth(long)
    return [
        ("reply on time", short, ON_TIME, lambda answer: answer["text"].lstrip().lower().startswith("yes" if on_time else "no")),
        ("long thread count", long, WHOLE_THREAD, lambda answer: graded(answer, facts)["count_right"]),
        ("not in the records", short, NOT_HELD, lambda answer: answer["found"] is False),
        ("needs a lookup", short, NEEDS_LOOKUP, lambda answer: any(source["kind"] == "article" for source in answer["sources"])),
    ]


async def ask_once(assistant, store, embedder, detail, question, choice):
    """One question, read the way the panel reads it: text before a lookup is dropped."""
    lookups = Lookups(store, embedder, detail)
    answer = {"text": "", "complete": False, "found": None, "sources": [], "error": None}
    trace = io.StringIO()
    started = time.monotonic()
    with contextlib.redirect_stdout(trace):
        async for raw in assistant.answer(case_text(detail), question, lookups, ServerTools(False), None, choice):
            name, data = raw.split("\n")[:2]
            name, data = name.removeprefix("event: "), json.loads(data.removeprefix("data: "))
            if name == "lookup":
                answer["text"] = ""
            elif name == "delta":
                answer["text"] += data["text"]
            elif name == "done":
                answer.update(complete=data["complete"], found=data["found"], sources=data["sources"])
            elif name == "error":
                answer["error"] = data["error"]["code"]
    line = trace.getvalue()
    answer["seconds"] = round(time.monotonic() - started, 1)
    answer["calls"] = int(re.search(r"calls=(\d+)", line)[1]) if "calls=" in line else 0
    answer["answered_by"] = sorted(set(re.findall(r"gen-\S+ (\S+) via", line)))
    answer["cost"] = (re.search(r"total=(\S+)", line) or [None, None])[1]
    return answer


async def ask_with_retry(*request):
    for attempt in range(1, TRIES + 1):
        answer = await ask_once(*request)
        if answer["error"] not in BUSY or attempt == TRIES:
            return {**answer, "attempts": attempt}
        await asyncio.sleep(WAIT_SECONDS)


async def key_usage(key):
    async with httpx2.AsyncClient(timeout=30) as client:
        reply = await client.get(f"{BASE_URL}/v1/key", headers={"Authorization": f"Bearer {key}"})
    return reply.json()["data"]["usage"]


async def check_line(line, assistant, store, embedder, key, checks, rows, skills_team):
    before = await key_usage(key)
    runs = []
    for name, detail, question, passes in checks:
        for round_number in range(1, ROUNDS + 1):
            answer = await ask_with_retry(assistant, store, embedder, detail, question, line.ask)
            passed = answer["error"] is None and bool(passes(answer))
            runs.append({"check": name, "round": round_number, "passed": passed, **answer})
            print(line.id, name, round_number, "pass" if passed else answer["error"] or "fail", answer["seconds"], flush=True)
    triage = []
    for row in rows:
        triage.append(await one(assistant, store, embedder, row, line.triage))
        print(line.id, "triage", row["ticket_id"], triage[-1]["error"] or "ok", triage[-1]["seconds"], flush=True)
    await asyncio.sleep(SETTLE_SECONDS)
    after = await key_usage(key)
    passed = {name: sum(run["passed"] for run in runs if run["check"] == name) for name, *_ in checks}
    seconds = sorted(run["seconds"] for run in runs)
    return {"line": line.listed(), "ask": runs, "triage": triage,
            "summary": {"ask_passed": passed, "ask_rounds": ROUNDS, "ask_median_seconds": seconds[len(seconds) // 2],
                        "ask_slowest_seconds": seconds[-1], "triage": score(rows, triage, skills_team),
                        "answered_by": sorted({model for run in runs for model in run["answered_by"]}),
                        "key_usage_change": round(after - before, 6)}}


async def checks(out):
    settings = load_settings()
    store = Store(settings)
    store.open()
    try:
        with store.pool.connection() as db:
            rows = sample(db.execute(TICKETS, (SEED,)).fetchall())
            skills_team = {skill: row["team"] for row in db.execute(SKILLS).fetchall() for skill in row["skills"].split(";")}
        questions = ask_checks(store.ticket(SHORT_CASE), store.ticket(LONG_CASE))
        assistant, embedder = Assistant(settings.openrouter_api_key), Embedder()
        results = [await check_line(line, assistant, store, embedder, settings.openrouter_api_key, questions, rows, skills_team)
                   for line in MODELS.values() if line.run]
    finally:
        store.close()
    report = {"tickets": [row["ticket_id"] for row in rows], "not_run": [line.id for line in MODELS.values() if not line.run],
              "lines": results}
    out.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps([result["summary"] for result in results], indent=2))


class Counted(httpx2.AsyncHTTPTransport):
    """Every request that leaves the desk, so `broken` can show exactly what was called."""

    def __init__(self, models):
        super().__init__()
        self.models = models

    async def handle_async_request(self, request):
        self.models.append(json.loads(request.content)["model"])
        return await super().handle_async_request(request)


async def broken(out):
    settings = load_settings()
    store = Store(settings)
    store.open()
    results = []
    try:
        detail = store.ticket(SHORT_CASE)
        before = await key_usage(settings.openrouter_api_key)
        for model in BROKEN_IDS:
            choice = ModelChoice(model)
            sent = []
            assistant = Assistant(settings.openrouter_api_key, lambda sent=sent: httpx2.AsyncClient(transport=Counted(sent)))
            answer = await ask_once(assistant, store, Embedder(), detail, ON_TIME, choice)
            try:
                await assistant.triage(case_text(intake(detail)), TriageLookups(store, Embedder(), detail), choice)
                triage = None
            except ModelFailed as failed:
                triage = failed.body
            results.append({"model": model, "ask_error": answer["error"], "triage_error": triage, "text": answer["text"],
                            "models_called": sent})
            print(json.dumps(results[-1], indent=2), flush=True)
        await asyncio.sleep(SETTLE_SECONDS)
        after = await key_usage(settings.openrouter_api_key)
    finally:
        store.close()
    report = {"results": results, "key_usage_change": round(after - before, 6)}
    out.write_text(json.dumps(report, indent=2) + "\n")
    print("key usage change", report["key_usage_change"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=["checks", "broken"])
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    asyncio.run({"checks": checks, "broken": broken}[arguments.step](arguments.out))
