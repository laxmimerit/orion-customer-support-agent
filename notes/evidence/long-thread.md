# Effort, model and a shortened thread on the longest case

Run on 2026-11-05 with `tools/measure_long_thread.py`, after Arun said hard tickets get thin answers and long ones get slow. Every answer, its raw usage and its grade are in [long-thread.json](long-thread.json). Answers went through `Assistant.answer` with the desk's tools and limits, called from a script and not through the panel.

The case is T00360: 115 messages and 11,662 characters, the longest by both measures. The median thread is 9 messages and 1,017 characters, and only 10 of 4,000 tickets pass 20 messages.

The question, fixed before any answer: is this case really finished, how many customer messages say the issue is still reproducible, where are the first and last, and did any agent reply change? The rows say 10 messages, first at follow-up 6, last at 56, and one agent reply repeated throughout.

## Effort and model, full thread, five runs each

| | Free, as the desk sends it | Free, medium | Free, high | `openai/gpt-6-luna`, high |
|---|---|---|---|---|
| Seconds, median (range) | 10.5 (7.1–20.0) | 11.5 (7.2–17.6) | 8.6 (6.0–17.6) | 5.0 (3.8–7.6) |
| Prompt tokens | 5,687 | 5,687 | 5,687 | 4,704 |
| Output tokens, median | 973 | 793 | 732 | 405 |
| Of which thinking | 775 | 573 | 543 | 308 |
| Words in the answer, median | 131 | 130 | 117 | 52 |
| Right count of 10 | 1 of 5 | 1 of 5 | 1 of 5 | 5 of 5 |
| Cost per answer | $0 | $0 | $0 | $0.00035 |

- **Effort changed nothing measurable on this question.** Medium and high overlap on time, and high did not think longer. The free model's wrong answers said 9 and left out follow-up 26.
- **The answers were not thin by length.** The free model wrote more than twice the words of gpt-6-luna at every setting. Its answers also used Markdown, which the prompt forbids.
- **gpt-6-luna was faster and right every time** on this ticket.

## The free model's miss belongs to this ticket

At the same setting, free at high effort, the question was also asked once on each of the nine next longest tickets. It gave the right count on all nine. On T00360 it was right 1 time in 9. So this table shows one ticket the free model gets wrong, not that it can't count long threads.

## What the slow answers were doing

- **Time follows what the model writes.** It ran at a steady rate within each batch, about 95 tokens a second in the main run and 60 in the control. Seconds track output tokens (r = 0.64) better than prompt tokens (r = 0.44), over 30 free one-call runs.
- **The two worst answers both used the shell.** T00356 took 143 seconds and T00359 took 77. In each the model ran the shell twice, hit the limit and was cut off, then answered on a second turn. No answer on T00360 used the shell. Those two questions also cost about $0.003 each, so the shell bills about ten times a gpt-6-luna answer on a free model.
- **Nothing reached the panel's 180 seconds, and nothing was cut at 8,192 tokens** in the 58 answers here. In an earlier arithmetic probe one high-effort call did spend all 8,192 on reasoning and return no text.
- **The provider's cache is not the cause.** First-time and repeat full-thread runs in the same window came out alike, at 21.5 and 18.7 seconds median over four runs each.

## Keeping the last 10 messages and summarising the other 105

Free model, high effort, T00360, nine runs of each from two batches:

| | Full thread | Shortened | Change |
|---|---|---|---|
| Case characters | 17,110 | 3,375 | −80% |
| Prompt tokens | 5,687 | 2,809 | −51% |
| Seconds, median | 11.1 | 7.4 | −3.6 |
| Seconds, worst | 39.2 | 11.8 | −27.3 |
| Runs over 20 seconds | 2 of 9 | 0 of 9 | |
| Output tokens, median | 754 | 736 | |
| Right count of 10 | 1 of 9 | 8 of 9 | |

- **The real saving is the long tail.** The median moves a few seconds, and the worst answers stop happening.
- **The summary has a price.** Each one took 6.0 to 12.4 seconds and about 3,400 tokens in and 600 to 1,000 out. The desk keeps nothing between requests, so made per question it costs more time than it saves. Kept and reused, tokens pay back on the second question.
- **On gpt-6-luna it made things worse.** The first prompt fell from 4,704 to 1,862 tokens, but the model went back for the full ticket in 4 of 5 runs. Median time rose from 5.0 to 9.5 seconds, tokens across turns to 7,500, and the five answers cost $0.0023 against $0.0018.
- **The better count flatters the summary.** The summary prompt asks for repeats to be counted with their follow-up numbers, which suits this question, and the summary did the counting. A question about something it dropped would go the other way.
- **Summaries are not reliable on counts.** Three tries gave 53, 52 and 52 agent replies, and 17, 17 and 16 workspace follow-ups. The true agent figure is 52, and the summary used here says 53. One shortened answer ignored the summary and said 2.
- **A question about the latest message came out the same either way**, three runs each. It was faster shortened (3.7 against 8.1 seconds median). One answer in each arm wrongly implied an agent had replied after follow-up 58, though the customer wrote last.

Shortening is not wired into the Ask route. Only `tools/measure_long_thread.py` uses it.

## The two effort fields

Each model obeys one field and ignores the other with no error, measured by thinking tokens on one fixed arithmetic question:

| Median thinking tokens | `reasoning.effort` low / high | `output_config.effort` low / high |
|---|---|---|
| Free model, six runs each | 2,175 / 8,425 | 2,161 / 1,973 |
| gpt-6-luna, four runs each | 256 / 183 | 127 / 340 |

Each arm here used the field its model obeys. `TRIAGE_ENFORCED` already uses the right one for gpt-6-luna.

## What this doesn't show

- It is one question, and mostly one ticket, with five to nine runs an arm. The time ranges overlap widely, so small differences mean nothing.
- The ticket text is templated lab data, which repeats far more than a real thread. Summaries would shrink a real thread less.
- No ordinary short ticket was timed, so the only comparison for "long" is the shortened T00360.
- The free model shares a provider queue, so times depend on the hour. The arms were interleaved to spread that, but the other nine tickets ran in later batches.
- Answers were graded on the count, first and last. The count check is a pattern match, and the T00360 answers were also read by eye. The other nine tickets were not.
- What the shell commands contained was not recorded. To count messages the model may have pasted message text in, which the shell rules forbid.

## What it cost

$0.012 of OpenRouter credit in all, including the probes, on 2026-11-05.
