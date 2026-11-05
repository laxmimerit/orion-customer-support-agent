# What triage costs at 4,000 tickets

Run on 2026-11-05 with `tools/measure_triage_cost.py`, each step once. Every response is in [triage-cost.json](triage-cost.json). Token prices are OpenRouter's listing on that day: `openai/gpt-6-luna` is $0.10 in and $0.50 out per million, and half that on its batch endpoint.

## The answer

| Way to run it | Cost per ticket | At 4,000 tickets | Basis |
|---|---|---|---|
| Batch on `openai/gpt-6-luna`, one search put in the prompt | $0.000154 | **$0.61** | Billed for 12 tickets, then multiplied |
| Triage button on `openai/gpt-6-luna`, model runs its own lookups | $0.00045 | **$1.80** | Billed for 10 tickets in [triage-score.md](triage-score.md), then multiplied |
| Batch on the free model | None | **Not possible** | Refused: no batch endpoint |
| Triage button on the free model | $0 | $0, over at least 8 days | Calculated: at least 2 calls a ticket, at 1,000 calls a day |

Nobody has run 4,000 tickets. The two dollar figures are small samples multiplied up, and the batch and the button did not get the same tickets.

## What each run cost

| Run | Result | Billed |
|---|---|---|
| Long prompt, first send (T01531) | 1,374 tokens written to the cache, 0 read | $0.00018605 |
| Same prompt, second send | 1,374 tokens read from the cache | $0.00004404 |
| Same instructions, another ticket (T03018) | 0 read, 1,340 written | $0.00018080 |
| Batch of 12 on `openai/gpt-6-luna` | 12 of 12 done, 17,482 tokens in, 3,883 out, 0 cached | $0.00184485 |
| Batch of 12 on the free model | Refused at once with a 400: no `:batch` endpoint | $0 |
| Upload of `docs/communication-contract.md`, 6,775 bytes | `or_file_0Va3ybZEZ7pHm8kvDF8jkJa1` | $0 (key usage unchanged) |
| **All of it** | | **$0.00225574** |

The third send was added to the request, because 4,000 tickets are 4,000 different prompts. It is what shows the first two don't carry over.

## What the runs show

- **Caching saves money only on a true repeat.** The second send cost 76% less. A different ticket read nothing, because the prompt puts the ticket after the instructions and the shared part seems to fall short of the 1,024-token minimum. That reason is inferred from the sizes, not measured.
- **On a new ticket, caching costs extra.** A cache write bills 1.25 times the input price, so the first send's input cost $0.000172 where uncached input would be $0.000138. This run did not measure how much later turns of the same ticket gain back.
- **The batch was cheap and slow.** Twelve tickets took 4 hours 24 minutes, and OpenRouter allows up to 24 hours. It suits a backlog, and it can't serve the Triage button.
- **The batch held up on the labels.** 12 of 12 fit the form and matched stored category, priority and team by skills. 3 of 12 matched the assigned agent's team. 42 record IDs were kept and none dropped. The caution in [triage-score.md](triage-score.md) applies: these tickets are easy, so 12 of 12 is a ceiling.
- **The batch is not the button.** It can't run lookups between turns, so each ticket got one search on its subject, plus a note in the prompt saying so.
- **An upload saves nothing by itself.** It cost nothing, and OpenRouter says reading a file bills as normal tokens. So a file used on every ticket still costs its tokens on every ticket.

## Before running 4,000

- **One batch of 4,000 would probably be refused.** OpenRouter estimates a batch before accepting it, and held about $0.05 against the key for these twelve. That matches 12 × 16,384 maximum output tokens plus the input ($0.0500). The same sum for 4,000 is about $16.68, over the $12.48 account balance and the key's $2 limit.
- **`max_tokens` can come down.** The longest output here was 781 tokens. At 2,048 the estimate falls to about $2.34, which still needs a higher key limit or several batches.
- **OpenRouter publishes no request cap for a batch.** It answers 413 past an unstated size, so 4,000 in one batch is untested.

## How far the numbers can be trusted

- **Checked:** the batch's billed cost equals its tokens at the listed batch prices, and the three cache calls match the key's usage to the last digit.
- **The key's usage can't confirm the batch.** Other sessions spent on this key during the 4 hours 24 minutes. Its total rose $0.0239 from just before the batch: the batch's $0.0018, about $0.012 for [long-thread.md](long-thread.md), and about $0.010 of other traffic not itemised here. The total also rose with no call from this run.
- **Not measured:** what a model pays to read the uploaded file. The `openrouter:files` tool answered 400 on the Messages route and 403 on Chat Completions ("not currently enabled"), neither of which charged.
- **Cost per ticket varies with ticket length.** These twelve ran 1,388 to 1,518 input tokens. The largest ticket holds about 12,000 characters, so a sample of twelve may read low.

## Left at OpenRouter

- The uploaded file stays until it is deleted: workspace files do not expire.
- The twelve tickets' text and the answers stay in `batch-1793846853-jKgYFvt8YTmvZJdKnS6g` for 30 days, or until that batch is deleted.
