"""Print one day on the desk: mail, drafts, sends, late cases and handoffs. Run from api/:

    uv run --locked python ../tools/daily_summary.py [--date 2026-11-05]

Reads through the desk's read-only Store and writes nothing. A day is a UTC day, today by default. Late cases are the
count now, aged at the data snapshot as on the Follow-up page, so they don't change with --date. Follow-up drafts aren't
stored, so "Drafts" counts composed replies only.
"""
import argparse
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from orion_api.settings import load_settings  # noqa: E402
from orion_api.store import Store  # noqa: E402


def summary(day, counts):
    return "\n".join((f"Orion desk, {day} (UTC)", f"Mail: {counts['mail']} received", f"Drafts: {counts['drafts']}",
                      f"Sends: {counts['sends']} sent, {counts['failed']} failed", f"Late cases: {counts['late']} now",
                      f"Handoffs: {counts['handoffs']}"))


def main():
    parser = argparse.ArgumentParser(description="One day on the Orion desk")
    parser.add_argument("--date", type=date.fromisoformat, default=datetime.now(UTC).date())
    day = parser.parse_args().date
    start = datetime.combine(day, time.min)
    store = Store(load_settings())
    store.open()
    try:
        print(summary(day, store.day_counts(start, start + timedelta(days=1))))
    finally:
        store.close()


if __name__ == "__main__":
    main()
