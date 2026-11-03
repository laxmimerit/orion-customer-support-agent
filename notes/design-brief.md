# Design brief: Orion desk for support agents

## Who it is for

Leena's support agents, who keep the desk open all day. They need to find a ticket quickly from the queue, then open the case to see whether it met its targets, who the customer is, and what was said. The desk is read-only: nothing on it changes a ticket.

## What the API can answer: design only for this

- **Ticket list fields**: ticket ID, subject, category, channel, status, priority, customer ID, agent ID. Nothing else appears in the queue or in search results.
- **Case page fields**: everything in the list, plus:
  - request text, component, sentiment, CSAT, reopened count, escalated count
  - first-reply target and time waited
  - resolution target and time taken
  - the conversation messages in order
  - the customer's company, plan and seats
- **Search**: by meaning (plain words) or by exact ticket ID, with an optional priority filter (P1 to P4).
- **Reports**: the five reports the API provides.
- **Paged list**: tickets 25 per page, in the order the API returns them.

Design nothing beyond these. In particular, do not design controls, placeholders or "coming soon" states for:

- sorting of any kind, and clickable column headers
- a status filter, or an agent filter
- export, download or copy-to-spreadsheet
- targets, waits, company, plan or seats in the queue or in search results
- customer details beyond customer ID, company, plan and seats
- agent names or teams beyond the agent ID
- dates or times, which must not appear anywhere
- any claim about list order beyond "in API order"

## Design system

- Use the Orion design system and the token roles set out in DESIGN.md sections 3 to 5.
- Use the `Ours: 4.5:1 text` colours if the design-system owners accept that proposal, and the `Live site` colours if they do not.
- Body text stays at 13px.
- A status always shows its word; colour only supports it.

## Pages

### Ticket queue

1. **Page heading**: breadcrumb "Tickets / Ticket queue", title, one-line description.
2. **Read-only notice**: one line, stating that values come from the Orion desk API.
3. **Search toolbar**:
   - one labelled input that accepts a ticket ID or plain words
   - a priority select (All priorities, P1, P2, P3, P4), which applies to the search
   - a Clear button
   - a hint saying the box takes either a ticket ID or a description of the problem
4. **Summary strip**: figures from the reports only, each with its unit and a one-line note on what it covers. If no report fits, leave the strip out. Do not show page numbers here.
5. **Ticket list**, with these columns, left to right:
   - **Ticket / subject**: ID, subject as a link to the case page, and "category · channel" beneath. The subject is the only link in the row.
   - **Customer**: customer ID as plain text, not styled as a link.
   - **Status**: pill.
   - **Priority**: chip.
   - **Agent**: agent ID.
6. **Caption and paging**: the caption reads "1–25 of 4000, in API order", with Previous and Next controls beside the list.
7. **Empty state**: "No tickets match." with a one-line way to recover.
8. **Density**: rows tight enough that at least eight are visible at 1280 × 800 below the toolbar.

### Search results (on the Ticket queue page)

- Same list and columns as the queue.
- The caption names the query and the count, for example `3 results for "invite link expired"`.
- An exact ticket ID returns that ticket alone.
- A meaning search lists results in the API's relevance order, and the caption says so.
- The priority filter narrows the results. Clear returns the queue to page 1.

### Case page

As in DESIGN.md section 7, with the source changed from the trace to the API, and with these changes.

**Header and left column**

1. **Heading**: breadcrumb "Ticket queue / <ID>", where the first part links back; the title; the ribbon "category · component · Via channel".
2. **Read-only notice**.
3. **Request summary**: the request text.
4. **Service targets**: two tiles. This is the only place targets and waits appear.
   - First reply: target, time waited, the outcome words ("target met" or "target missed"), and the wait bar with its target tick.
   - Resolution: target, time taken, the outcome words, and the same bar.
5. **Conversation**: messages oldest first, with no times. Customer messages are labelled with the customer ID; agent messages with the agent ID.

**Right column**

6. **Ticket facts**: status, priority, assigned agent ID, channel, category, component, sentiment, CSAT, reopened, escalated.
7. **Customer panel**: customer ID, company, plan, seats.

**Missing values**: a field the API does not return for a ticket reads "Not recorded". Never leave it blank or fill it in.

### Reports

- One panel per report: its name, its figures with units, and a one-line note on what it covers.
- No export and no date pickers.

## Narrow widths

- **768px**: the summary strip and toolbar wrap without overlapping.
- **375px**:
  - the sidebar stacks above the content
  - the search input and priority select go full width
  - the ticket list scrolls sideways inside its own box
  - the case page's right column drops below the left
  - the page itself never scrolls horizontally

## Acceptance criteria

Check each item on the running app.

| # | Page | Record or width | Action | Expected result |
|---|---|---|---|---|
| 1 | Ticket queue | 1280px | Load the page | Caption reads "1–25 of 4000, in API order" and 25 rows are shown |
| 2 | Ticket queue | 1280px | Look across the page and click each column header | No sort control, status filter, agent filter or export control anywhere; clicking a header changes nothing |
| 3 | Ticket queue | 1280px | Read the column headers | Exactly: Ticket / subject, Customer, Status, Priority, Agent |
| 4 | Ticket queue | T01970 row | Read the row | Shows exactly T01970, "Export stops before completion", "bug · web", C0272, Open, P3, A03; no target, wait, company, plan or seats |
| 5 | Ticket queue | 1280 × 800 | Load the page | At least eight rows visible below the toolbar without scrolling |
| 6 | Ticket queue | T00727 | Search "T00727" | Exactly one row: T00727 "Invite link expired", "account access · web", C0086, Resolved, P2, A03; no target, wait, company, plan or seats |
| 7 | Ticket queue | T00727 | Search "invite link expired" | T00727 appears on the first page of results; the caption shows the count and the query |
| 8 | Ticket queue | T00727 | Search "invite" with priority P2 | Every row shows P2, and T00727 is among them |
| 9 | Ticket queue | 1280px | Search "zzqx" | Shows "No tickets match." with a way to recover; Clear restores "1–25 of 4000, in API order" |
| 10 | Ticket queue | 1280px | Press Next | Caption reads "26–50 of 4000, in API order" and the first row differs from page 1 |
| 11 | Ticket queue | Any row | Hover the customer ID | It is not a link; only the subject is |
| 12 | Case page | T00727 | Load the page | Breadcrumb reads "Ticket queue / T00727", and its first part opens the queue; title "T00727 · Invite link expired"; ribbon "account access · Identity · Via web" |
| 13 | Case page | T00727 | Read the first-reply tile | "First reply: target missed", target 3 h, waited 7.96 h, tick about 37.7% along the bar |
| 14 | Case page | T00727 | Read the resolution tile | "Resolution: target missed", target 24 h, took 25.58 h, tick about 93.8% along the bar |
| 15 | Case page | T00727 | Read the conversation | Header reads "5 messages"; oldest first; no times; customer messages labelled C0086, agent messages labelled A03 |
| 16 | Case page | T00727 | Read the Ticket facts | Resolved, P2, A03, web, account access, Identity, urgent, CSAT 4, reopened 0, escalated 0 |
| 17 | Case page | T00727 | Read the Customer panel | Customer ID C0086, the company the API returns for C0086, plan "scale", seats 8 |
| 18 | Case page | T00727 at 1280px | Measure the right column | Ticket facts and Customer panels sit beside the left column, between 280px and 320px wide |
| 19 | Case page | T00727 at 375px | Load and scroll | Ticket facts and Customer panels sit below the left column; the page has no horizontal scroll |
| 20 | Ticket queue | 375px | Load and scroll | Sidebar above content; search and priority full width; the list scrolls sideways inside its box; the page has no horizontal scroll |
| 21 | Ticket queue | 768px | Load the page | Summary strip and toolbar wrap with nothing overlapping |
| 22 | Ticket queue and Case page | Keyboard | Tab to the search input, priority select, Clear, subject links and breadcrumb link | Each shows a 3px solid #bd7200 outline at 3px offset |
| 23 | Ticket queue | 1280px | Read the status pills | Every pill shows its word: Open, In progress, Pending or Resolved |
| 24 | Reports | 1280px | Load the page | Exactly five report panels, named as in the API, each figure with a unit, and no export control |
| 25 | Ticket queue, Case page, Reports | Any record | Scan the page | No dates, times or agent names appear anywhere; company, plan and seats appear only in the case page's Customer panel |
| 26 | Ticket queue | Breadcrumb | Inspect its computed colour | #626f78 if the 4.5:1 text colours were accepted, #7a8b96 if the live colours were kept |

Direction chosen: Desk direction · Opus 5.5, because it shows every value the brief doesn't give as a labelled placeholder instead of inventing or mislabelling it.