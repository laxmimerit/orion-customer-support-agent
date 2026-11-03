### Evidence: first-reply target vs satisfaction (orion_lab)

**Question.** For rated tickets, is average satisfaction (CSAT) different when the first reply met the ticket's own response target versus when it missed? How many resolved tickets have no rating?

**Rule.**
- Target is the ticket's own `sla_response_hours`. All 4,000 tickets agree with `sla_policy` for their plan and priority.
- Met means `first_response_hours <= sla_response_hours`, so a reply exactly at the target counts as met. Three tickets sit on the line.
- Time basis: elapsed calendar hours, UTC, as stated in `sla_policy.time_basis`.
- Rated means `csat IS NOT NULL` (1–5). Unrated means `status = 'resolved' AND csat IS NULL`.

**Queries.**
```sql
SELECT priority,
       CASE WHEN first_response_hours <= sla_response_hours THEN 'met' ELSE 'missed' END AS first_reply,
       COUNT(*) AS rated_tickets,
       ROUND(AVG(csat), 2) AS avg_csat
FROM tickets
WHERE csat IS NOT NULL
GROUP BY priority, first_reply
ORDER BY priority, first_reply;

SELECT priority, COUNT(*) AS resolved, SUM(csat IS NULL) AS resolved_unrated
FROM tickets
WHERE status = 'resolved'
GROUP BY priority
ORDER BY priority;
```

**Result.**

| Priority | Met: n | Met: avg CSAT | Missed: n | Missed: avg CSAT | Gap | Resolved | Resolved, no rating |
|---|---|---|---|---|---|---|---|
| P1 | 140 | 4.09 | 73 | 2.68 | 1.41 | 320 | 107 |
| P2 | 320 | 4.28 | 213 | 2.85 | 1.43 | 830 | 297 |
| P3 | 703 | 4.46 | 447 | 2.97 | 1.49 | 1,736 | 586 |
| P4 | 263 | 4.52 | 170 | 2.90 | 1.62 | 639 | 206 |
| All | 1,426 | 4.40 | 903 | 2.90 | 1.50 | 3,525 | 1,196 |

All 2,329 rated tickets are resolved, and none were dropped for missing reply or target data.

**Snapshot.**
- Database `orion_lab`, baseline `orion-legacy-v1`, snapshot taken 2026-06-30 23:59:59 UTC.
- Covers tickets created from 2026-01-01 to 2026-06-30 UTC, 4,000 in total.
- `lab_metadata` marks the dataset as fictional.

**What it does not show.**
- Causation. This is an association only, with no controls for category, channel, agent, plan, escalation or reopen count.
- How unrated tickets would score. About a third of resolved tickets in each priority have no rating, so the averages could shift if those customers differ from the ones who rated.
- Open, pending or in-progress tickets. None of the 475 has a rating.
- Business-hours effects. Hours are calendar hours, not working hours.
- Which part of the experience drove the score. CSAT is recorded once per ticket and may reflect the resolution rather than the first reply.
- An independent check on first-reply times. The value comes from the ticket row because `ticket_events` logs no first-reply event. For 3,976 tickets the hours match `created_at` to `first_response_at` on the same row, and the message thread was checked for one ticket only (T00727).