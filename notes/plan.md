# Replacement plan: Orion Classic → new desk

- **Status:** Draft
- **Inputs:** [backlog.md](backlog.md), [observations.md](observations.md), [investigation.md](investigation.md), [decisions/0001-database.md](decisions/0001-database.md), `../orion-legacy/database/manifest.json`, the `orion-legacy` and `main` READMEs and AGENTS files.

Anything marked **Assumption (An)** has no evidence in those sources. Each one is listed at the end with how to check it.

## 1. Starting point

| What | State | Evidence |
|---|---|---|
| Legacy code | Branch `orion-legacy` at `a1740ed`, clean, matches `origin/orion-legacy`. Flask/Jinja2, `pymysql`, every query a `SELECT`. | `git status` in `../orion-legacy`; investigation, Method; ADR 0001, Today's setup |
| Legacy data | Baseline `orion-legacy-v1`: 15 tables (e.g. 4000 tickets, 300 customers, 36694 messages, 1800 invoices). Restored and checked by `tools/lab.py`, which verifies the SQL checksum, all 15 counts and that no message is orphaned. | `manifest.json` (`table_counts`, `sql_sha256`); `tools/lab.py` |
| Legacy deployment | https://orion-legacy.vercel.app, read-only credentials. | `../orion-legacy/VERIFICATION.md`; README |
| Empty checkpoint | Tag `course-start` = `main` head `8e124f6`, "Document empty course-start checkpoint". It holds only `.gitignore`, `AGENTS.md`, `README.md`. | `git ls-remote origin`; shallow clone of `main` checked 2026-11-02 |
| Target stack | FastAPI backend, Next.js frontend, checked SQL reports, MySQL → PostgreSQL-compatible migration. | `main` README |
| Development database | Separate PostgreSQL-compatible TiDB Starter instance (ADR 0001, **Proposed**, not yet accepted). | ADR 0001 |

## 2. Keep the legacy code as a reference

- Do not change `orion-legacy`. Its AGENTS file limits changes to baseline or setup corrections and asks to keep the original deployment available.
- Do not copy or merge its code into `main` as a scaffold (both AGENTS files). `store.py` and `views.py` are read for behaviour, not ported line for line (ADR 0001, Consequences).
- Run a personal legacy copy beside the new build (`lab.py restore`, `lab.py check`, `serve.py` on http://127.0.0.1:8080) so every increment can be compared page by page with the original.
- The legacy tests in `tests/test_baseline.py` (search escaping, nulls, pagination, joins, HTML escaping, full message bodies) are the list of behaviours the replacement must match or deliberately change.
- Behaviour that is deliberately limited today (subject-only search, status-only report) is changed only through a backlog item (B04, B08, B10, B11), never as a side effect.

## 3. Build from `course-start` in small checked increments

Work on a personal branch cut from the tag: `git switch -c my-orion-build course-start` (main README). Bring `notes/` in first.

Each increment is one small change that ends with:

1. its check, written before the code and run against the new desk;
2. the Must-stay checks M01–M07 from the backlog that it touches;
3. a side-by-side look at the same page on the legacy reference;
4. a commit (and a tag such as `inc-03`) only when all of the above pass, so the previous tag is always a working rollback point.

| # | Increment | Done when (check) | Source |
|---|---|---|---|
| 0 | Branch from `course-start`, add notes, ignore rules for `.env` | `git diff course-start` shows only notes; no credentials tracked | main README, AGENTS |
| 1 | Development database loaded and reconciled (Section 4) | All 14 checks in ADR 0001 pass and are recorded | ADR 0001, M06 |
| 2 | Read-only backend: ticket by ID with customer and messages | `/tickets/T00727` returns T00727, C0086, agent A03 and messages M007386–M007390 in order | M01, M02 |
| 3 | Ticket page with Orion branding, parity with legacy | Every area in investigation F3 matches the legacy page for T00727; keyboard-only use works | M04, M05, investigation F3 |
| 4 | Customer's other tickets and the help article on the ticket page | B01 / B03 / B07 criteria; it is clear whether KB004 or KB034 applies | backlog |
| 5 | Customer page shows messages in place | B02 criterion on C0086's 18 tickets | backlog |
| 6 | Customer list search | B13: "Fern" or "C0086" finds Fern Platform 086 | backlog |
| 7 | Queue shows first response against each priority's target | B06 criterion | backlog |
| 8 | Search that matches other wording, with reasons; exact ID lookup kept | B04 and B08 criteria, M01 | backlog |
| 9 | Reports with filters and response times, missing values excluded and counted | B10, B11, M07 | backlog |
| 10 | Owner and status changes (first writes, new database only) | B09 criterion; nothing written to legacy | backlog, M06 |
| 11 | Reply drafting with sources and human approval | B15 criterion, M03 | backlog |

Not scheduled yet:

- **B05, B14** are Assumed in the backlog. Measure them before they change the order above. **B12** is Seen in data (association only); see the backlog.
- **Resolution-target flag.** The legacy ticket page never flags a missed resolution (226 tickets missed both targets, 257 only the resolution one; investigation F2). Whether that omission is intended is unknown (investigation Unknown 1), so it stays out until you decide.
- **Order of increments 4–11.** **Assumption (A1):** the order follows the backlog's Seen and Asked items, reads before writes, and drafting last. No priority has been agreed.

## 4. Reconcile the data

The full list is ADR 0001, "What the migration must prove" (checks 1–14). In short:

- **Source untouched.** Export from `orion_lab` with `SELECT` only, through a read-only account. VERIFICATION.md says the reference account denied a write probe; the account used for the export must be checked the same way (investigation Unknown 5).
- **Counts.** All 15 tables, counted in `orion_lab` at export time and again in the new database. The manifest counts are the expected values but are not yet confirmed against `orion_lab` (ADR 0001, Unknown 3). Also the investigation's subtotals: 3525 resolved, 483 missed resolution, 226 missed both.
- **Identity and links.** IDs unchanged; every ticket → customer, message → ticket and non-null agent link resolves; T00727 → C0086, A03, 5 messages.
- **Values.** UTC dates to the second, nulls stay null (no `''` or `0`), 4-decimal hours, exact invoice amounts, UTF-8 text byte for byte.
- **Behaviour.** Sort order (customer list bytewise under the new default: Fern Platform 086 at row 163), filters, the legacy search counts ("invite" 265, "invitation" 0).
- **Repeatable.** Export, load and checks run from one script and are run again for the final reconciliation at cut-over (Section 6).

VERIFICATION.md records that an instructor rehearsal already reconciled all 15 tables by checksum on an isolated schema. That shows the path works; it does not replace running the checks on our own export.

**Assumption (A2):** `orion_lab` does not change between the first export and cut-over. The legacy app only reads, but whether anything else writes to it was not checked (investigation Unknown 7). If it does change, the final reconciliation must re-export and re-check, not reuse the first load.

## 5. Rollback

| Level | How to roll back | Evidence / status |
|---|---|---|
| One increment | Return the branch to the previous `inc-NN` tag (or revert the commit). | Plan rule (Section 3) |
| Development database | Drop it and reload from the export with the repeatable script. Never use `lab.py reset` for this: it is for a personal legacy lab and "is not a backup or migration tool". | ADR 0001 check 14; legacy README |
| After cut-over | Send users back to the legacy desk. It keeps running against its own unchanged data. | AGENTS (keep the original deployment); M06 |

Open problems with rolling back after cut-over:

- **Writes made in the replacement do not exist in legacy.** Once increments 10 and 11 are live, owner and status changes and approved replies exist only in the new database. The legacy app has no write path to replay them. **Assumption (A3):** a rollback can accept losing those writes from the desk view, provided the replacement keeps an exportable log of them. Needs a decision before cut-over.
- **Rollback window and trigger.** **Assumption (A4):** legacy stays deployed for at least two weeks after cut-over, and any failed Must-stay check in production triggers a rollback. Neither the length nor the trigger has been agreed.

## 6. Cut-over

Blocked until the replacement has a production database. ADR 0001 rules out production on PostgreSQL-compatible TiDB while it is in preview, and says production gets its own decision record (option C if GA has not arrived).

Preconditions:

1. ADR 0001 accepted, and the production database decided in its own record.
2. All accepted increments tagged, each with its checks passing.
3. Final export from `orion_lab`, loaded into the production database, and all 14 reconciliation checks passing on it.
4. The rollback questions in Section 5 answered.

Steps:

1. Record the export time and the counts.
2. Deploy the replacement against the production database. **Assumption (A5):** hosting is not chosen yet; the legacy desk runs on Vercel, but nothing says where the FastAPI and Next.js apps will run.
3. Smoke check on the deployed desk: open T00727 by ID, its customer and messages, the C0086 page, the queue search, the report, and the missing-value cases (e.g. T01841's satisfaction).
4. Point staff at the new desk. Leave https://orion-legacy.vercel.app running for the rollback window.
5. After the window, write down the outcome. Retiring the legacy deployment is a separate decision; AGENTS says to keep it as the reference.

**Assumption (A6):** you make the go / no-go call. No owner for cut-over is named in the notes.

## Assumptions to check

| ID | Assumption | How to check |
|---|---|---|
| A1 | Increments 4–11 follow the order in Section 3 | Agree priorities with you; measure B05, B14 |
| A2 | `orion_lab` is not changing | Compare counts and a checksum of each table on two dates |
| A3 | Rollback may drop replacement writes if they are logged | Your decision before increment 10 ships |
| A4 | Two-week rollback window; failed Must-stay check triggers rollback | Your decision before cut-over |
| A5 | Hosting for the replacement is undecided | Decision record for hosting |
| A6 | You own go / no-go | Confirm with you |

Other unknowns carried over: investigation Unknowns 1, 4, 5 and 7, and ADR 0001 Unknowns 1–4.
