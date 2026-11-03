# Trace: ticket T00727 and account-access first responses

Source: `orion_lab` database, read-only `SELECT` statements only (TiDB MCP `db_query`). Nothing was written to the database.
Date of trace: 2026-11-02. Timestamps are shown exactly as stored. `lab_metadata.snapshot_utc` is `2026-06-30T23:59:59Z`.

## 1. Ticket T00727

```sql
SELECT * FROM orion_lab.tickets WHERE ticket_id = 'T00727' LIMIT 1;
```

| Field | Value |
|---|---|
| ticket_id | T00727 |
| customer_id / agent_id | C0086 / A03 |
| subject | Invite link expired |
| category / component | account access / Identity |
| priority / status / channel | P2 / resolved / web |
| created_at | 2026-06-28 03:34:00 |
| first_response_at | 2026-06-28 11:31:36 |
| resolved_at | 2026-06-29 05:08:48 |
| sla_response_hours / first_response_hours | 3.0000 / 7.9600 |
| sla_resolution_hours / resolution_hours | 24.0000 / 25.5800 |
| csat / reopened_count / escalated | 4 / 0 / 0 |
| sentiment | urgent |
| plan_id / industry / region / company_size | scale / Finance tools / Americas / 11-50 |

body: "Invite link expired. We use the scale plan with 8 seats. Several people cannot complete an important workflow today. We have a temporary workaround, but it takes considerable manual work. Workspace reference C0086; case demo-00727. Please explain the next step and any workaround."

## 2. Customer C0086, joined by customer_id, with ticket count

```sql
SELECT c.*,
       (SELECT COUNT(*) FROM orion_lab.tickets t2 WHERE t2.customer_id = c.customer_id) AS customer_ticket_count
FROM orion_lab.tickets t
JOIN orion_lab.customers c ON c.customer_id = t.customer_id
WHERE t.ticket_id = 'T00727'
LIMIT 1;
```

| Field | Value |
|---|---|
| customer_id | C0086 |
| company | Fern Platform 086 |
| industry / company_size | Finance tools / 11-50 |
| country / region | United States / Americas |
| plan_id / seats | scale / 8 |
| signup_date | 2025-01-09 |
| contact_email | contact086@example.com |
| acquisition_source | search |
| customer_ticket_count | 18 |

## 3. Messages for T00727, by ticket_id, oldest first

```sql
SELECT message_id, ticket_id, created_at, author_role, body
FROM orion_lab.messages
WHERE ticket_id = 'T00727'
ORDER BY created_at ASC, message_id ASC
LIMIT 100;
```

| # | message_id | created_at | author_role | body |
|---|---|---|---|---|
| 1 | M007386 | 2026-06-28 03:34:00 | customer | Same text as the ticket body. |
| 2 | M007387 | 2026-06-28 11:31:36 | agent | Verified the account through the approved recovery flow and confirmed access was restored without sharing credentials. |
| 3 | M007388 | 2026-06-28 17:24:00 | customer | Thank you. Please confirm whether this also applies to our other team. Follow-up 2. |
| 4 | M007389 | 2026-06-28 23:16:24 | agent | Verified the account through the approved recovery flow and confirmed access was restored without sharing credentials. |
| 5 | M007390 | 2026-06-29 05:08:48 | customer | Thank you. Please confirm whether this also applies to our other team. Follow-up 3. |

Observations from sections 1–3:
- Both SLA targets were missed: first response 7.96 h against 3.0 h; resolution 25.58 h against 24.0 h.
- The customer asked twice whether the fix applies to their other team. Both agent replies are the same text and do not answer it.
- `resolved_at` equals the timestamp of the last customer message (M007390). No agent message follows it.
- The first agent message is at exactly `first_response_at`. After that, messages are evenly spaced 5 h 52 m 24 s apart, which looks like generated seed data.

## 4. Average first_response_hours for account access tickets

```sql
SELECT COUNT(*) AS total_tickets,
       COUNT(first_response_hours) AS with_first_response_hours,
       SUM(first_response_hours IS NULL) AS null_first_response_hours,
       SUM(first_response_at IS NULL) AS null_first_response_at,
       AVG(first_response_hours) AS avg_first_response_hours,
       ROUND(AVG(first_response_hours), 2) AS avg_first_response_hours_2dp
FROM orion_lab.tickets
WHERE category = 'account access';
```

| total_tickets | with_first_response_hours | null_first_response_hours | null_first_response_at | avg_first_response_hours |
|---|---|---|---|---|
| 526 | 522 | 4 | 4 | 17.65350575 (17.65) |

- Average first response for account access: **17.65 hours**.
- `AVG()` ignores NULLs, so this is the average over the 522 tickets that have a response, not all 526.

Check that the stored hours match the timestamps:

```sql
SELECT COUNT(*) AS responded_tickets,
       SUM(ABS(first_response_hours - TIMESTAMPDIFF(SECOND, created_at, first_response_at) / 3600) > 0.01) AS hours_mismatch_count
FROM orion_lab.tickets
WHERE category = 'account access' AND first_response_at IS NOT NULL;
```

| responded_tickets | hours_mismatch_count |
|---|---|
| 522 | 0 |

`first_response_hours` agrees with `first_response_at - created_at` on every responded ticket (within 0.01 h).

## 5. Account access tickets with no first response

**4 tickets** have no first response. `first_response_at` and `first_response_hours` are both NULL on the same 4 rows.

```sql
SELECT t.ticket_id, t.customer_id, t.agent_id, t.created_at, t.first_response_at, t.resolved_at,
       t.status, t.priority, t.channel, t.first_response_hours, t.resolution_hours,
       t.sla_response_hours, t.csat, t.reopened_count, t.escalated,
       (SELECT COUNT(*) FROM orion_lab.messages m WHERE m.ticket_id = t.ticket_id) AS message_count,
       (SELECT COUNT(*) FROM orion_lab.messages m WHERE m.ticket_id = t.ticket_id AND m.author_role = 'agent') AS agent_message_count,
       (SELECT COUNT(*) FROM orion_lab.ticket_events e WHERE e.ticket_id = t.ticket_id) AS event_count
FROM orion_lab.tickets t
WHERE t.category = 'account access' AND t.first_response_hours IS NULL
ORDER BY t.created_at
LIMIT 20;
```

| ticket_id | customer | agent | created_at | status | priority | channel | sla_response_hours | messages | agent messages | events |
|---|---|---|---|---|---|---|---|---|---|---|
| T01917 | C0007 | A07 | 2026-06-19 19:27:00 | open | P3 | API | 18 | 1 | 0 | 1 |
| T01839 | C0282 | A02 | 2026-06-27 18:43:00 | pending | P4 | web | 18 | 1 | 0 | 1 |
| T00723 | C0135 | A04 | 2026-06-28 19:13:00 | in progress | P4 | web | 36 | 1 | 0 | 1 |
| T03087 | C0299 | A01 | 2026-06-30 10:46:00 | in progress | P3 | API | 12 | 1 | 0 | 1 |

On all four, `resolved_at`, `resolution_hours` and `csat` are also NULL, `reopened_count` is 0 and `escalated` is 0.

The single message and single event on each:

```sql
SELECT e.ticket_id, e.event_at, e.event_type, m.message_id, m.created_at AS message_created_at, m.author_role
FROM orion_lab.ticket_events e
LEFT JOIN orion_lab.messages m ON m.ticket_id = e.ticket_id
WHERE e.ticket_id IN ('T01917','T01839','T00723','T03087')
ORDER BY e.ticket_id, e.event_at
LIMIT 20;
```

| ticket_id | event_at | event_type | message_id | message created_at | author_role |
|---|---|---|---|---|---|
| T00723 | 2026-06-28 19:13:00 | created | M007361 | 2026-06-28 19:13:00 | customer |
| T01839 | 2026-06-27 18:43:00 | created | M017249 | 2026-06-27 18:43:00 | customer |
| T01917 | 2026-06-19 19:27:00 | created | M017955 | 2026-06-19 19:27:00 | customer |
| T03087 | 2026-06-30 10:46:00 | created | M028518 | 2026-06-30 10:46:00 | customer |

Status breakdown:

```sql
SELECT status, COUNT(*) AS tickets,
       SUM(first_response_at IS NULL) AS no_first_response,
       SUM(resolved_at IS NULL) AS no_resolution
FROM orion_lab.tickets
WHERE category = 'account access'
GROUP BY status
ORDER BY status
LIMIT 20;
```

| status | tickets | no_first_response | no_resolution |
|---|---|---|---|
| in progress | 21 | 2 | 21 |
| open | 20 | 1 | 20 |
| pending | 29 | 1 | 29 |
| resolved | 456 | 0 | 0 |

Time open at the data snapshot:

```sql
SELECT ticket_id, status, priority, created_at, sla_response_hours,
       ROUND(TIMESTAMPDIFF(SECOND, created_at, '2026-06-30 23:59:59') / 3600, 2) AS hours_open_at_snapshot,
       TIMESTAMPDIFF(SECOND, created_at, '2026-06-30 23:59:59') / 3600 > sla_response_hours AS past_response_sla_at_snapshot
FROM orion_lab.tickets
WHERE category = 'account access' AND first_response_at IS NULL
ORDER BY created_at
LIMIT 20;
```

```sql
SELECT baseline_id, snapshot_utc, fictional, scenario FROM orion_lab.lab_metadata LIMIT 5;
```

| ticket_id | sla_response_hours | hours open at snapshot | past response SLA |
|---|---|---|---|
| T01917 | 18 | 268.55 | yes |
| T01839 | 18 | 77.28 | yes |
| T00723 | 36 | 52.78 | yes |
| T03087 | 12 | 13.23 | yes |

## 6. Why those four are empty

The NULLs are real "no response yet" values, not missing or broken data:
- None of the four has an agent message. Each has exactly one message (the customer's opening message) and one `created` event, both at `created_at`. There is nothing to compute a first response from.
- All four are unresolved (open, pending or in progress). Every resolved account-access ticket (456 of 456) has a first response. The NULLs occur only on tickets still in flight at the snapshot.
- `first_response_at` and `first_response_hours` are NULL on the same rows. On the 522 responded tickets the hours match the timestamps exactly, so the NULL is not a calculation gap.

However, each of the four was already past its response SLA at the snapshot (`2026-06-30 23:59:59` UTC). T01917 had waited 268.55 h against an 18 h target. Because `AVG()` drops NULLs, the 17.65 h average covers only tickets that got a reply. It does not count these four unanswered, overdue tickets, so it understates the wait customers actually experienced.
