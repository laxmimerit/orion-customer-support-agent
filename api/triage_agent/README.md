# Triage agent

**Purpose.** Go through the unresolved queue and propose a category, priority and team for each ticket. A person approves or rejects each proposal. Nothing changes a ticket.

**Reason.** Arun asked for proposals across the queue. The Triage button on the case page does one ticket at a time, and it keeps no record.

**Prerequisites.** `uv`, the `orion_desk_reader` login, an OpenRouter key and `.env.triage-agent` at the repository root:

```
OPENROUTER_API_KEY=...
PG_HOST=...
PG_PORT=...
PG_USER=...        # The read-only login. The agent refuses a login that can write.
PG_PASSWORD=...
PG_DATABASE=...
```

## Is this route supported?

**No. It works, but neither company stands behind it.**

- **Anthropic does not support it.** Its gateway page says it doesn't support routing Claude Code to non-Claude models through any gateway. The Agent SDK runs Claude Code, so that covers this agent. Supported routes are Anthropic's own API, Bedrock, Vertex and Foundry, all with Claude models.
- **OpenRouter documents the connection but guarantees less.** Its guide gives these settings for the Agent SDK, and says the setup is only guaranteed with the Anthropic first-party provider. This agent uses a provider that isn't Anthropic.
- **So an SDK or CLI update can break it without notice.** The SDK is locked in `uv.lock` for that reason. After any update, run the tests in `api/tests/test_triage_agent.py` and one small real run.

The route the desk already uses has less to break: the Anthropic client library pointed at OpenRouter, with the loop written by hand (`Assistant.triage`). It has no CLI between the desk and the model, and the CLI is the part Anthropic's statement covers. It still depends on OpenRouter's compatibility with the Messages API.

## Run it

From `api/`:

```bash
uv run --group agent python -m triage_agent run --tickets 10
```

A run takes the unresolved tickets with no proposal yet, newest first, and stops at `tickets_per_run`. Run it again to carry on. A ticket that failed has no proposal, so the next run tries it again. Expect some: 8 of 73 real attempts failed, all because the model's answer didn't pass the form check. Reasoning written before the form is tolerated, and the form itself is still checked in full.

## Review

These need neither the SDK nor the agent's settings:

```bash
uv run python -m triage_agent list --status pending --changed
```

```bash
uv run python -m triage_agent show T00727
```

```bash
uv run python -m triage_agent approve T00727 --by "Name"
```

```bash
uv run python -m triage_agent reject T00727 --by "Name" --note "Why"
```

- `*` in the list marks a label that differs from the ticket's stored one.
- A decision is final, and it needs a name.
- **Approving records a decision and changes no ticket.** The desk has no write path yet (plan increments 10 and 11), and `.claude/skills/orion-endpoint` holds that line until the creator lifts it.
- **The name is typed, not checked.** Anyone who can run the command or edit the file can write any name. Treat the list as a working record, not an audit log.
- **Stored teams are a weak comparison.** A ticket's stored team is its assigned agent's team, and only 34.8% of tickets sit with the team whose skills match their category (`notes/evidence/triage-score.md`). Expect most `*` to be on team.

The list is `.triage-agent/review.jsonl`, one entry per line, only ever added to. It is ignored by git and readable only by its owner.

## Limits

All are in `agent.toml`.

| Limit | Set to | What happens |
|---|---|---|
| Turns per ticket | 6 | No proposal for that ticket. Tests stop at 6 model calls, but the SDK's counter has read 7 on real tickets |
| Lookups per ticket | 8 | The tools refuse, and the model answers from what it has |
| Time per ticket | 180 s | The CLI is stopped, with no proposal |
| Estimated budget per ticket | $0.25 | No proposal for that ticket |
| Estimated budget per run | $5.00 | The run stops |
| Real spend per run | $0.00 | Any rise in the key's usage stops the run |
| Tickets per run | 25 | The run stops |
| Failures in a row | 3 | The run stops |

### What the budgets mean

**`max_budget_usd` is not money here.** The SDK does not know this model, so it estimates with a price of its own and marks the result `costBasis: unknown`. It charged a free run about $0.08 per ticket on paper, while OpenRouter charged $0. Treat it as a brake on tokens. It is also checked between turns, so a turn in progress runs to its end.

**The real limit is the key's usage on OpenRouter**, read after each ticket, plus a check of the model's listed price before each run. Both act after the fact or before it, so neither can stop a charge in the moment. **The only hard stop on money is a credit limit on the key.** Give the agent its own OpenRouter key with the lowest limit OpenRouter allows.

Another use of the same key during a run, such as the desk's Ask panel, also moves the usage figure, and stops the run. That is another reason for its own key.

## How it stays apart from your setup

| Yours | The agent |
|---|---|
| `~/.claude`, your login, your CLAUDE.md, hooks, plugins, MCP servers | Not read. `HOME` and `CLAUDE_CONFIG_DIR` point at an empty folder made for the run, and `setting_sources=[]` |
| This repository's `.claude`, `CLAUDE.md`, `AGENTS.md`, `.mcp.json` | Not read. The CLI runs in that empty folder |
| `ANTHROPIC_*` and anything else in your shell | Removed before the CLI starts. Only `PATH`, `HOME`, `LANG`, `LC_*`, `TMPDIR` and `TZ` remain |
| The desk's `.env` | Not read. The agent has `.env.triage-agent` and `agent.toml` |
| Owner database login | Not used, and refused if configured |

Set `ANTHROPIC_BASE_URL` nowhere but here: the agent gives it to its own CLI process, so your Claude Code keeps talking to Anthropic. Managed system settings, if a machine has any, still apply to the CLI.

The empty folder is deleted when the run ends, with the CLI's transcripts in it. If a run is killed, the folder stays in `$TMPDIR`.

## What the model can do

It has six read-only tools: `search_records`, `list_articles`, `read_ticket`, `find_customers`, `read_customer` and `read_article`. These are `TriageLookups`, the tools behind the Triage button, so it sees each ticket as it arrived and can't copy the stored labels. They run in the Python process, so the database login never reaches the CLI. It has no shell, no file access, no web and no subagents, and no tool that reaches the review list.

Ticket text goes to OpenRouter and the free model's provider, as it does for the Triage button. The prompt tells the model to ignore instructions inside tickets, but that is a request and not a control. The person reviewing is the control.

## Deployment

`claude-agent-sdk` is in the `agent` dependency group, because its CLI is 321 MB. The deployed API doesn't import this package, and a test holds that.

**Handoff.** Measured results are in `notes/evidence/triage-agent.md`.
