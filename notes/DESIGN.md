# DESIGN.md: Orion desk

This describes the desk as built in `web/`: nine pages from the design at
<https://claude.ai/code/artifact/0b59821c-cbf8-4014-a9df-b349e462ea38>. The design decides the look. The API decides every value.

## 1. Rules

- Every value on a page comes from the desk API in `api/`. Nothing is read from `notes/design-data`: those files are saved samples that the design was drawn from.
- A sentence that makes a claim about the data, such as a report headline, is computed. If the claim is not true of the data, a neutral sentence with the real figures is shown instead.
- No emails and no dates or times. Periods in reports are numbered, not named. Durations ("7h 58m", "81 days") are not dates and stay.
- A missing value reads "Not recorded". It is never 0 or an empty cell.
- A status or priority always shows its word. Colour only supports it.
- The desk is view only. Nothing on it changes a ticket.

## 2. Tokens

CSS variables on `:root` in `web/app/globals.css`. Pages use the variables, never a raw colour.

| Group | Values |
|---|---|
| Surfaces | page #F3F6F6, surface #FCFDFD, surface-soft #F7F9F9, hover #EAF0F1 |
| Text | ink #152C39, ink-strong #0F2430, ink-2 #3F505B, ink-muted #4A5A64, placeholder #6B7A83 |
| Lines | line #E1E7E8, line-soft #EDF1F2, row #E7ECED, control #CBD5D7, input #D3DDDF |
| Teal | teal #098278, fill #00927F, ink #066B63, deep #05524C, bubble #0A7A70, pill #E0F2EF, tint #E3F2F0 |
| Amber | amber #BD760A, ink #8A4B06, pill #FBF0DC |
| Indigo | indigo #5457D6, ink #3F3CB8, pill #ECEBFC |
| Priority | P1 #B42318, P2 #B54708, both with light text; P3 #E6ECED with #2E3E48; P4 surface with a 1px #CBD5D7 inset |
| Neutral | pill #EDF1F3, ink #465661 |
| Navy | selected chip #152C39 with #F3F6F6 text |

Status pills: Open is indigo, In progress is teal, Pending is amber, Resolved is neutral.

**Type.** Inter 400 to 800 through `next/font`, 14px with line height 1.5, tabular figures (`tnum`, `cv11`). Page titles 28px bold (24px on phones).

**Shape.** Cards 16px radius, rows 12px, controls 10px, pills 999px. Focus is a 3px solid teal ring, `--focus-ring`, with a transparent outline that forced colours paint in its place.

## 3. Frame

- A 3px teal rule on top of the page.
- **Skip link**, off-screen until the Tab key reaches it: the first stop on every page, moving focus to the column.
- **Sidebar**, 232px and sticky: logo at 24px high, Workspace links (Tickets, Customers, Knowledge, Reports, Company) and Settings at the bottom. Items are 44px high; the active one has a teal wash and a 3px inset bar.
- **Top bar**, at least 68px high: a search box up to 480px wide and a "View only" badge.
- **Page**, up to 1120px wide, padding 40px 32px 64px, gap 32px. Detail pages use 36px at the top and a 28px gap.

## 4. Pages

| Route | Board | Data |
|---|---|---|
| `/` | Main | `/api/tickets`, reports `backlog`, `first-reply`, `priority`; `/api/search` for `?q=`; one ticket for the preview |
| `/tickets/[ticketId]` | Case | `/api/tickets/{id}` |
| `/customers` | Customers | `/api/customers` |
| `/customers/[customerId]` | Customer | `/api/customers/{id}` |
| `/knowledge` | Knowledge | `/api/knowledge` |
| `/knowledge/[articleId]` | Article | `/api/knowledge/{id}` |
| `/reports` | Reports | the five `/api/reports/*` routes |
| `/company` | Company | `/api/company` |
| `/settings` | Settings | `/openapi.json`, `/api/tickets` |

**Queue.** A pulse of desk-wide figures from the reports, then the 25 tickets of the current page in lanes. Lanes, counts and filters cover that page and say so. Selecting a row opens a preview with the service targets and an "Open case" link; it is fetched through a server action so the token stays on the server. Previous and Next move between pages.

**Search.** Typing filters what is on the page. Enter on the queue, or on any page with the ticket search, opens `/?q=words`, which searches the whole desk through `/api/search` and lists tickets and articles. `/` focuses the search box where the design shows the key.

**Case.** The clock draws both targets and both actual times on one axis whose end is 1.055 times the largest value. Close labels fall back to a stacked legend, which is also the phone layout. A missing first reply, an unresolved ticket and a missing target each have their own wording. Customer messages are headed by the company and agent messages by the agent ID.

**Customers.** All accounts in one response, filtered on the client by plan, region and words, 20 more at a time. Active cases are tickets that are not resolved.

**Customer.** Account and subscription details, invoices (shown in order, without months), support history with assigned agent and team, and tickets by component. Every invoice shows its own seats and price, because these change between invoices on some accounts.

**Knowledge and Article.** A filterable list; each article shows its body, the tickets with the same subject (up to 5 and the total), and more articles in its category.

**Reports.** Each section stands on its own: if one report fails, the others still show. Total rows are read as totals, never drawn as a bar. Headlines come from `web/lib/report-text.ts`.

**Company.** Handbook sections with owner and team, then staff requests. The database stores the owner as "Name · Team"; the API splits it.

**Settings.** What the desk is connected to, read live. The token is never shown.

## 5. States

- **Loading.** Each list and board route has a `loading.tsx` using `PageLoading`: a pulsing outline of the page, announced to screen readers. The pulse stops under `prefers-reduced-motion`. Ticket, customer and article pages have none, and no `loading.tsx` may sit above them, which is why the lists keep theirs in route groups: a loading state starts the stream and fixes the status at 200, so a missing record could not answer 404. While one of those pages opens, `DetailPending` shows a thin bar at the top of the window and announces the same wait to screen readers.
- **API errors.** `ApiProblemPanel` replaces the data and keeps the heading. It shows the message, the code and a button that names what it reloads, such as Reload the ticket queue.
- **Crashes.** Each route has an `error.tsx` boundary.
- **Not found.** Tickets, customers and articles have their own page and tab title, and a 404 or 422 from the API lands there.
- **Empty.** Every filtered list says nothing matched and how to recover.

## 6. Phones

Below 800px the sidebar becomes a strip above the page: logo, then six links with the icon over the label, all in view, each at least 44px high. The page never scrolls sideways; wide content scrolls inside its own box. The search box takes a full row and the `/` hint goes. Details rails drop under the main column. Chips, buttons and toggles grow to 44px.

## 7. Code

- `web/app/globals.css`: tokens, frame and shared pieces. Styles for one page sit beside it, such as `web/app/customers/customers.css`, with classes prefixed for that page.
- `web/components/desk.tsx`: top bar, headings, pills, tiles, facts, error panel, loading.
- `web/components/search.tsx`: the search box. `web/components/icons.tsx`: the stroke icons.
- `web/lib/api.ts`: the server-only client and the response types. It leaves out the timestamps and contact emails that older routes still return.
- `web/lib/format.ts`: display helpers.

## 8. Changes from the design

The boards decide the look. These are the places the desk differs from them, and why.

**Queue**

- The sample limits are gone: every row links to its case and every row previews. The hard-coded "Full case" card is dropped.
- Real Previous and Next paging is added.
- Enter in the search box runs the desk-wide `/api/search` and shows the results at `/?q=`. Those rows have no customer, agent or channel, because a search hit does not carry them. The pulse stays above the results.
- A "Status or priority not recorded" lane is added, and each empty lane says so in one line.
- The first ranked ticket is preselected, so each load makes one preview call. On a phone, picking a row scrolls to the panel.
- An unresolved ticket's preview reads "First reply none yet" or "Resolution not yet". "Not recorded" is kept for closed tickets.

**Search on other pages**

- Ticket search goes to `/?q=`. Article search goes to `/knowledge?q=`.

**Case**

- The priority uses the shared priority tile. The frustrated and positive sentiment tones are ours.
- The company name links to the customer. The contact line is removed.
- The clock uses a stacked legend when its labels would collide. That is about 39% of tickets, estimated, even at desktop width. The axis maximum rounds up to 0.1h.
- A ticket with no messages shows its body instead.

**Customer**

- Invoice tiles sit in two columns, each with its own seats and price, under "Paid X of Y". No months are shown.
- Ticket search covers subject, ID and component. The board also searched assignee and team.
- Rows are clickable across their full width.

**Knowledge and Company**

- Every customer ID and article row links.
- Related tickets are limited to 5, with "Showing N of TOTAL".
- Company contents stay sticky only at 1120px and wider.
- Phone ticket rows use a single line.

**Reports**

- The board's "At every priority" headline is false for this data (P1 is 65%), so the page prints "About 6 in 10 on time, 59% to 65% by priority". The other four headlines hold.
- The backlog stays in API order.
- "No first reply" reads "past target, of 24 unanswered". The 24 comes from the API.
- The hero note adds the unrated counts. The footnote says dates are left out. Periods are numbered.
- A Show tables toggle is added.

**Settings**

- The page lists 14 routes, not 9.
- The database pill follows the ticket read.
- A "Not answering" state is added.
- The label column narrows on phones.

**Phone layout**

- The boards have no phone layout, so this one is ours: a strip of six links above the page, in two rows under 375px, with 44px touch targets.
