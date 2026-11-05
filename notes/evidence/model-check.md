# Model allow-list, same checks on two models, a dead model and a stalled one

Run on 2026-11-05. The checks and the broken IDs came from `tools/check_models.py`, and every answer is in [model-check.json](model-check.json) and [model-broken.json](model-broken.json). The panel results came from the real Ask and Triage panels, on a production build of the web app, with the API on a separate port.

**Result: if the free model disappears, Ask and Triage fail with a visible error that names the model, and nothing moves to a paid model.** Luna stays in the picker, and a person has to choose it.

## Same checks, free model and Luna at high

The rows supply each right answer, not a model. Each Ask check ran three times. Triage ran on the same ten tickets as [triage-score.md](triage-score.md).

| | `nvidia/nemotron-3-ultra-550b-a55b:free` | `openai/gpt-6-luna`, high |
|---|---|---|
| Reply on time (the rows say no) | 3 of 3 | 3 of 3 |
| Long thread count (the rows say 10) | **0 of 3** | **2 of 3 by eye**, 1 of 3 by the grader |
| Not in the records (phone number) | 3 of 3 | 3 of 3 |
| Needs a lookup (cites an article) | 3 of 3 | 3 of 3 |
| Ask seconds, median / slowest | 15.2 / 73.1 | 5.8 / 17.6 |
| Triage answers that fit the form | 10 of 10 | 10 of 10 |
| Category / priority match stored | 10 / 10 of 10 | 10 / 10 of 10 |
| Team matches the assigned agent / the skills | 5 / 10 of 10 | 5 / 10 of 10 |
| Triage seconds per ticket, average / slowest | 23.1 / 37.0 | 14.2 / 19.1 |
| Ask cost, 12 answers, from each call's own figure | $0 | $0.003247 |
| Model on every Ask call and Triage result | Only this ID | Only this ID |
| Retries needed | 0 | 0 |

- **The two models gave the same category, priority and team on all ten tickets.** As in the earlier score, this set doesn't separate them.
- **The free model said 9 all three times.** That repeats the miss in [long-thread.md](long-thread.md), where it was right 1 time in 5 on this ticket at each setting.
- **Luna missed once too.** It said 9 in round 1, after 5 of 5 in the earlier run, so it is not always right on this ticket.
- **The grader undercounted Luna.** Round 2 says "10 such customer messages", which `said_count` can't read, so the JSON records a fail. The result was corrected by eye here and the grader was left alone, so the rule didn't change after the results.
- **"Needs a lookup" tests that an article was cited, not which one.** Luna's round 3 named KB004 and KB034, and both carry the same title.

## What the cost figures can't show

- **The key's usage figure can't be used.** It rose $0.000859 across the free run and fell $0.039622 across the Luna run. A spend can't be negative. The likely cause is the batch from `tools/measure_triage_cost.py`, on the same key, which finished at 12:42 during the Luna run: its readings show the key at $0.162 and then settling near $0.135. That timing fits, but it wasn't proved.
- **Free Ask cost is proved per call**, at $0 on all 22 calls. Triage cost isn't recorded per call by this tool, so this run has no Triage cost for either model. The earlier run measured $0 and $0.0045 for the same ten tickets.

## Breaking the model ID on purpose

| ID sent | What OpenRouter did | Desk | Calls | Key usage |
|---|---|---|---|---|
| `nvidia/nemotron-3-ultra-550b-a55b-BROKEN:free` | 400, not a valid model ID | 502 `model_not_found`, Ask and Triage | That ID only, once each | No change |
| `openai/gpt-6-luna:free` | 404, and points at the paid slug | 502 `model_not_found`, Ask and Triage | That ID only, once each | No change |

The second row is the closest thing to the free model disappearing. OpenRouter's own error names the paid slug, and the desk does not follow it.

In the real panels, with the broken ID on the free line, both showed "OpenRouter does not offer nvidia/nemotron-3-ultra-550b-a55b-BROKEN:free. The desk did not switch to another model." with `HTTP 502 · model_not_found`. The Ask trace read `calls=0 total=$0.000000`. Settings showed the free line as Model unavailable, Luna as Connected, and Anthropic and OpenAI as Not run.

## A stalled model, before and after

A local stub accepted each model request and never answered. The panel ran with the free model at the real time limits.

| | Before: 90-second read limit, one retry | After: 150-second limit on the whole call |
|---|---|---|
| Triage panel | 180.1 s, "The desk API at http://127.0.0.1:8010 did not answer." `HTTP 502 · api_unreachable` | 153.9 s, "nvidia/nemotron-3-ultra-550b-a55b:free did not finish within 150 seconds." `HTTP 504 · model_timeout` |
| Ask panel | 180.1 s, "The desk did not answer." `desk_unreachable` | 154.9 s, the same message, `HTTP 504 · model_timeout` |

Times include a few seconds between starting the clock and clicking. "Before" is the current code with the new limit switched off, which leaves the old read limit and retry in place.

## What this doesn't show

- **Anthropic and OpenAI are unproven by design.** The checks skip them, the API refuses them with `model_not_run`, and their IDs have never been sent anywhere.
- **The stall came from a stub, not a real provider.** A model that trickles text is covered only by tests.
- **Vercel is unchecked.** A function duration limit under 150 seconds would cut the call first and bring back a blame message.
- **The exact model match relies on today's behaviour.** OpenRouter returned the requested ID on every call here. If it starts returning a different name, the desk will refuse with `wrong_model`.
