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
- any claim about list order beyond "in API order", apart from the page ranking defined under Ticket queue

## Design system

The look follows `notes/reference-design.md`: its colours, Inter type, spacing, radii and component styles. It is a look only. The product stays Orion: keep the Orion logo, never recoloured, and never show the reference's product name. DESIGN.md section 7 still sets the case page's layout; its colours and type now come from here.

**Rules that stay**

- Body text stays at 13px.
- A status always shows its word; colour only supports it.
- Keep it flat and dense: no decorative gradients, illustrations or shadows on resting elements.

**How the reference applies**

- **Page and surfaces**: page background #F7F7F7; panels and cards #F7F7FF with a 1px #E2E8F0 border, 14px radius and 20px padding.
- **Text**: #1E293B for text, #0F172A for titles, #607086 for muted text such as breadcrumbs and notes.
- **Type**: Inter throughout, with two weights per screen: regular and semibold. Page title 24px, card and panel headings 16px, inputs 14px, captions 12px.
- **Status pills**: full pill, word always shown. Open uses the teal tint with #0E4F41 text, Pending the amber combo, In progress the blue info combo, Resolved the slate combo.
- **Priority chips**: 4px radius. P1 uses the red combo, P2 the amber combo, P3 and P4 the slate combo.
- **Buttons**: Clear, Previous and Next use the secondary style. The desk changes nothing, so it has no filled primary button.
- **Summary strip**: metric cards with a large semibold figure and its label.
- **Conversation**: chat bubbles, customer on the left on the surface colour, agent on the right.

**Changes to the reference**

- The accent is Orion's teal #098278. It replaces the reference's #31927F everywhere, including that colour's tints.
- Link text and the current top bar link use #0E4F41, because #098278 is 4.4:1 on the surface, just under 4.5:1.
- Agent bubbles use a #0E4F41 fill with #F7F7FF text, for the same reason.
- The focus ring is solid #098278, not the reference's faint 35% tint.
- Muted text is #607086 (4.71:1 on the page, 4.74:1 on the surface), not #64748B (4.44:1 and 4.46:1).

**Left out of the reference, because the desk has no data or use for them**

- timestamps, read receipts and message download links
- sortable headers
- trend indicators on metric cards
- notification badges, lead scores and flow builder nodes
- kanban cards, drag states and per-channel stripes, colours and icons
- the sidebar, replaced by the top bar below
- illustrated empty states, which stay as one line of text
- the hover lift on cards, because only the subject is a link

## Pages

### Top bar (every page)

- One full-width bar at the top of every page, on the surface colour with a 1px #E2E8F0 bottom border. It replaces the masthead and the sidebar in DESIGN.md section 4.
- Left to right: the Orion logo, "Service Desk", then links to Ticket queue and Reports. The current page is marked in the reference's underline tab style, with a 2px #098278 bottom border.
- Nothing else goes in it: no search, counts, account menu, notifications, agent name, date or clock.

### Ticket queue

The queue is a ranked triage view of the 25 tickets on the current page: cards for what needs an agent now, then rows for what's next.

1. **Page heading**: breadcrumb "Tickets / Ticket queue", title, one-line description.
2. **Read-only notice**: one line, stating that values come from the Orion desk API.
3. **Search toolbar**:
   - one labelled input that accepts a ticket ID or plain words
   - a priority select (All priorities, P1, P2, P3, P4), which applies to the search
   - a Clear button
   - a hint saying the box takes either a ticket ID or a description of the problem
4. **Summary strip**: figures from the reports only, each with its unit and a one-line note on what it covers. If no report fits, leave the strip out. Do not show page numbers here.
5. **Needs an agent now**: a heading, the note "Open or in progress at P1 or P2, on this page", then one card per ticket, up to three across at 1280px. Each card shows:
   - ID, subject as a link to the case page, and "category · channel" beneath. The subject is the only link on the card.
   - customer ID as plain text, status pill, priority chip and agent ID.
   - nothing else, and no action of any kind: the desk is read-only.
   - If the page has no such ticket, the section reads "Nothing on this page needs an agent now."
6. **What's next**: a heading, then every other ticket on the page as a row, with these columns, left to right:
   - **Ticket / subject**: ID, subject as a link to the case page, and "category · channel" beneath. The subject is the only link in the row.
   - **Customer**: customer ID as plain text, not styled as a link.
   - **Status**: pill.
   - **Priority**: chip.
   - **Agent**: agent ID.
7. **Caption and paging**: the caption reads "1–25 of 4000, in API order", followed by the note "Ranked within this page by status and priority.", with Previous and Next controls beside it.
8. **Empty state**: "No tickets match." with a one-line way to recover, shown only when the API returns no results. A meaning search normally returns its nearest tickets however weak the match, so this is rare.
9. **Density**: at 1280 × 800, the first line of cards and at least three What's next rows are visible without scrolling.

**Ranking**

The desk ranks the 25 tickets it already has for the page. Which tickets are on a page, and the order of pages, stay as the API returns them.

- It uses status and priority only, both of which the list returns.
- A ticket gets a card when its status is Open or In progress and its priority is P1 or P2. Every other ticket is a row.
- Cards and rows each follow this order:
  1. Tickets that are not resolved come before resolved ones. A ticket with no status counts as not resolved.
  2. Priority: P1, P2, P3, P4.
  3. Status: Open, In progress, Pending.
  4. The ticket's position in the API's list.
- A missing status or priority ranks last at its step, reads "Not recorded", and never earns a card.
- Position is the only sign of rank. Show no rank number, score or reason per ticket.
- Never suggest the ranking covers more than this page. These are the page's 25 tickets, not the 25 most pressing of the 4000. Do not use words such as "most urgent", "oldest" or "longest waiting".
- There is no control to change, turn off or re-run the ranking.

### Search results (on the Ticket queue page)

- Rows only, with the same columns as What's next. No cards and no ranking: results stay in the order the API returns them.
- The section heading reads "Search results".
- The caption names the query and the count: `1 result for "T00727"`, `10 results for "invitation", in relevance order`, or `10 results for "invitation" at P2, in relevance order`.
- An exact ticket ID returns that ticket alone.
- A meaning search lists results in the API's relevance order, and the caption says so.
- The priority filter narrows the results. Clear returns the queue to page 1.

**Every search row**

The API's search answer holds each ticket's ID, subject, status, priority and category only. The desk shows that and says what is missing:

- **Note under the caption**: "Found by exact ID." or "Found by meaning.", then "This answer holds each ticket’s ID, subject, status, priority and category; customer, channel and agent are not in it."
- **Under the subject**: "category · channel not in this answer", then "Found by exact ID" or "Found by meaning".
- **Customer and Agent**: read "Not in this answer". This differs from "Not recorded", where the API returned the field with no value.
- The similarity score is not shown.

**Help articles in results**

A meaning search with no priority filter can return help articles among the tickets. They stay in the API's order and count towards the caption's total. A priority filter leaves them out.

- Each article is a row with its KB ID and title as plain text, not a link: the desk has no article page. Do not design one.
- **Under the title**: "category · Help article", then "Found by meaning".
- **Customer, Status, Priority and Agent**: read "Not a ticket", with no pill or chip.

**ID not found**

When the query has the shape of a ticket ID, the letter T in either case and five digits, and the API answers with `"match": "semantic"`, no ticket has that ID. The API has returned the closest tickets by meaning instead. The desk keeps those results and says what they are, as in the design's States page ("Queue · ID not found"):

- **Caption**: `No ticket has the ID "T09999" · 10 results by meaning`, with the query and count from the answer.
- **Line beneath it**: "No ticket has that ID, so the API returned the 10 tickets closest to it by meaning instead."
- **Note**: "Found by meaning, in relevance order. This answer holds each ticket’s ID, subject, status, priority and category; customer, channel and agent are not in it."
- **Rows**: as for every search row, in the API's order.

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
- Each panel draws real charts from the report's rows:

| Report | Charts |
|---|---|
| volume | Stacked bars, one per month row: resolved and unresolved tickets |
| backlog | Horizontal bars, one per status: tickets. Beside each bar: no first reply, no first reply past target, and average age in hours |
| priority | Stacked bars, one per priority: resolved and unresolved tickets. Separate bar charts for average first reply (h), average resolution (h) and average CSAT |
| category | The same charts as priority, one bar per category |
| first-reply | Stacked bars, one per priority: met, missed and no first reply. Paired bars for average CSAT when met and when missed |

**Chart rules**

- Plot the API's figures as returned. Add no derived rates, trend lines, forecasts or target lines.
- Keep rows in API order. Charts do not re-order them.
- The row named "All" is the report's total. Show it as a figure beside the chart, never as a bar.
- One unit per axis, and every bar axis starts at zero. Tickets, hours and CSAT never share a chart.
- Series colours: resolved and met #0E4F41; unresolved and single-series bars #098278; missed #EF4444; no first reply #64748B. Stacked segments have a 2px gap. All of these reach at least 3:1 on the surface.
- Every value is printed on or beside its mark, so nothing depends on hover. Every series is named in words; colour only supports the name.
- Each average shows how many tickets it covers and how many are not recorded, for example "3.61 from 213 tickets, 107 not recorded".
- A value the API does not return reads "Not recorded" and draws no bar. It is never drawn as zero.
- Volume's rows are months, and months are dates. Its bars carry no month labels and there is no time axis. The note reads "One bar per calendar month, in API order."
- Backlog's oldest ticket date is never shown.
- Charts have no controls: no zoom, range, series toggles or download.

### States

As on the design's States page.

**Queue · loading**

- The top bar, heading, notice and toolbar show as normal. The summary strip, three cards and six rows show as #E2E8F0 placeholder blocks, with no values, real or invented.
- The caption reads "Loading tickets from the Orion desk API", followed by "Ranked within this page by status and priority once loaded." What's next reads "Loading".
- Previous and Next are disabled.

**Queue · desk API down**

- When the API does not answer, or answers 503, the top bar, heading, notice and toolbar stay. The summary strip, cards and rows go.
- One card takes their place, announced as an alert: the heading "Tickets can’t be shown", then "The Orion desk API isn’t responding, so the queue can’t load. Reload the page to try again."

**Queue · token refused**

- When the API answers 401, the page keeps the same frame and shows one alert card: the heading "The desk’s access was refused", then "The Orion desk API refused this desk’s token, so no tickets can be shown. Ask whoever manages the desk’s API access for a new token."
- Beneath it, a facts list shows Status, Code and Message from the API's error answer, as returned.
- The token itself never appears, on the page or in its source.

**Case · resolved, no rating (T00790)**

- This is the case page with both targets met and no CSAT. Nothing in its layout changes.
- CSAT reads "Not recorded", by the rule for missing values.
- Each wait bar fills in #0E4F41 up to the time taken, with the target tick at the end of the bar. The key shows "Within target" only.

## Narrow widths

- **768px**: the summary strip, toolbar and cards wrap without overlapping.
- **375px**:
  - the top bar's links wrap below the logo
  - the search input and priority select go full width
  - cards stack one per line
  - the What's next rows scroll sideways inside their own box
  - each chart fits the page width with its labels readable
  - the case page's right column drops below the left
  - the page itself never scrolls horizontally

## Acceptance criteria

Check each item on the running app.

| # | Page | Record or width | Action | Expected result |
|---|---|---|---|---|
| 1 | Ticket queue | 1280px | Load the page | Caption reads "1–25 of 4000, in API order", followed by "Ranked within this page by status and priority."; 3 cards and 22 rows are shown, 25 tickets in all |
| 2 | Ticket queue | 1280px | Look across the page and click each column header | No sort or ranking control, status filter, agent filter or export control anywhere; clicking a header changes nothing |
| 3 | Ticket queue | 1280px | Read the What's next column headers | Exactly: Ticket / subject, Customer, Status, Priority, Agent |
| 4 | Ticket queue | T01970 row | Read the row | Shows exactly T01970, "Export stops before completion", "bug · web", C0272, Open, P3, A03; no target, wait, company, plan or seats |
| 5 | Ticket queue | 1280 × 800 | Load the page | All 3 cards and at least three What's next rows visible without scrolling |
| 6 | Ticket queue | T00727 | Search "T00727" | No cards and exactly one row, under the caption `1 result for "T00727"`: T00727 "Invite link expired", "account access · channel not in this answer", "Found by exact ID", Resolved, P2; Customer and Agent read "Not in this answer"; no target, wait, company, plan or seats |
| 7 | Ticket queue | T00727 | Search "invitation" | T00727 is the first row; the caption reads `10 results for "invitation", in relevance order` |
| 8 | Ticket queue | T00727 | Search "invite" with priority P2 | Every row shows P2, and T00727 is among them |
| 9 | Ticket queue | T09999 at 1280px | Search "T09999" | Caption reads `No ticket has the ID "T09999" · 10 results by meaning`, then the line and note set out under ID not found; 10 rows from T00244 to T00767, no cards; Clear restores "1–25 of 4000, in API order" and the cards |
| 10 | Ticket queue | 1280px | Press Next | Caption reads "26–50 of 4000, in API order"; the tickets differ from page 1 and follow the same ranking |
| 11 | Ticket queue | Any card or row | Hover the customer ID | It is not a link; only the subject is |
| 12 | Case page | T00727 | Load the page | Breadcrumb reads "Ticket queue / T00727", and its first part opens the queue; title "T00727 · Invite link expired"; ribbon "account access · Identity · Via web" |
| 13 | Case page | T00727 | Read the first-reply tile | "First reply: target missed", target 3 h, waited 7.96 h, tick about 37.7% along the bar |
| 14 | Case page | T00727 | Read the resolution tile | "Resolution: target missed", target 24 h, took 25.58 h, tick about 93.8% along the bar |
| 15 | Case page | T00727 | Read the conversation | Header reads "5 messages"; oldest first; no times; customer messages labelled C0086, agent messages labelled A03 |
| 16 | Case page | T00727 | Read the Ticket facts | Resolved, P2, A03, web, account access, Identity, urgent, CSAT 4, reopened 0, escalated 0 |
| 17 | Case page | T00727 | Read the Customer panel | Customer ID C0086, the company the API returns for C0086, plan "scale", seats 8 |
| 18 | Case page | T00727 at 1280px | Measure the right column | Ticket facts and Customer panels sit beside the left column, between 280px and 320px wide |
| 19 | Case page | T00727 at 375px | Load and scroll | Ticket facts and Customer panels sit below the left column; the page has no horizontal scroll |
| 20 | Ticket queue | 375px | Load and scroll | Top bar above content with its links wrapped below the logo; search and priority full width; cards one per line; the rows scroll sideways inside their box; the page has no horizontal scroll |
| 21 | Ticket queue | 768px | Load the page | Summary strip, toolbar and cards wrap with nothing overlapping |
| 22 | Ticket queue and Case page | Keyboard | Tab to the top bar links, search input, priority select, Clear, subject links and breadcrumb link | Each shows a 3px solid #098278 ring |
| 23 | Ticket queue | 1280px | Read the status pills on cards and rows | Every pill shows its word: Open, In progress, Pending or Resolved |
| 24 | Reports | 1280px | Load the page | Exactly five report panels, named as in the API, each with its charts, each figure with a unit, and no export control |
| 25 | Top bar, Ticket queue, Case page, Reports | Any record | Scan the page | No dates, times or agent names appear anywhere; company, plan and seats appear only in the case page's Customer panel |
| 26 | Ticket queue | Breadcrumb | Inspect its computed colour | #607086 |
| 27 | Ticket queue | Page 1 at 1280px | Read the cards in order | Exactly T01447, T02210, T02894, three across, under "Needs an agent now" |
| 28 | Ticket queue | T01447 card | Read the card | Shows exactly T01447, "Renewal total changed", "billing · email", C0297, Open, P1, A06; no target, wait, company, plan or seats |
| 29 | Ticket queue | Any card | Look for actions | The subject is the only link; no button, menu or other control on the card |
| 30 | Ticket queue | Page 1 at 1280px | Read What's next from the top | Starts T02116, T02899, T01970, T01431; ends T02402, T01054, T03778, T00729 |
| 31 | Ticket queue | T02116 | Find the ticket | It is a row, not a card: pending at P2 does not earn one |
| 32 | Ticket queue | Page 1 at 1280px | Scan cards, rows and notes | No rank numbers, scores or per-ticket reasons; no "most urgent", "oldest" or "longest waiting"; nothing claims to cover more than this page |
| 33 | Ticket queue | Page 4 | Load the page | The section reads "Nothing on this page needs an agent now." and What's next still lists the page's tickets |
| 34 | Every page | 1280px | Read the top bar | Orion logo, "Service Desk", then Ticket queue and Reports with the current page in #0E4F41 and a 2px #098278 underline; each link opens its page; no search, counts, account menu, agent name, date or clock; no sidebar |
| 35 | Ticket queue | T00727 | Search "invitation" and compare with the API's results | Rows only, in the API's order, with no ranking applied |
| 36 | Reports | volume | Read the chart | Six stacked bars with no month labels and no time axis; the first shows 581 resolved and 83 unresolved; the total of 4000 tickets is a figure, not a bar; the note reads "One bar per calendar month, in API order." |
| 37 | Reports | backlog | Read the chart | Three bars in API order: in progress 147, open 172, pending 156; the total of 475 is a figure, not a bar; no oldest ticket date anywhere |
| 38 | Reports | priority | Read the charts | Four bars per chart, P1 to P4; tickets, hours and CSAT on separate charts; P1 average first reply 1.50 h from 352 tickets; P1 average CSAT "3.61 from 213 tickets, 107 not recorded" |
| 39 | Reports | category | Read the charts | Six bars per chart, from account access to outage in API order, with no "All" bar; outage average first reply 3.51 h |
| 40 | Reports | first-reply | Read the charts | P1 shows met 230, missed 122, no first reply 0; average CSAT 4.09 when met and 2.68 when missed, each with the tickets it covers |
| 41 | Reports | 1280px | Hover and click each chart, then view the page in greyscale | Every value is readable without hover; every series is still named in words; nothing filters, zooms or downloads |
| 42 | Reports | 375px | Load and scroll | Each chart fits the page width with labels readable; the page has no horizontal scroll |
| 43 | Ticket queue | Any card | Inspect its computed styles | Background #F7F7FF, 1px #E2E8F0 border, 14px radius, 20px padding, no shadow at rest or on hover, no lift on hover; the page behind it is #F7F7F7 |
| 44 | Ticket queue, Case page, Reports | 1280px | Inspect headings, body text and links | Inter throughout; body text 13px; at most two weights; links #0E4F41 |
| 45 | Ticket queue | Page 1 | Read the pills and chips | Open is a #098278 tint with #0E4F41 text, Pending amber, In progress blue, Resolved slate; P1 red, P2 amber, P3 and P4 slate; every pill and chip reaches 4.5:1 and shows its word |
| 46 | Ticket queue | 1280px | Look at the buttons | Clear, Previous and Next use the secondary style; no filled primary button anywhere |
| 47 | Case page | T00727 | Read the conversation | Customer bubbles left on the surface colour; agent bubbles right in #0E4F41 with #F7F7FF text; no times, read receipts or download links |
| 48 | Reports | Any chart | Inspect the series | Resolved and met #0E4F41, unresolved and single-series bars #098278, missed #EF4444, no first reply #64748B; stacked segments have a 2px gap |
| 49 | Every page | Any record | Scan the page | The reference's product name, trend indicators, notification badges, lead scores, kanban cards and channel stripes do not appear; the Orion logo is unchanged |
| 50 | Ticket queue | T09999, first row | Read the row | Shows exactly T00244, "Missing rows in downloaded CSV", "bug · channel not in this answer", "Found by meaning", Resolved, P3; Customer and Agent read "Not in this answer"; no similarity score |
| 51 | Ticket queue | 1280px | Search "zzqx" | 10 rows in the API's relevance order, with the caption `10 results for "zzqx", in relevance order`; no ID not found message and no "No tickets match." |
| 52 | Ticket queue | 1280px | Search "t00727" in lower case | Caption reads `No ticket has the ID "t00727" · 10 results by meaning`, because IDs are case-sensitive |
| 53 | Ticket queue | Search "invitation" with priority P2 | Read the caption, note and rows | Caption reads `10 results for "invitation" at P2, in relevance order`; the note starts "Found by meaning."; every row reads "Found by meaning" and "Not in this answer" for Customer and Agent |
| 54 | Ticket queue | Loading, with the API's answer held back | Load the page | Placeholder blocks for the summary strip, three cards and six rows; no values shown; caption reads "Loading tickets from the Orion desk API", then "Ranked within this page by status and priority once loaded."; Previous and Next disabled |
| 55 | Ticket queue | `ORION_API_URL` set to a closed port | Load the page | Top bar, heading, notice and toolbar show; no summary strip, cards or rows; one alert card, "Tickets can’t be shown", with the reload line |
| 56 | Ticket queue | `ORION_AGENT_TOKEN` set to a wrong value | Load the page | One alert card, "The desk’s access was refused"; facts read Status 401, Code invalid_token, Message "The token is not valid."; no tickets shown |
| 57 | Ticket queue | Wrong token, as in 56 | Search the page and its source for the token sent | It appears nowhere |
| 58 | Case page | T00790 | Read the heading and both tiles | Title "T00790 · Role change not applied"; ribbon "account access · Identity · Via chat"; "First reply: target met", target 9 h, waited 6 h, bar filled about 66.7%; "Resolution: target met", target 72 h, took 24.73 h, bar filled about 34.3%; tick at the end of both bars; the key shows "Within target" only |
| 59 | Case page | T00790 | Read the Ticket facts and conversation | Resolved, P3, A02, chat, account access, Identity, positive, CSAT "Not recorded", reopened 0, escalated 0; header reads "8 messages", customer messages labelled C0086, agent messages labelled A02 |
| 60 | Ticket queue | KB009 | Search "how do I export tickets" | KB009 then KB039 are the first two rows, then T02368; the caption counts all 10 |
| 61 | Ticket queue | KB009 row | Read the row and hover the title | KB009, "Export monthly ticket history" as plain text with no link, "how-to · Help article", "Found by meaning"; Customer, Status, Priority and Agent read "Not a ticket", with no pill or chip |
| 62 | Ticket queue | KB009 | Search "how do I export tickets" with priority P2 | Every row is a ticket showing P2; no help articles |