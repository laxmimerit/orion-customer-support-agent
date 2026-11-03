# Roadmap: Orion replacement desk

- **Status:** Draft
- **Built from:** [backlog.md](backlog.md), [investigation.md](investigation.md), [decisions/0001-database.md](decisions/0001-database.md) (Proposed), [evidence/b12-satisfaction-vs-first-reply.md](evidence/b12-satisfaction-vs-first-reply.md) and [plan.md](plan.md).
- **No dates.** Phases are an order, not a schedule.
- **Increments are not repeated here.** Each phase points to its increment numbers in [plan.md, Section 3](plan.md#3-build-from-course-start-in-small-checked-increments). That table holds the "done when" checks.

**Owner.** No file names a delivery owner for any row, and plan.md A6 says even go / no-go is unconfirmed. So "Owner" here is who the row is for: the named requester where the handbook gives one, otherwise the role in backlog.md. Replace it when someone is assigned.

**Evidence strength** (how well the row's own claim is supported):

| Level | Meaning |
|---|---|
| Strong | Reproduced on the live desk or measured in the data, as the row states it. |
| Moderate | A confirmed staff request, or a measured association. The claim holds, but the cost or the cause is not measured. |
| None | Assumed. Nothing in the notes supports it. |

Almost every Seen row comes from one walkthrough (ticket T00727, customer C0086). Strong means the gap exists on the desk; none of the rows measures how much time it costs agents. That is what B05 is for.

## Check first

Assumed rows. Do not build on them, and do not let them set the order, until the check is done.

| Row | Owner | Claim | Waits on | Gates | Evidence |
|---|---|---|---|---|---|
| B05 | Support agent | Agents lose the most time on the customer page | Time per page measured for a sample of tickets, showing whether the customer page is the largest share (backlog B05 criterion) | The order of the customer-page work in Phase 2 (B01, B02, B07). Plan A1. | None |
| B14 | Admin | Admins look up customer accounts many times a day | Lookups per admin per day counted (backlog B14 criterion) | Whether B13 (customer list search) is worth its place in Phase 2 | None |

## Phase 0: Foundation

Plan increments [0–1](plan.md#3-build-from-course-start-in-small-checked-increments). No backlog rows; everything below depends on it.

Waits on:
- ADR 0001 accepted (it is Proposed).
- The export account checked as read-only, as plan Section 4 requires, and the migration checks recorded: [ADR 0001, "What the migration must prove"](decisions/0001-database.md#what-the-migration-must-prove).
- Confirming `orion_lab` is not changing (plan A2).

## Phase 1: Read parity

Plan increments [2–3](plan.md#3-build-from-course-start-in-small-checked-increments). No backlog rows. Must-stay M01, M02, M04, M05 are first proven here. Phase 2 onward waits on this.

## Phase 2: Ticket, customer and guidance in one place

Plan increments [4–6](plan.md#3-build-from-course-start-in-small-checked-increments). Order still depends on the B05 and B14 checks above.

| Row | Item | Owner | Waits on | Evidence |
|---|---|---|---|---|
| B01 | Ticket and customer need page hopping | Support agent | Phase 1. B05 check, for order. | Strong. Six clicks, three of them repeats. The ticket page already shows the conversation and customer summary, so the real gap is the customer's other tickets and invoices. |
| B07 | Less moving between queue, customer and conversation | Leena (REQ003), Support lead | Same check as B01, so it moves with it. | Moderate. A staff request; the B01 observation supports it. |
| B03 | Ticket page has no link to guidance | Support agent | Phase 1. A decision on which of KB004 and KB034 (both titled "Invite link expired") applies. Nothing in the notes says who decides. | Strong |
| B02 | Customer page shows no messages | Support agent | Phase 1 (messages by ticket). B05 check, for order. | Strong. 18 tickets, no messages. |
| B13 | Customer list has no search | Admin | Phase 1. B14 check. Customer list order must match legacy under the new database's bytewise default (Fern Platform 086 at row 163; ADR check 8). | Strong |

## Phase 3: Service targets and reports

Plan increments [7 and 9](plan.md#3-build-from-course-start-in-small-checked-increments). Must-stay M07 (missing is never zero) applies to every row here.

| Row | Item | Owner | Waits on | Evidence |
|---|---|---|---|---|
| B06 | Queue shows first response against each priority's target | Support lead | Phase 0 (targets and `sla_policy` loaded and reconciled). A rule for "missed": the page uses `>`, and three tickets sit exactly on the line (investigation Unknown 2). | Strong. T00727: 7.96 h against 3 h; the queue shows none of it. |
| B10 | Report filters by date, channel and customer segment | CX / founder | Phase 0. "Customer segment" is not defined in these five files. | Strong. The report says itself it has no filters. |
| B11 | Response times by channel, plan and period | Maya (REQ002), CX / founder | Phase 0. Written definitions of each measure, and a check of missing values and denominators (REQ002). First-reply time comes from the ticket row because `ticket_events` logs no first-reply event. | Moderate. A staff request. |

### Not in an increment: B12

| Row | Item | Owner | Waits on | Evidence |
|---|---|---|---|---|
| B12 | Customers are unhappy with slow first replies | CX / founder | A decision on whether an association is enough to act on, or whether a causal test comes first. The evidence file lists what is uncontrolled: category, channel, agent, plan, escalation, reopen count. About a third of resolved tickets have no rating. CSAT may reflect the resolution, not the first reply. If it is acted on, B06 is the nearest row it would inform (my reading; no file links them). | Moderate, as an association only. Rated tickets that missed the target average 2.90 / 5 against 4.40 when met (903 vs 1,426), lower in every priority. T00727 missed by about 5 h and scored 4 / 5. |

plan.md now records B12 as Seen in data too.

## Phase 4: Finding related cases

Plan increment [8](plan.md#3-build-from-course-start-in-small-checked-increments). Must-stay M01: exact lookup by ticket ID stays.

| Row | Item | Owner | Waits on | Evidence |
|---|---|---|---|---|
| B04 | Search matches only exact words in the subject | Support agent | Phase 1. The search design, which ADR 0001 does not choose. Today's subject-only search is documented as intended, so this changes it deliberately through this row. | Strong. "invitation" 0, "invite" 265; IDs are not matched either. |
| B08 | Related cases worded differently, with the reason shown | Leena (REQ001), Support lead | The same search design, and a way to show why each case was proposed. Vector and full-text are available on the preview database, but production cannot use that database yet. | Moderate. A staff request. |

## Phase 5: Writes and drafting

Plan increments [10–11](plan.md#3-build-from-course-start-in-small-checked-increments). These are the first writes, so they wait on the rollback questions in [plan Section 5](plan.md#5-rollback).

| Row | Item | Owner | Waits on | Evidence |
|---|---|---|---|---|
| B09 | Change owner and status on the ticket page | Support lead | Phase 0. A decision on whether a rollback may drop replacement writes if they are logged (plan A3), needed before increment 10 ships. M06: new database only. | Strong that the controls are missing. No staff request asks for them. |
| B15 | Draft replies from evidence | Arun (REQ004), Engineering | Phase 0. M03: a named person approves every reply. Sources to cite, which is my reading and not stated in plan.md: related-ticket search (Phase 4) and the article link (Phase 2). | Moderate. A staff request. |

## Gates that apply to every phase

- **Production database.** ADR 0001 rules out the preview database for production. Production needs its own decision record.
- **Cut-over preconditions and open assumptions** (rollback window, hosting, go / no-go owner): [plan Sections 5 and 6](plan.md#6-cut-over), and its assumptions table.
- **Order.** Plan A1 says no priority has been agreed. This roadmap uses the plan's order and changes nothing in it.
