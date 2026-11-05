"""The review list: every proposal and every person's decision, as one line each, added to and never rewritten.

It lives in a file of its own, not in orion_desk, because the desk has no writes yet (plan increments 10 and 11).
Approving records a decision here and changes no ticket. Only this module writes the file, and the model has no tool
that reaches it.
"""
from datetime import datetime, UTC
import json
import os
from pathlib import Path

LABELS = ("category", "priority", "team")


class ReviewError(Exception):
    """A decision the list refuses. The message is for the person who tried it."""


def now():
    return datetime.now(UTC).isoformat(timespec="seconds")


def printable(text):
    """Text from a ticket or a model, safe to print: control characters could rewrite what a reviewer's terminal shows."""
    return "".join(character if character.isprintable() else " " for character in str(text))


class ReviewList:
    def __init__(self, path):
        self.path = Path(path)

    def add(self, entry):
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        line = json.dumps({**entry, "at": now()}) + "\n"
        descriptor = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(descriptor, line.encode())  # One write, so a decision made during a run can't land inside a proposal.
        finally:
            os.close(descriptor)

    def entries(self):
        if not self.path.is_file():
            return []
        # Split on \n alone. splitlines() also splits on characters a customer can put in a subject, such as U+2028.
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").split("\n") if line]

    def proposals(self):
        """Each ticket's proposal with its status, in the order they were made."""
        proposals = {}
        for entry in self.entries():
            if entry["type"] == "proposal":
                proposals[entry["ticket_id"]] = {**entry, "status": "pending", "decision": None}
            elif entry["type"] == "decision":
                proposals[entry["ticket_id"]].update(status=entry["decision"], decision=entry)
        return proposals

    def propose(self, run_id, row, outcome):
        result = outcome.result
        self.add({"type": "proposal", "run_id": run_id, "ticket_id": row["ticket_id"], "subject": row["subject"],
                  "ticket_status": row["status"], "current": {label: row[label] for label in LABELS},
                  "proposed": {label: result[label] for label in LABELS}, "reason": result["reason"],
                  "record_ids": result["record_ids"], "dropped_ids": result["dropped_ids"], "model": result["model"],
                  "turns": outcome.turns, "tool_calls": outcome.tool_calls, "estimated_usd": outcome.estimated_usd})

    def decide(self, ticket_id, decision, by, note=None):
        by = (by or "").strip()
        if not by:
            raise ReviewError("A decision needs the name of the person making it.")
        proposal = self.proposals().get(ticket_id)
        if proposal is None:
            raise ReviewError(f"{ticket_id} has no proposal.")
        if proposal["status"] != "pending":
            raise ReviewError(f"{ticket_id} was already {proposal['status']} by {proposal['decision']['by']}.")
        self.add({"type": "decision", "ticket_id": ticket_id, "decision": decision, "by": by, "note": note})


def changed(proposal):
    """The labels this proposal would change. A ticket's stored team is its assigned agent's team."""
    return [label for label in LABELS if proposal["current"][label] != proposal["proposed"][label]]
