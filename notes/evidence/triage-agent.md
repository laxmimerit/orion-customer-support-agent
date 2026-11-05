# Triage agent on the real queue, 73 attempts

Run on 2026-11-05 with `python -m triage_agent run`, in five runs, on `nvidia/nemotron-3-ultra-550b-a55b:free` through OpenRouter with `claude-agent-sdk` 0.2.178. The prompt and the tools are the Triage button's.

| | |
|---|---|
| Queue (unresolved tickets) | 475 |
| Attempts | 73 |
| Proposals on the review list | 65 |
| Tickets with no proposal yet | 410 |
| Failed attempts | 8 of 73 (11%), all `triage_invalid` |
| Real cost, from the key's usage before and after | $0.00 ($0.174473365 both times) |
| The SDK's estimate for the same work | $6.00, about $0.08 per attempt |
| Seconds per attempt, average | 26 |
| Tickets' labels changed by a run | None in any of the five runs (hash of every ticket's labels) |
| Models that answered | Only the free one |
| IDs dropped by the check | 0 |

## Proposals against stored labels

| Label | Same as stored |
|---|---|
| Category | 65 of 65 |
| Priority | 62 of 65. The other three all go from P4 to P3 |
| Team | 22 of 65 |

- **These tickets are easy, as in [triage-score.md](triage-score.md).** The lab data has few subjects and impact sentences, so high agreement here says little about real tickets.
- **Team can't be scored against stored data**, for the reason in that file: a stored team is the assigned agent's team.
- **No proposal has been reviewed.** Agreement with stored labels is not the same as being right.

## The failures

| Runs | Attempts | Failed | What was seen |
|---|---|---|---|
| Before the fix | 53 | 5 | One answer had reasoning before the form. The other four weren't kept |
| After the fix | 20 | 3 | One `reason` was over the 300-character limit. The other two weren't kept |

- **The fix isn't shown to lower the rate.** `form_in` handles the one shape it was written for, and two later attempts failed for reasons not seen. Twenty attempts are too few to compare.
- **Failures don't repeat on a ticket.** All seven failed tickets that were tried again got a proposal. T00875 hasn't been tried again. A failed ticket gets no proposal, and the next run tries it.
- **The Triage button's route scored 10 of 10 on form** ([triage-score.md](triage-score.md)), on ten other tickets. That sample is too small to say this route is worse.

## What the tests with a stand-in for OpenRouter show

The real SDK and CLI ran against a local server that logged each request, in `api/tests/test_triage_agent.py`.

- Every request names the free model and offers exactly the six desk tools.
- The key goes as a bearer token, even with `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL` and `ANTHROPIC_MODEL` set in the parent.
- A fake `~/.claude` with its own CLAUDE.md never reaches the model, and nothing is written to it.
- A `Bash` call from the model doesn't run.
- `max_turns = 6` stopped a ticket at 6 model calls. Over a real run the SDK's counter read 7 on six tickets that finished with a proposal, and calls weren't counted there, so the real limit isn't confirmed to be exact.
- `max_budget_usd` stops between turns, after the response that crossed it.
- A timed-out ticket leaves no CLI process behind.

Ten settings were each removed in turn to prove a test fails without them. Eight failed at once. `dontAsk` and `setting_sources=[]` sit behind other layers, so each now has a direct test on the options.

## Other checks

- **Network:** one real run with a made-up prompt, through a logging proxy, reached `openrouter.ai` and no other host. This sees only traffic that honours the proxy setting.
- **Database:** the agent's login holds no INSERT, UPDATE, DELETE or TRUNCATE on any of the 16 tables. The owner login has them on all 16 and is refused.
- **Free price:** the model's listed price was checked on OpenRouter before each run after the first two.
