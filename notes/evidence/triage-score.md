# Triage scored against stored fields, ten tickets, two models

Run on 2026-11-05 with `tools/score_triage.py`, once per model, with no prompt change after the results. Every answer is in [triage-score.json](triage-score.json).

| | `nvidia/nemotron-3-ultra-550b-a55b:free` | `openai/gpt-6-luna` |
|---|---|---|
| Settings | Form in the prompt only. The model can't be held to a schema | Schema enforced, high effort |
| Answers that fit the form | 10 of 10 | 10 of 10 |
| Category matches stored | 10 of 10 | 10 of 10 |
| Priority matches stored | 10 of 10 | 10 of 10 |
| Team matches the assigned agent's team | 5 of 10 | 5 of 10 |
| Team matches the skills for the stored category | 10 of 10 | 10 of 10 |
| Record IDs kept / dropped | 28 / 0 | 13 / 0 |
| Tool calls | 30 | 27 |
| Seconds per ticket, average | 13.4 | 14.9 |
| Cost of the ten | $0 | $0.0045 |

## What this does and doesn't show

- **It doesn't separate the models.** They gave the same category, priority and team on all ten tickets.
- **These tickets are easy, so 10 of 10 is a ceiling.** The lab data has 35 subjects, each with one category, and four impact sentences, each with one priority, across all 4,000 tickets. The priority scale in the prompt was written after reading those sentences, because the desk records no scale of its own. Real tickets would score lower by an unknown amount.
- **Team can't be scored against stored data.** Tickets are stored with the assigned agent's team, and only 1,392 of 4,000 (34.8%) sit with the team whose agents list that category as a skill. Both models missed the same five tickets, and on each the assigned team differs from the skills.
- **The sample is thin in places.** It has no outage ticket, and one P1. Outage is the only category that is never P3 or P4.
- **The ID filter never fired on a real answer.** No model named an ID that a tool hadn't returned, so only the tests in `api/tests/test_triage.py` prove the filter.
- **A kept ID proves a tool returned it, not that the record supports the triage.**

## How the score was kept honest

- The model saw only the subject, body, channel, customer and the customer's own messages. Stored category, priority, component, targets, agent, status and agents' replies were held back.
- Tools hide the open ticket too. No tool result in either run named it (`exposed` is 0).
- Tickets came from a fixed hash order, picked before any result, capped at 2 per category and 3 per priority. Both models got the same ten.
