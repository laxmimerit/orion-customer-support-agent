# Analytics definitions

All historical charts use the demonstration pool only. The fixed snapshot is 2026-06-30 23:59:59 UTC. A date filter selects tickets by creation date; resolution metrics describe that cohort, not the number of resolutions occurring within the selected dates.

- Ticket volume: count of selected tickets.
- Response time: median observed first-response hours; exclude tickets awaiting a response and show the observed denominator.
- Response SLA met: observed responses within their individual target divided by observed responses. This is not overall SLA compliance; overdue unanswered tickets are shown separately.
- Resolution time: median elapsed hours among resolved selected tickets. Pending tickets are excluded, never zero-filled.
- CSAT: mean observed score among respondents; show response count and coverage.
- Open backlog: tickets without resolved_at at the snapshot. Age is snapshot minus created_at.
- Revenue: invoice totals, not realised cash. Paid and overdue amounts are separate. Do not join invoices directly to ticket rows before aggregation.
- Regional and industry views describe synthetic customer segments. Synthetic patterns are teaching fixtures and not business conclusions.
