# DESIGN.md: Orion ticket queue and case page prototype

This describes two artboards, **Ticket queue** and **Case page T00727**, built on the Orion design system. Anything the design system does not define, or that goes beyond it, is marked **Ours**. Everything else is taken from the system as it is.

## 1. Sources

| Source | What it supplied |
|---|---|
| Orion design system, `project/README.md` | Voice, logo rules, colour roles, type scale, spacing, shape, layout widths, iconography |
| Orion design system, `project/tokens.json` | Every colour value, in two themes: `Live site` and `Ours: 4.5:1 text` |
| Trace of ticket T00727 (read-only queries on the `orion_lab` database) | Every value shown on either page |
| Attached `orion-logo.png` | The logo, used unaltered |

Only values from the trace appear. Where the trace does not hold a detail, the page says "not in trace". No dates or times appear on either page.

## 2. Themes

The design system has two themes. The artboards expose a **Theme** tweak.

- **Ours: 4.5:1 text** (default). This is the design system's own proposal: the 24 text colours that fall short of 4.5:1 are darkened, keeping their hue. All other tokens are identical to the live site.
- **Live site**. The exact production values.

**Ours:** defaulting to the 4.5:1 theme. The README says to use it only where the proposal is accepted, so switch the tweak to `Live site` if it is not. The larger 15px body text from the same proposal (`body-ours`, `message-body-ours`) is **not** applied; body text stays at the live 13px.

## 3. Tokens

Names below are the design system's token names. In the files they are CSS variables on the `.orion` root (for example `--ink`, `--b-panel`), with `.orion.is-live` overriding the values that differ on the live site.

### 3.1 Brand and logo

| Token | Value | Source | Use here |
|---|---|---|---|
| `teal` | #098278 | tokens.json | 4px stripe on top of the masthead |
| `teal-indicator` | #178278 | tokens.json | Inset bar on the active sidebar item |
| `logo-teal`, `logo-navy` | #087f78, #152e3b | tokens.json | Belong to the logo file only; not used in markup |
| `focus` | #bd7200 | tokens.json | 3px solid outline, 3px offset, on links, inputs, select and button |

### 3.2 Surfaces

| Token | Value | Use here |
|---|---|---|
| `surface-page` | #eef1f4 | Page background |
| `surface` | #ffffff | Masthead, panels, stat strip, inputs, active nav item |
| `surface-sidebar` | #e3e9ed | Sidebar |
| `surface-toolbar` | #e4eaee | Search and filter toolbar |
| `surface-panel-heading` | #f6f8f9 | Panel headings, prototype notice |
| `surface-table-head` | #edf2f5 | Ticket list header row |
| `surface-row-even` | #fafbfc | Zebra rows |
| `surface-row-hover` | #f0f6f7 | Row hover |
| `surface-nav-hover` | #f0f3f5 | Sidebar item hover |
| `button` | #486b80 | Reset button fill, white label |
| `button-border` | #3d6074 | Reset button border |

All from tokens.json, same in both themes.

### 3.3 Text

| Token | Live site | Ours | Use here |
|---|---|---|---|
| `ink` | #253c4a | same | Default text, page title |
| `ink-strong` | #213f50 | same | "Service Desk" |
| `ink-stat` | #344f60 | same | Stat numbers |
| `ink-message` | #425a69 | same | Message bodies |
| `ink-fact` | #3b5665 | same | Fact values |
| `link` | #186b86 | same | Links; underline on hover only |
| `subject` | #254f65 | same | Ticket subject |
| `account` | #2f596d | same | Customer name |
| `nav-text`, `nav-active` | #3e5665, #17586a | same | Sidebar text, active item |
| `nav-icon` | #6f838e | same | Sidebar glyphs |
| `text-product-sub` | #647883 | same | "Customer operations" |
| `nav-label` | #6c7f89 | #5a6a72 | Sidebar group labels |
| `nav-count` | #607682 | #566a75 | Sidebar counts |
| `breadcrumb` | #7a8b96 | #626f78 | Breadcrumb |
| `breadcrumb-separator` | #a0adb6 | same | The slash |
| `text-page-description` | #647782 | #5e6f7a | Page description |
| `text-muted` | #687c88 | #5d6f7a | Notes under panels |
| `text-stat-label` | #6d7e87 | #687881 | Stat labels |
| `text-toolbar-label` | #546b79 | same | Toolbar labels and hint |
| `text-caption-meta` | #718490 | #63737e | Panel and table meta text |
| `text-table-head` | #5f7582 | #5b707d | List column headers |
| `text-ticket-number` | #6d8592 | #617682 | Ticket number above the subject |
| `text-cell-sub` | #7b8d97 | #66757d | Second line in list cells |
| `text-case-ribbon` | #6c818c | #5d7079 | "account access · Identity · Via web" |
| `text-fact-label` | #7a8d98 | #687881 | Fact labels |
| `text-time` | #7c8e98 | #697880 | Author line in messages |
| `text-footer` | #83939d | #636f77 | Footer |
| `on-button` | #ffffff | same | Button label |

Source for every row: tokens.json. The "Ours" column is the design system's own 4.5:1 proposal, not something added here.

### 3.4 Status, priority and outcome

| Token group | Values | Use here |
|---|---|---|
| `status-*` Open | text #456578, fill #eaf4f8, border #c3d2da, dot #688793 | T01917 |
| `status-progress-*` | text #62799b (Ours #596e8d), fill #edf1f8, border #cbd5e5, dot #688793 | T00723, T03087 |
| `status-pending-*` | text #8c754d (Ours #7f6a46), fill #f6f1e9, border #dfd3bc, dot #ad8a4e | T01839 |
| `status-resolved-*` | text #527360, fill #eef4ef, border #c7d8cb, dot #71957b | T00727 |
| `priority-*` default | text #72828b (Ours #66747c), fill #f7f9fa, border #d3dce2 | P3, P4 |
| `priority-p2-*` | text #9b7947 (Ours #896b3f), fill #faf5e9, border #e5d6b8 | P2 on T00727 |
| `outcome-missed-*` | text #a27042 (Ours #94663c), fill #fcf5eb, border #e8d6bd | Missed first-reply and resolution targets, and the wait bar |
| `avatar-*` | text #526f7f (Ours #4e6a79), fill #dce7ec, border #c4d3dc | Customer avatar |
| `avatar-agent-*` | text #5f7f70 (Ours #536e61), fill #e1ece7, border #c9dbd1 | Agent avatar |
| `dot-open`, `dot-in-progress`, `dot-pending`, `dot-resolved` | #337ca1, #b58b36, #9a8170, #759183 | Sidebar queue dots |

Source: tokens.json. A status or priority always shows its word; colour only supports it. Not used on these pages: `priority-p1-*`, `outcome-*` (target met), `status-text`, `link` variants for the account name.

### 3.5 Borders

`border-masthead` #bdc9d1, `border-brand-divider` #d5dce1, `border-tag` #bbc8ce, `border-sidebar` #becbd3, `border-nav-active` #c1cdd5, `border-heading` #cbd5dc, `border-panel` #c3cfd7, `border-stat-divider` #d8e0e5, `border-toolbar` #c0ced7, `border-input` #a8b9c5, `border-caption` #cbd6de, `border-row` #dce3e8, `border-cell` #edf1f4, `border-facts` #e9eef1, `border-message` #dce5ea. Source: tokens.json, one per role, 1px.

### 3.6 Type

One family: `sans`, Arial, Helvetica, sans-serif. No web fonts. Source: README and tokens.json.

| Style | Size, weight | Use here |
|---|---|---|
| `page-title` | 25px, 400 | Page title |
| `stat-value` | 25px, 400 | Summary numbers |
| `product-name` | 18px, 700 | "Service Desk" |
| `panel-title` | 13px, 700 | Panel and table headings |
| `body` | 13px, line height 1.7 | Page description, request summary |
| `message-body` | 13px, line height 1.85 | Conversation |
| `nav-item` | 13px | Sidebar items, bold when active |
| `ui` | 12px | Table cells, fact values, Reset button |
| `small` | 11px | Breadcrumb, ribbon, notes |
| `label` | 11px, 700 | Toolbar labels |
| `overline` | 10px, 700, 1.2px tracking | Sidebar group labels, the PROTOTYPE tag |
| `table-head` | 10px, 700, 0.5px tracking | Column headers |
| `badge` | 10px | Status pills, ticket numbers (bold, 0.3px), fact labels |

Two sizes are used beyond the scale: **Ours:** the 20px figures in the case page's service-target tiles, and 13px bold for the wait value in the list. Both stay inside the scale's range.

### 3.7 Spacing, shape, layout

| Token | Value | Source |
|---|---|---|
| Masthead | 77px high plus 4px teal stripe | `masthead-height` |
| Sidebar | 215px | `sidebar-width` |
| Case sidebar | 280px, up to 320px | `case-sidebar-width` |
| Content padding | 26px 30px 34px | `space-30` and README |
| Panel and column gap | 22px | `space-22` |
| Control height | 34px | `control-height` |
| Avatar | 31px square | `avatar-size` |
| State dot | 6px round | `state-dot-size` |
| Radius | 0 on panels, 2px on controls, pills and chips, 50% on dots only | `radius-*` |
| Shadow | none, except the inset teal bar on the active nav item | `nav-active-indicator` |
| Focus | 3px solid `focus`, 3px offset | `focus-ring-width` |

## 4. Shared frame (both pages)

- **Masthead.** The attached logo at 120 × 30, never recoloured or redrawn, then 26px of clear space to a `border-brand-divider` rule, then "Service Desk" over "Customer operations". The 4px `teal` stripe sits on top.
- **Ours: PROTOTYPE tag.** Right-aligned in the masthead, in the style of the system's small bordered "CLASSIC" tag. It replaces that tag.
- **Sidebar.** WORKSPACE group: Tickets (active), Customers, Knowledge, Reports, Company, with the system's block glyphs. Tickets links to the queue; the others are not wired.
- **Ours: ACCOUNT ACCESS VIEWS group.** Four queue views with dots and counts from the trace: Open 20, In progress 21, Pending 29, Resolved 456. The group label says which category the counts cover. These are display only.
- **Ours: prototype notice.** A `surface-panel-heading` strip under the page heading saying every value comes from a read-only trace and that missing details read "not in trace".
- **Ours: footer note.** States that targets and waits are in hours.

Not carried over from the live site: header links, the workspace initial square and its sub-line, and the sidebar footer, because the trace holds no real values for them.

## 5. Components

| Component | Description | Used on |
|---|---|---|
| Masthead | See section 4 | Both |
| Sidebar nav | Active item has white fill, `border-nav-active` and the inset teal bar | Both |
| Page heading | Breadcrumb, 25px normal title, 1px `border-heading` rule underneath | Both |
| Prototype notice | **Ours.** See section 4 | Both |
| Stat strip | Four stats in a white bordered row, hairline dividers | Queue |
| Toolbar | Toolbar fill and border, labelled search input and status select, slate Reset button | Queue |
| Ticket list | Zebra grid inside a horizontally scrolling box. Built as `role="table"` divs on a shared column template, not an HTML table | Queue |
| Status pill | 2px radius, 6px dot, word always shown | Both |
| Priority chip | 2px radius, bold | Both |
| **Ours: wait bar** | 6px bar with a 2px target tick. Track length is the larger of wait and target, so the tick shows where the target fell. Decorative (`aria-hidden`); the figures and the words "Past target" carry the meaning | Queue |
| Panel | White, 1px `border-panel`, heading strip with bottom rule | Case |
| Outcome note | Missed-outcome fill, text and border | Case |
| **Ours: service-target tile** | Outcome note extended with Target and Waited/Took figures and the same bar | Case |
| Message | 31px avatar, author, role and message number, body in `ink-message` | Case |
| Facts list | `dl` with 10px labels, 12px values, `border-facts` rules | Case |

## 6. Ticket queue: layout

Artboard 1280 wide, fluid page. Frame: masthead, then a wrapping row of sidebar and main. Main stacks, top to bottom:

1. Page heading: breadcrumb "Tickets / Ticket queue", title, one-line description.
2. Prototype notice.
3. Stat strip: 526 account access tickets; 17.65 h average first reply; 522 with a first reply; 4 with no first reply yet.
4. **Ours: average caveat.** One note stating the 17.65 h average covers only the 522 replied tickets and that the 4 unanswered tickets are already past their targets.
5. Toolbar: search, status select, Reset, and a hint that word forms match.
6. Ticket list, with a caption showing "n of 5 tickets shown" and how to read the bar.
7. Footer note.

List columns, left to right: **Ticket / subject**, **Customer**, **Status**, **Priority**, **Agent**, **First-reply target**, **Time waited**. The target sits directly beside the wait. The wait cell holds the value, "Past target" or "Within target", the bar and a note ("until the first reply" or "no reply yet, at data snapshot"). Rows are sorted by longest wait first.

Behaviour (the artboard is interactive):

- **Ours: word-form search.** Words are reduced to a stem (endings such as -ation, -ing, -ed, -es, -e, -s are removed) and a query word matches any word in the ticket that equals it or begins with it. "invite", "invited" and "invitation" all find T00727. It searches ticket number, subject, request text, customer, company, status, priority, agent and channel.
- Status select filters by status. Reset clears both.
- The T00727 subject links to the case page. The other four have no case page in this prototype.
- Empty state: "No tickets match." with how to recover.

Narrow widths: the list scrolls sideways inside its box; stats and toolbar wrap; the sidebar stacks above the content.

## 7. Case page T00727: layout

Artboard 1280 wide, fluid page. Same frame as the queue. Main stacks:

1. Page heading: breadcrumb "Ticket queue / T00727" (the first part links back), title "T00727 · Invite link expired", ribbon "account access · Identity · Via web".
2. Prototype notice, which also says messages are shown in order without times.
3. A two-column row that wraps. Left column is flexible, right column is 280px (up to 320px) and drops below the left column at narrow widths.

**Left column**

- **Request summary.** The ticket body, 13px, line height 1.7.
- **Ours: service targets.** Two tiles side by side. First reply: target 3 h, waited 7.96 h, target missed. Resolution: target 24 h, took 25.58 h, target missed. Each has the wait bar and target tick, and a one-line key beneath.
- **Conversation.** Five messages, oldest first, with a header showing the count. Customer messages carry the customer avatar ("FP"), agent messages the agent avatar ("A03"). Each shows the author, role and message number, and no time. The two agent replies are the same text as stored, and the two follow-ups end with "Follow-up 2" and "Follow-up 3" as stored.

**Right column**

- **Ticket.** Status Resolved, priority P2, assigned to A03, channel web, category account access, component Identity, sentiment urgent, CSAT 4, reopened 0, escalated 0.
- **Customer.** Fern Platform 086; customer id C0086; plan scale with 8 seats; Finance tools; company size 11-50; United States and Americas; acquired through search; contact contact086@example.com; 18 tickets from this customer.

## 8. Summary of what is ours

1. Default to the system's `Ours: 4.5:1 text` theme, with a Theme tweak back to `Live site`. The larger 15px body text is not applied. This is Assumption 2 in requirements.md, still a guess.
2. PROTOTYPE tag in the masthead, a prototype notice on both pages, and "not in trace" wording for missing details.
3. Account access views group in the sidebar, with counts from the trace and a label that scopes them.
4. Word-form search on the queue.
5. First-reply target beside time waited in the list, with the wait bar and target tick, and the past-target words.
6. Average caveat under the stat strip.
7. Service-target tiles on the case page.
8. Ticket list built from role-annotated grid rows instead of an HTML table, so it can render and filter live inside the artboard.
9. Page-level choices with no system equivalent: sort by longest wait, the footer note, and omitting header links, the workspace square and the sidebar footer.

## 9. Not covered by the trace

Subjects, companies and request text for T01917, T01839, T00723 and T03087; any case page for those tickets; message times; and any ticket beyond the five shown. These are left out or marked "not in trace" rather than invented.