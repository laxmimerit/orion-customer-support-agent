"""Run the agent, and review what it proposed. From api/:

    uv run --group agent python -m triage_agent run --tickets 10
    uv run --group agent python -m triage_agent draft T00727 --approver "Name"
    uv run python -m triage_agent list --status pending --changed
    uv run python -m triage_agent show T00727
    uv run python -m triage_agent approve T00727 --by "Name"
    uv run python -m triage_agent reject T00727 --by "Name" --note "Why"

Only `run` and `draft` call the model. Nothing here changes a ticket or sends anything: approving records a person's
decision on the review list, and a draft is printed for a named person to approve.
"""
import argparse
import asyncio
import json
import re
import sys

from .config import REVIEW_FILE, load_config
from .review import LABELS, ReviewError, ReviewList, changed, printable


def positive(text):
    number = int(text)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def ticket_id(text):
    if not re.fullmatch(r"[A-Za-z0-9]{1,32}", text):
        raise argparse.ArgumentTypeError("must be a ticket ID, such as T00727")
    return text


def person(text):
    if not text.strip() or len(text) > 100 or not text.isprintable():
        raise argparse.ArgumentTypeError("must be a person's name")
    return text.strip()


def draft(_, arguments):
    from .drafts import run_draft  # Here, as with `run`.
    outcome = asyncio.run(run_draft(load_config(needs_database=False), arguments.ticket_id, arguments.approver))
    if outcome.text is None:
        sys.exit(f"No draft for {arguments.ticket_id}: {outcome.error}")
    print(outcome.text)


def run(review, arguments):
    from .agent import run_queue  # Here, so reviewing needs neither the SDK nor the agent's settings.
    summary = asyncio.run(run_queue(load_config(), review, arguments.tickets))
    print(json.dumps(summary, indent=2))
    if not summary["tickets_unchanged"]:
        sys.exit("The tickets' labels changed during this run. Check who else was writing.")


def show_list(review, arguments):
    proposals = [proposal for proposal in review.proposals().values()
                 if arguments.status in ("all", proposal["status"]) and (changed(proposal) or not arguments.changed)]
    print(f"{'ticket':8} {'status':9} {'category':16} {'priority':9} team")
    for proposal in proposals:
        proposed, moved = proposal["proposed"], changed(proposal)
        cells = {label: printable(proposed[label]) + ("*" if label in moved else "") for label in LABELS}
        print(f"{proposal['ticket_id']:8} {proposal['status']:9} {cells['category']:16} {cells['priority']:9} {cells['team']}")
    print(f"{len(proposals)} shown. * differs from the ticket's stored label.")


def show_one(review, arguments):
    proposal = review.proposals().get(arguments.ticket_id)
    if proposal is None:
        sys.exit(f"{arguments.ticket_id} has no proposal.")
    print(f"{proposal['ticket_id']}  {printable(proposal['subject'])}  ({proposal['status']})")
    for label in LABELS:
        print(f"  {label:9} {printable(proposal['current'][label])} -> {printable(proposal['proposed'][label])}")
    print(f"  reason    {printable(proposal['reason'])}")
    print(f"  records   {printable(', '.join(proposal['record_ids']) or 'none')}")
    print(f"  model     {printable(proposal['model'])}, {proposal['turns']} turns, {proposal['tool_calls']} lookups")
    if proposal["decision"]:
        print(f"  decided   {proposal['status']} by {printable(proposal['decision']['by'])}")
        if proposal["decision"]["note"]:
            print(f"  note      {printable(proposal['decision']['note'])}")


def decide(review, arguments):
    review.decide(arguments.ticket_id, {"approve": "approved", "reject": "rejected"}[arguments.command], arguments.by,
                  arguments.note)
    print(f"{arguments.ticket_id} {arguments.command} recorded. No ticket was changed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run").add_argument("--tickets", type=positive, help="At most this many, within tickets_per_run")
    listing = commands.add_parser("list")
    listing.add_argument("--status", choices=("pending", "approved", "rejected", "all"), default="pending")
    listing.add_argument("--changed", action="store_true", help="Only proposals that differ from the stored labels")
    drafting = commands.add_parser("draft", help="Draft a reply through the desk's MCP route. Nothing is sent")
    drafting.add_argument("ticket_id", type=ticket_id)
    drafting.add_argument("--approver", type=person, required=True, help="The person who will approve the draft")
    commands.add_parser("show").add_argument("ticket_id")
    for name in ("approve", "reject"):
        command = commands.add_parser(name)
        command.add_argument("ticket_id")
        command.add_argument("--by", required=True, help="The name of the person deciding")
        command.add_argument("--note")
    arguments = parser.parse_args()
    actions = {"run": run, "draft": draft, "list": show_list, "show": show_one, "approve": decide, "reject": decide}
    try:
        actions[arguments.command](ReviewList(REVIEW_FILE), arguments)
    except ReviewError as refused:
        sys.exit(printable(refused))


if __name__ == "__main__":
    main()
