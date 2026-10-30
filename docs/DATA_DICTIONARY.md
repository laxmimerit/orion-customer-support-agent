# Data dictionary and use

The historical pool has 4,000 tickets, 300 customers, nine agents, three plans and six months of invoices. All dates use UTC. Empty CSV values correspond to null JSON/Parquet values. Do not replace missing observed times with zero.

| File | Grain and key | Use |
|---|---|---|
| customers | One company; customer_id | Segment and plan lookup |
| agents | One fictional agent; agent_id | Team, shift and skills |
| subscriptions | One active subscription per customer | Plan and seat lookup |
| plans | One current plan; plan_id | Current illustrative list price |
| invoices | One customer-month; invoice_id | Recorded historical price and paid/overdue totals |
| tickets | One case; ticket_id | Operational and satisfaction analysis |
| messages | One message; message_id → ticket_id | Ordered conversation history |
| ticket_events | One creation/resolution event | Event chronology |
| sla_policy | Priority × plan | Elapsed-hour targets; no business-hours calendar |
| duplicate_clusters | Cluster membership → historical ticket | Retrieval exercises |
| evaluation_inputs | One held-out case; ticket_id | Model inputs only |
| evaluation_labels | Expected category and priority → evaluation ID | Scoring only; never retrieval context |
| untriaged_backlog | One new case with blank labels | Batch classification exercise |
| releases / incidents | Release or service incident | Timeline context |
| waitlist_daily | Date × acquisition source | Same Part 1 launch input |

Tickets include subject/body, category, priority, status, channel, component, owner, customer, created/first-response/resolved timestamps, response/resolution hours, SLA targets, CSAT, reopening/escalation fields and denormalised customer dimensions. SLA deadlines are creation time plus the individual target. CSAT is collected only on some resolved tickets. Unobserved responses/resolutions are null. Only the first customer message precedes the first recorded agent reply.

## Classification rubric

Category follows the customer's primary issue: invoice/charge → billing; malfunction → bug; instructions → how-to; sign-in/permission → account access; new capability → feature request; service unavailability → outage. Priority follows stated impact, independently of category: P1 entire production team blocked with no workaround; P2 important workflow impaired for multiple people with a costly workaround; P3 limited impact with normal operations continuing; P4 no production impact or deadline. An outage in a test workspace can have lower urgency than an account-access problem blocking production.

## Limits of the simulation

Texts use authored templates and explicit urgency signals. Evaluation IDs and records are disjoint, but vocabulary/templates overlap with history. This is a course integration test, not evidence of real-world model quality. For a production evaluation, collect independently authored and adjudicated cases with ambiguous language. Customer plans remain fixed; historical invoice prices may differ from the current plans table. Security fixtures are isolated untrusted input, never instructions to execute.

## Rebuilding

Run `python3 tools/generate_data.py` for core CSV/JSON and dashboard data; pyarrow is optional for Parquet. The seed is fixed. Hand-authored documents, brand assets and supporting resource tables are versioned files. The SHA-256 manifest identifies this exact release. Follow the on-camera Python/model setup before generating Nomic vectors; no invented embeddings are included.
