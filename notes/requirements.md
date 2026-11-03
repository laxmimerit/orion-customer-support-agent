# Phase 1 requirements

## Requirements

Phase 1 is proven by four Must-stay rows from backlog.md: M01, M02, M04 and M05. roadmap.md lists no B-row under Phase 1 and names these four. Each line is tested on the new desk's ticket page for T00727.

| Row | Requirement |
| --- | --- |
| M01 | Opening `/tickets/T00727` shows ticket T00727 and no other ticket. |
| M02 | T00727's page shows customer C0086 (Fern Platform 086) and all 5 messages, M007386 to M007390, oldest first. |
| M04 | Every control on the ticket page can be reached and used with the keyboard alone, and body text meets the contrast measure in Assumption 2. |
| M05 | Every page that exists in Phase 1 shows the Orion orbit mark and the company name. |

## Assumptions

These are guesses, not decisions. Each one changes a requirement above if it turns out wrong.

| # | Guess | How to check |
| --- | --- | --- |
| 1 | Phase 1 ships only the ticket page for T00727 (plan.md increments 2 and 3), so M05 is tested on that page alone. | Confirm that no other page ships in Phase 1. |
| 2 | "Readable text" means body text contrast of at least 4.5:1 (WCAG AA). backlog.md gives no measure. | Agree a measure, then test against it. |
| 3 | M02 is met by showing C0086's summary on the ticket page. The customer page first appears in increment 5, so the link to it may not work in Phase 1. | Decide whether the link must work in Phase 1. If yes, the customer page moves into Phase 1. |
| 4 | The expected values (C0086, 5 messages M007386 to M007390) stay true because `orion_lab` does not change (plan.md A2). | Compare counts and a checksum of the tickets and messages tables on two occasions. |
| 5 | Phase 1 starts once ADR 0001 is accepted and Phase 0's checks pass. The ADR is still Proposed. | Check the ADR's status before starting. |

## Decisions

Six constraints are already decided in the Company handbook and the repository AGENTS files. The requirements above apply them; none is new here.

| Decision | Source |
| --- | --- |
| Every ticket keeps its ID, and exact lookup by ID stays. | Handbook: REQ001, Existing brand and interface (backlog M01) |
| A ticket stays linked to its customer and its messages. | Handbook: Support workflow (backlog M02) |
| New controls and views are usable by keyboard, with readable text. | Handbook: REQ003 (backlog M04) |
| The Orion orbit mark and company identity are kept. | Handbook: Existing brand and interface (backlog M05) |
| Engineering changes run on a separate development database, not the operational records. | Handbook: Changes and responsibilities (backlog M06) |
| The `orion-legacy` code is not changed, and not copied into `main` as a scaffold. | AGENTS files (plan.md Section 2) |

Not yet decided: ADR 0001 is Proposed and plan.md is a Draft. Anything Phase 1 takes from either is an assumption, not a decision.

## Out of scope

Phase 1 reproduces the legacy ticket page under Orion branding and changes no behaviour.

- Every B-row. B01 to B04, B06 to B13 and B15 belong to Phases 2 to 5 in roadmap.md; B05 and B14 are Assumed and wait under "Check first".
- New ID search. Phase 1 covers the `/tickets/T00727` route only; any search by ID is Phase 4.
- Flagging a missed resolution target. The legacy page never does, and whether to change that is undecided (investigation Unknown 1).
- Must-stay M03 and M07. The roadmap first proves them in Phases 5 and 3. M06 is covered by Phase 0's migration checks.
- Reconciling IDs, links, dates and nulls across all 15 tables. That is Phase 0 (ADR 0001, "What the migration must prove").
- Production database, hosting and cut-over (plan.md Sections 5 and 6).
