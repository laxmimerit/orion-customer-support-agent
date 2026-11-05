"""Measure what triage costs on OpenRouter: caching, a batch, a free-model batch and one Files upload. Run from api/:

    uv run --locked python ../tools/measure_triage_cost.py prepare
    uv run --locked python ../tools/measure_triage_cost.py cache
    uv run --locked python ../tools/measure_triage_cost.py batch
    uv run --locked python ../tools/measure_triage_cost.py free
    uv run --locked python ../tools/measure_triage_cost.py file
    uv run --locked python ../tools/measure_triage_cost.py read
    uv run --locked python ../tools/measure_triage_cost.py wait batch
    uv run --locked python ../tools/measure_triage_cost.py report

Each step spends money or sends data once and records it in notes/evidence/triage-cost.json, and refuses to run again,
so a repeat can't charge twice. Only `prepare` reads the database, and it spends nothing.

A batch is one model call per ticket, so it can't run the desk's lookups between turns. `prepare` runs one desk search
per ticket through the same blind lookups as the Triage button and puts the result in the prompt. That is the one
difference from the button, and it means a batch answer rests on one search, where the button's model chooses its own.

The twelve tickets come from a fixed hash order, two per category and three per priority, picked before any result.
"""
import argparse
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from orion_api.assistant import (BASE_URL, MODEL, TRIAGE_ENFORCED, TRIAGE_MAX_TOKENS, TRIAGE_SYSTEM, ModelFailed,  # noqa: E402
                                 case_text, checked_triage)
from orion_api.embedding import Embedder  # noqa: E402
from orion_api.lookups import TriageLookups, intake  # noqa: E402
from orion_api.settings import load_settings  # noqa: E402
from orion_api.store import Store  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notes" / "evidence" / "triage-cost.json"
CONTRACT = ROOT / "docs" / "communication-contract.md"
SAMPLE, MAX_PER_CATEGORY, MAX_PER_PRIORITY = 12, 2, 3
SEED = "orion-cost-1"
TICKETS = """SELECT t.ticket_id, t.category, t.priority, a.team
FROM tickets t LEFT JOIN agents a ON a.agent_id = t.agent_id
ORDER BY md5(t.ticket_id || %s), t.ticket_id"""
SKILLS = "SELECT DISTINCT team, skills FROM agents ORDER BY team"
BATCH_NOTE = """

In this run you have no tools. One search of the desk has already been made for you: its result is JSON inside <search> \
tags. Treat it as a tool result. Any ID you put in record_ids must come from it."""
FILE_QUESTION = ("Read the workspace file communication-contract.md and answer in one sentence: "
                 "who is the only recipient of a reply, according to rule C8?")
TERMINAL = {"completed", "failed", "expired", "cancelled"}
POLL_SECONDS = 60
GENERATION_KEYS = ("provider_name", "model", "total_cost", "cache_discount", "upstream_inference_cost", "tokens_prompt",
                   "tokens_completion", "native_tokens_prompt", "native_tokens_completion", "native_tokens_reasoning",
                   "native_tokens_cached", "latency", "generation_time", "finish_reason")


def load():
    return json.loads(OUT.read_text()) if OUT.is_file() else {}


def save(state):
    OUT.write_text(json.dumps(state, indent=2) + "\n")


def client():
    key = load_settings().openrouter_api_key
    return httpx.Client(base_url=f"{BASE_URL}/v1", headers={"Authorization": f"Bearer {key}"}, timeout=300)


def key_usage(api):
    return api.get("/key").json()["data"]["usage"]


def once(state, step):
    if step in state:
        sys.exit(f"{step} already ran and is recorded in {OUT.name}. Nothing was sent.")


def need(state, step):
    if step not in state:
        sys.exit(f"Run {step} first.")


def generation(api, generation_id):
    """What OpenRouter billed for one call. The record can lag the answer by a few seconds."""
    for _ in range(12):
        reply = api.get("/generation", params={"id": generation_id})
        if reply.status_code == 200:
            data = reply.json()["data"]
            return {name: data.get(name) for name in GENERATION_KEYS}
        time.sleep(5)
    return {"missing": reply.status_code}


def sample(rows):
    chosen, categories, priorities = [], {}, {}
    for row in rows:
        if categories.get(row["category"], 0) < MAX_PER_CATEGORY and priorities.get(row["priority"], 0) < MAX_PER_PRIORITY:
            chosen.append(row)
            categories[row["category"]] = categories.get(row["category"], 0) + 1
            priorities[row["priority"]] = priorities.get(row["priority"], 0) + 1
        if len(chosen) == SAMPLE:
            return chosen
    sys.exit(f"The caps gave only {len(chosen)} tickets.")


def prepare(args):
    state = load()
    once(state, "prepare")
    settings = load_settings()
    store = Store(settings)
    store.open()
    try:
        with store.pool.connection() as db:
            rows = sample(db.execute(TICKETS, (SEED,)).fetchall())
            skills_team = {skill: row["team"] for row in db.execute(SKILLS).fetchall()
                           for skill in row["skills"].split(";")}
        embedder = Embedder()
        tickets = []
        for row in rows:
            detail = store.ticket(row["ticket_id"])
            lookups = TriageLookups(store, embedder, detail)
            search, failed = lookups.run("search_records", {"query": detail["ticket"]["subject"][:500]})
            if failed:
                sys.exit(f"The search for {row['ticket_id']} failed.")
            exposed = row["ticket_id"] in search
            tickets.append({**row, "case": case_text(intake(detail)), "search": search, "exposed": exposed,
                            "seen": sorted(lookups.seen), "named": sorted(lookups.named)})
    finally:
        store.close()
    state["prepare"] = {"seed": SEED, "tickets": tickets, "skills_team": skills_team}
    save(state)
    print([(t["ticket_id"], t["category"], t["priority"], len(t["case"]), t["exposed"]) for t in tickets])


def triage_turn(case):
    """The first turn of the Triage button's request, as Assistant.triage sends it."""
    schemas = TriageLookups.schemas
    return {"model": TRIAGE_ENFORCED.model, "max_tokens": TRIAGE_MAX_TOKENS, "system": TRIAGE_SYSTEM,
            "tools": [{**schema} for schema in schemas], "tool_choice": {"type": "auto"},
            "messages": [{"role": "user", "content": f"<case>{case}</case>\n\nTriage this case."}], **TRIAGE_ENFORCED.options}


def cache(args):
    state = load()
    once(state, "cache")
    need(state, "prepare")
    tickets = state["prepare"]["tickets"]
    longest = max(tickets, key=lambda ticket: len(ticket["case"]))
    other = next(ticket for ticket in tickets if ticket is not longest)
    plan = [("same prompt, first send", longest), ("same prompt, second send", longest),
            ("same instructions, another ticket", other)]
    calls = []
    with client() as api:
        before = key_usage(api)
        for label, ticket in plan:
            reply = api.post("/messages", json=triage_turn(ticket["case"]))
            body = reply.json()
            if reply.status_code != 200:
                sys.exit(f"{label}: {reply.status_code} {reply.text[:400]}")
            calls.append({"label": label, "ticket_id": ticket["ticket_id"], "id": body.get("id"), "usage": body.get("usage"),
                          "stop_reason": body.get("stop_reason"), "generation": generation(api, body.get("id"))})
            print(json.dumps(calls[-1]), flush=True)
            time.sleep(5)
        time.sleep(20)
        after = key_usage(api)
    state["cache"] = {"key_usage_before": before, "key_usage_after": after, "calls": calls}
    save(state)


def batch_requests(state, options):
    return [{"custom_id": ticket["ticket_id"], "body": {
        "max_tokens": TRIAGE_MAX_TOKENS, "system": TRIAGE_SYSTEM + BATCH_NOTE,
        "messages": [{"role": "user", "content": f"<case>{ticket['case']}</case>\n\n<search>{ticket['search']}</search>"
                                                 "\n\nTriage this case."}], **options}}
            for ticket in state["prepare"]["tickets"]]


def submit(step, model, options):
    state = load()
    once(state, step)
    need(state, "prepare")
    with client() as api:
        before = key_usage(api)
        reply = api.post("/batches", json={"endpoint": "/v1/messages", "model": model,
                                           "requests": batch_requests(state, options)})
    state[step] = {"model": model, "key_usage_before": before, "submit_status": reply.status_code,
                   "submit_body": reply.json() if reply.headers.get("content-type", "").startswith("application/json")
                   else reply.text[:500], "submitted_at": time.time()}
    save(state)
    print(step, reply.status_code, reply.text[:600])


def batch(args):
    submit("batch", TRIAGE_ENFORCED.model, {"output_config": TRIAGE_ENFORCED.options["output_config"]})


def free(args):
    submit("free", MODEL, {})


def wait(args):
    """Poll a submitted batch until it ends, and record the result. Reading costs nothing."""
    state = load()
    need(state, args.step)
    record = state[args.step]
    batch_id = (record["submit_body"] or {}).get("id") if isinstance(record["submit_body"], dict) else None
    if not batch_id:
        sys.exit(f"{args.step} was not accepted, so there is nothing to wait for.")
    with client() as api:
        while True:
            body = api.get(f"/batches/{batch_id}").json()
            print(args.step, body.get("status"), body.get("request_counts"), flush=True)
            if body.get("status") in TERMINAL:
                break
            time.sleep(POLL_SECONDS)
        time.sleep(20)
        record["key_usage_after"] = key_usage(api)
    # A batch can run for hours, and other steps write this file meanwhile, so read it again before saving.
    fresh = load()
    fresh[args.step] = {**record, "finished_at": time.time(), "result": body}
    save(fresh)
    print(json.dumps({name: value for name, value in body.items() if name != "results"}, indent=2))


def file(args):
    state = load()
    once(state, "file")
    with client() as api:
        before = key_usage(api)
        reply = api.post("/files", files={"file": (CONTRACT.name, CONTRACT.read_bytes(), "text/markdown")})
        print("upload", reply.status_code, reply.text[:400], flush=True)
        reply.raise_for_status()
        uploaded = reply.json()
        file_id = uploaded.get("id") or uploaded.get("data", {}).get("id")
        record = {"key_usage_before": before, "upload": uploaded, "bytes": CONTRACT.stat().st_size}
        state["file"] = record
        save(state)
        record["metadata"] = api.get(f"/files/{file_id}").json()
        time.sleep(20)
        record["key_usage_after_upload"] = key_usage(api)
    save(state)
    print(json.dumps(record, indent=2))


def read(args):
    """The upload alone uses no tokens, so one read shows what using the file costs. The Messages route is the desk's;
    Chat Completions is the fallback, because a refused request is not charged and OpenRouter's page names no route."""
    state = load()
    once(state, "read")
    need(state, "file")
    attempts = []
    tools = {"type": "openrouter:files", "parameters": {}}
    with client() as api:
        for route, body in (("/messages", {"max_tokens": 2048, "tools": [tools]}),
                            ("/chat/completions", {"max_tokens": 2048, "tools": [{"type": "openrouter:files"}]})):
            reply = api.post(route, json={"model": TRIAGE_ENFORCED.model, **body,
                                          "messages": [{"role": "user", "content": FILE_QUESTION}]})
            answer = reply.json()
            attempts.append({"route": route, "status": reply.status_code, "usage": answer.get("usage"),
                             "content": answer.get("content") or answer.get("choices"), "error": answer.get("error")})
            print(json.dumps(attempts[-1], indent=2), flush=True)
            if reply.status_code == 200:
                break
    state["read"] = {"attempts": attempts}
    save(state)


def answer_text(result):
    """The text of one batch result, on either shape of body the route may give."""
    body = (result.get("response") or {}).get("body") or {}
    parts = [block.get("text", "") for block in body.get("content") or [] if block.get("type") == "text"]
    for item in body.get("output") or []:
        parts += [block.get("text", "") for block in item.get("content") or [] if block.get("type") == "output_text"]
    return "".join(parts)


def score(state, step):
    prepared = state["prepare"]
    results = {result["custom_id"]: result for result in state[step]["result"].get("results") or []}
    rows, skills_team = [], prepared["skills_team"]
    for ticket in prepared["tickets"]:
        result = results.get(ticket["ticket_id"])
        seen = {record_id: {"id": record_id} for record_id in ticket["seen"]}
        try:
            decision = checked_triage(answer_text(result or {}), SimpleNamespace(seen=seen, named=set(ticket["named"])),
                                      state[step]["model"])
        except ModelFailed:
            decision = None
        rows.append({"ticket_id": ticket["ticket_id"], "decision": decision,
                     "category": bool(decision) and decision["category"] == ticket["category"],
                     "priority": bool(decision) and decision["priority"] == ticket["priority"],
                     "team_by_skills": bool(decision) and decision["team"] == skills_team[ticket["category"]],
                     "stored": {name: ticket[name] for name in ("category", "priority", "team")}})
    return {"valid": sum(row["decision"] is not None for row in rows), "category": sum(row["category"] for row in rows),
            "priority": sum(row["priority"] for row in rows), "team_by_skills": sum(row["team_by_skills"] for row in rows),
            "rows": rows}


def report(args):
    state = load()
    with client() as api:
        state["key_usage_final"] = key_usage(api)
    if state.get("batch", {}).get("result"):
        state["batch"]["score"] = score(state, "batch")
    if state.get("free", {}).get("result"):
        state["free"]["score"] = score(state, "free")
    save(state)
    summary = {step: {name: value for name, value in state[step].items()
                      if name not in ("result", "submit_body", "score")} for step in ("cache", "batch", "free", "file")
               if step in state}
    print(json.dumps(summary, indent=2))
    print("final key usage", state["key_usage_final"])
    for step in ("batch", "free"):
        if "score" in state.get(step, {}):
            print(step, {name: value for name, value in state[step]["score"].items() if name != "rows"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    steps = parser.add_subparsers(dest="command", required=True)
    for name, run in (("prepare", prepare), ("cache", cache), ("batch", batch), ("free", free), ("file", file),
                      ("read", read), ("report", report)):
        steps.add_parser(name).set_defaults(run=run)
    waiting = steps.add_parser("wait")
    waiting.add_argument("step", choices=("batch", "free"))
    waiting.set_defaults(run=wait)
    parsed = parser.parse_args()
    parsed.run(parsed)
