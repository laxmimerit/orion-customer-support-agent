# Communication contract: customer mail

- **Status:** The desk checks the customer mailbox, and copies mail under the label into its own tables (sections 7 and 8). It cannot send, and has no draft or send route. Everything else here is still contract only.
- **Applies to:** reply drafting (plan increment 11, backlog B15) and every later feature that sends or receives customer mail.
- **Sources:** [`notes/backlog.md`](../notes/backlog.md) (B15, M03, M06, M07), [`notes/plan.md`](../notes/plan.md) (increment 11, assumption A3), the `orion_desk` data, `AGENTS.md` and `README.md`.

Rules marked **Proposal** come from this document, not from the handbook or the backlog. They need your agreement before the code that depends on them is written.

## 1. What the data holds today

Counted in `orion_desk` through the read-only API connection.

| Fact | Value | What it means for mail |
|---|---|---|
| Message authors | `author_role` is `customer` (19415) or `agent` (17279). Messages carry no agent ID, sender address, recipient, subject or thread header | A sent reply can be stored as an `agent` message, but who approved it must live somewhere else |
| Ticket channels | `email` 1000, `web` 1020, `API` 1037, `chat` 943 | Three in four tickets did not arrive by mail |
| Customer contacts | One `contact_email` per customer, 300 distinct, all at `example.com` | `example.com` is reserved and receives no mail. Nothing in the data is a real mailbox |

## 2. Rules every mail feature keeps

| # | Rule | Source |
|---|---|---|
| C1 | Nothing is sent automatically. No timer, retry, rule or model output sends a message on its own. | M03, REQ004 |
| C2 | A named person approves every outgoing message. The approval covers the exact recipient, subject and body. Any edit after approval returns the message to draft. | M03 |
| C3 | The shared `ORION_AGENT_TOKEN` and `ORION_ADMIN_TOKEN` identify a role, not a person, so they cannot approve mail. Approval waits for per-person sign-in. | M03; **Proposal** |
| C4 | A draft answers every question in the customer's messages, uses only facts from the ticket, its messages, its customer record and the articles or tickets it cites, and lists those sources. | B15, REQ004 |
| C5 | A draft states what is not known instead of guessing. When there is no relevant evidence, the desk says so and makes no draft. | B15, REQ004 |
| C6 | A missing value is never written as zero. "Not recorded" stays "not recorded" in a draft. | M07 |
| C7 | Every subject the desk sends carries the ticket ID in square brackets, for example `[T00727]`. Inbound mail links by one known ticket ID in its subject, or by replying to a linked mail (section 8). | **Proposal**; M01 |
| C8 | The only recipient is the ticket's customer `contact_email`. Addresses found in message bodies are never used, and there is no CC or BCC in the first version. | **Proposal** |
| C9 | Mail state is written to `orion_desk` only, never to `orion_lab`. Existing rows are never edited; a sent reply is added as a new `messages` row with `author_role = 'agent'`. | M06 |
| C10 | Every state change is logged with who made it and when, and the log can be exported. A rollback to the legacy desk can then account for every message sent from the new one. | Plan A3 |
| C11 | Outside production, mail goes only to a capture mailbox that never delivers. The development setup refuses to start if it would deliver to a real address. | **Proposal**; `example.com` contacts |
| C12 | Mail credentials live only in `.env` (for example `ORION_MAIL_*`), never in Git, `.claude/launch.json`, logs, error bodies or API responses. | AGENTS.md, README.md |
| C13 | Timestamps are stored and returned in UTC with a trailing `Z`, as in the read-only API. | ADR 0001 check 5 |

## 3. Life of an outgoing message

| State | Entered when | Who | Next states |
|---|---|---|---|
| `draft` | A draft is made, or an approved message is edited | Agent, or the drafting assistant on an agent's request | `approved`, `discarded` |
| `approved` | A named person approves the exact text | Approver (C2, C3) | `sending`, `draft` (on edit) |
| `sending` | The desk hands the message to the mail provider | System, only from `approved` | `sent`, `failed` |
| `sent` | The provider accepts it; a new `agent` message is added to the ticket | System | none |
| `failed` | The provider refuses it or does not answer | System | `draft` (a person must approve again) |
| `discarded` | A person drops the draft | Agent | none |

A failed message is never retried automatically (C1).

## 4. API shape (Proposal)

All routes sit under `/api`, use bearer tokens and return errors in the same JSON shape as the read-only API:

```json
{"error": {"status": 409, "code": "not_approved", "message": "Only an approved message can be sent."}}
```

| Method and path | Does | Allowed state |
|---|---|---|
| `POST /api/tickets/{ticket_id}/drafts` | Make a draft for the ticket, or answer `422 insufficient_evidence` (C5) | none |
| `GET /api/tickets/{ticket_id}/drafts` | List the ticket's drafts and messages in any state | any |
| `PATCH /api/drafts/{draft_id}` | Edit subject or body | `draft`, `approved` (returns to `draft`) |
| `POST /api/drafts/{draft_id}/approve` | Record the named approver | `draft` |
| `POST /api/drafts/{draft_id}/send` | Hand an approved message to the provider | `approved` |
| `POST /api/drafts/{draft_id}/discard` | Drop the draft | `draft` |

A draft record holds: `draft_id`, `ticket_id`, `to`, `subject`, `body`, `sources` (each with a kind of `ticket`, `message` or `article` and its ID), `unknowns`, `status`, `created_by`, `approved_by`, `approved_at`, `sent_at`, `provider_message_id` and `error`.

## 5. Checks that prove it

1. No route or job moves a message to `sending` unless its state is `approved` and `approved_by` names a person (C1, C2).
2. Editing an approved message sets it back to `draft` and clears `approved_by` (C2).
3. The shared tokens cannot approve (C3).
4. A draft for T00727 cites the tickets and article it used (for example KB004 or KB034), and a ticket with no relevant evidence gets `insufficient_evidence` and no draft (C4, C5).
5. A draft for a ticket with no recorded satisfaction says "not recorded", never 0 (C6).
6. Sending to `contact086@example.com` in development lands in the capture mailbox and nowhere else (C11).
7. No write reaches `orion_lab`, and no existing `messages` row changes (C9).
8. A search of the repository, logs and API responses finds no mail credential (C12).

## 6. Open questions

1. How a person signs in, and who may approve: any agent, or a lead only? (C3)
2. Whether inbound mail should also sync on a timer. Today a person presses Sync mail (section 8).
3. Whether tickets that arrived by web, API or chat get mail replies, or a reply on their own channel.
4. Whether a person can link an unlinked mail by hand, or make a ticket from it. Today it waits on the Unlinked mail page.
5. How long drafts, discarded drafts and the state log are kept.

## 7. The mailbox connection today

`api/orion_api/mail.py` holds one check, reached through `GET /api/mail/status` and shown on the Customer mail card on Settings.

| Part | What it does | What it never does |
|---|---|---|
| IMAP, `imap.gmail.com:993` | Logs in, asks `STATUS` for the counts under `ORION_MAIL_LABEL`, logs out | Open the mailbox, read a subject or body, mark anything as read |
| SMTP, `smtp.gmail.com:465` | Logs in and quits | Name a sender or recipient, or hand over a message |
| The route | Returns each check's state, the label and its counts | Return the mailbox address or the password |

- The adapter has no method that sends, so C1 and C2 hold because there is no way to break them. Sending needs new code.
- C11 is not met yet. Before any send route exists, the capture mailbox must be built, because the settings in `.env` reach a real mailbox.
- The check runs at most once a minute. Other calls get the last answer, a failure included, so repeated calls can't trip Google's login limits. The cache is held per running API, so several Vercel instances each keep their own.
- Checks run with TLS and a verified certificate. There is no setting that turns this off.
- CI uses the fake servers in `api/tests/fake_mail.py`. Only `api/tests/test_mail_live.py` reaches Gmail, and CI never runs it.

## 8. Inbound mail

`POST /api/mail/sync` opens the label read-only, fetches with PEEK and adds new mail to `mail_messages`, with any ticket link in `mail_links`. It is the desk's only write route, and it runs at most once a minute.

- **Login:** `tools/create_mail_writer.py` makes the only login that writes. It has `SELECT` and `INSERT` on those two tables and nothing else, so stored mail can't be edited or deleted. `Store` stays read-only.
- **Linking:** one known ticket ID in the subject, or a reply to a linked mail through `References` and `In-Reply-To`. Gmail's own thread ID is not used: it left a reply with a changed subject in a thread of its own.
- **Trust:** nothing checks the sender, so anyone can attach a mail to a ticket. The desk says so wherever it shows mail, and shows no address or date.
- **Ask:** the mail tools are read-only and offered only on a line marked `mail` (GPT-6 Luna), and not when web is ticked, so a planted mail can't steer a fetch. Mail is data, never instructions.
