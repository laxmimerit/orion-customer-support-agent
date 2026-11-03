# Investigation: newest resolved ticket that missed both service targets

Question: which resolved ticket, created most recently, missed both its response target and its resolution target, and what does its page show?

Answer: **T00727 "Invite link expired"**, created 28 Jun 2026 03:34 UTC, for Fern Platform 086 (C0086). Its first response took 7.96 hours against a 3-hour target, and resolution took 25.58 hours against a 24-hour target. Its page flags only the response miss.

## Method

- Code read in `orion-legacy` at commit `a1740ed` (branch `orion-legacy`, clean): `app/web.py`, `app/views.py`, `app/store.py`, `app/templates/base.html`. The `.env` file was not opened.
- Data: read-only `SELECT` queries on the `orion_lab` database through the TiDB connector (`SELECT DATABASE()` returned `orion_lab`). Nothing was written or changed.
- Live page: you opened T00727 on the live desk (https://orion-legacy.vercel.app, per [observations.md](observations.md)) on 2026-11-02 and confirmed it matches the description below.
- "Missed" means taking longer than the target (`>`). This matches the page, which counts a response as met when `first_response_hours <= sla_response_hours` (`app/views.py:91`).

## Findings

### F1. T00727 is the newest resolved ticket that missed both targets

Query:

```sql
SELECT ticket_id, created_at, sla_response_hours, first_response_hours,
       sla_resolution_hours, resolution_hours
FROM orion_lab.tickets
WHERE status = 'resolved'
  AND first_response_hours > sla_response_hours
  AND resolution_hours > sla_resolution_hours
ORDER BY created_at DESC, ticket_id
LIMIT 5;
```

Result (first two rows):

| ticket_id | created_at | response target | first response | resolution target | resolution time |
|---|---|---|---|---|---|
| T00727 | 2026-06-28 03:34:00 | 3.0000 | 7.9600 | 24.0000 | 25.5800 |
| T01792 | 2026-06-27 12:40:00 | 4.0000 | 5.5700 | 32.0000 | 39.2700 |

Supporting checks:

- No other resolved ticket has the same creation time: `SELECT COUNT(*) FROM orion_lab.tickets WHERE status='resolved' AND created_at='2026-06-28 03:34:00'` returned `1`.
- No resolved ticket is missing a target or a duration, so none drop out of the comparison: the null count over `first_response_hours`, `sla_response_hours`, `resolution_hours` and `sla_resolution_hours` was `0` of `3525` resolved tickets. No status values differed only by case or spacing (`odd_status = 0`).
- The raw timestamps give the same answer. Rerunning the query with `first_response_at > created_at + target` and `resolved_at > created_at + target` returned T00727 first and T01792 second.
- The stored hours match the timestamps exactly: `TIMESTAMPDIFF(SECOND, created_at, first_response_at)/3600 = 7.9600` and `TIMESTAMPDIFF(SECOND, created_at, resolved_at)/3600 = 25.5800`.

### F2. The ticket page flags a missed response but never a missed resolution

Code, `app/views.py:90-92`:

```python
if t.get('first_response_hours') is not None and t.get('sla_response_hours') is not None:
    met = float(t['first_response_hours']) <= float(t['sla_response_hours'])
    service = '<p class="service-outcome ' + ('met' if met else 'missed') + '">Response target ' + ('met' if met else 'missed') + '</p>' + service
```

No similar check exists for the resolution target. Resolution hours appear only as plain values (`app/views.py:89`).

Page: you confirmed that T00727's live page shows "Response target missed" and no resolution banner.

Size of the gap (query on `orion_lab.tickets WHERE status='resolved'`):

| Measure | Tickets |
|---|---|
| Resolved tickets | 3525 |
| Missed the resolution target | 483 |
| Missed both targets (no resolution flag shown) | 226 |
| Missed only the resolution target (no flag at all on the page) | 257 |

### F3. What T00727's page shows

You confirmed that the live page matches each item below.

| Page area | Shows | Evidence |
|---|---|---|
| Browser tab | `T00727 · Invite link expired — Orion Support Desk` | `app/web.py:77` builds the title from `ticket_id` and `subject`; `app/templates/base.html:6` adds the suffix |
| Badges | Resolved · P2 · account access · Identity · Via web | `app/views.py:86`; data: `status=resolved`, `priority=P2`, `category=account access`, `component=Identity`, `channel=web` |
| Request summary | "Invite link expired. We use the scale plan with 8 seats. …Workspace reference C0086; case demo-00727. Please explain the next step and any workaround." | `app/views.py:100` renders `t['body']`; data: `tickets.body` for T00727 |
| Case ownership | Clara · Customer success · Created 28 Jun 2026, 03:34 · First response 28 Jun 2026, 11:31 · Resolved 29 Jun 2026, 05:08 · Reopened 0 · Escalated No | `app/views.py:87`; data: `agent_id=A03` → `agents.name=Clara`, `team=Customer success`; `reopened_count=0`, `escalated=0` |
| Customer account | Fern Platform 086 (links to `/customers/C0086`) · C0086 · Scale · 8 seats · Americas · contact086@example.com | `app/views.py:88`; data from the join in `app/store.py:71-75` |
| Service levels | "Response target missed" · Response target 3 hours · First response 7.96 hours · Resolution target 24 hours · Resolution time 25.58 hours · Satisfaction 4 / 5 | `app/views.py:89-92`; `missing()` at `app/views.py:12-14` removes trailing zeros (`3.0000` → `3`) |
| Conversation | "5 messages": customer 03:34, agent 11:31, customer 17:24, agent 23:16, customer 05:08 (29 Jun) | `app/store.py:77-78` orders by `created_at, message_id`; data: messages M007386 to M007390 |

Display details (what the page does with the raw values):

- **Times are shown to the minute.** `stamp()` formats with `"%d %b %Y, %H:%M"` (`app/views.py:23`), so `11:31:36` becomes 11:31 and `05:08:48` becomes 05:08.
- **Agent messages are signed "Orion Support", not Clara.** Messages store only `author_role`, and the code says so: "The snapshot stores message roles, not individual author identities." (`app/views.py:96-97`). Customer messages are signed with the company name.
- **The sidebar shows no queue counts on ticket pages.** The ticket route calls `page(...)` without `queue_counts` (`app/web.py:77`), so `base.html:29` has no counts to print. Only the ticket list passes them.
- **The response and resolution times agree with the timestamps.** 7 h 57 min 36 s = 7.96 h, and 25 h 34 min 48 s = 25.58 h (see F1).

## Unknowns

1. **Whether the missing resolution flag is intended.** `AGENTS.md` asks to keep "basic status reporting", but it does not say whether the ticket page should flag resolution misses. Nothing in the code or notes says the omission is deliberate.
2. **The official definition of "missed".** I used "took longer than the target" (`>`), the same rule the page uses for responses (`app/views.py:91`). No written policy defining a miss was checked. A rule that also counts reaching the target exactly as a miss (`>=`) could give different counts in F2. It would not change the answer for T00727, which is over both targets by more than an hour.
3. **What "most recently created" means.** I used `created_at`. T00727 is not the highest ticket ID, so ordering by ID would give a different ticket.
4. **Whether the live desk reads exactly this data.** Only T00727's page was compared, and it matched. The live site's database settings were not checked, because `.env` was out of scope.
5. **Whether the connector account is read-only.** Answered. The chat's TiDB connection signs in as the reader user (`orion_reader`), whose grants allow `SELECT` only (checked with `SHOW GRANTS`). The Code tab's lab connection still signs in as root; its write tools are blocked by a deny rule, not by the database. See [evidence/b12-satisfaction-vs-first-reply.md](evidence/b12-satisfaction-vs-first-reply.md) for the query run through the reader.
6. **Which agent wrote each message.** The data stores only the author's role (`customer`/`agent`), so Clara cannot be confirmed as the author of the two agent replies.
7. **Whether the counts in F2 are current.** They come from the `orion_lab` data as queried on 2026-11-02. Whether this data is a fixed snapshot or still changing was not checked.
