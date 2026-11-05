# Customer mailbox connection, 2026-11-05

Complaints reach a Gmail mailbox under one label, and the desk couldn't see it.

**Result: the desk reaches the real mailbox over IMAP and SMTP and shows it on Settings. It sends nothing and reads no message.** Only the counts under the label come back: 1 message, 0 unread on the day.

## Checks run

| Check | Where it ran | Result |
|---|---|---|
| Offline suite, the CI command | Fake mail servers on 127.0.0.1 | 654 passed, 52 live tests deselected |
| `tests/test_mail_live.py` | Real Gmail, login only | 1 passed: two separate logins, connected both times, counts unchanged |
| `GET /api/mail/status`, four calls in a row | Running API, real Gmail | `connected` each time: 4.09 s for the first, under 0.01 s for the other three |
| Customer mail card | Running desk, 800px wide | Connected, 1 message, 0 unread, no address on the page, no console errors |
| Same card, wrong password | Running desk, 375px wide | Login refused on both checks, counts not recorded, no sideways scroll |
| Web typecheck, tests, build | Local, build on a throwaway copy | Clean, 523 passed, build passed |
| Leak scan of the password and address | Response, API docs, logs, settings repr, 214 repository files, the diff | Found in none |
| Security review | Read the code only | No Critical or High findings |

## What the real server showed that the fake did not

The first version reported a wrong password as `not_answering` on SMTP. `smtplib`'s `login()` tries PLAIN, then LOGIN. Gmail refuses PLAIN with 535 and hangs up, so the LOGIN attempt fails with `SMTPServerDisconnected`, and that replaces the refusal.

The fake had passed this, because it advertised only PLAIN and stayed connected. Two changes followed:

- `mail.py` now authenticates with PLAIN once, through `client.auth()`.
- The fake advertises both methods and hangs up after a refusal. With the old `login()` put back, 3 tests fail.

## One check a minute

The security review found that every call logged in to Gmail afresh, so anyone with the agent token could trigger a stream of logins. Google can throttle or lock an account for that, and repeated refused logins are the worst case.

`Mailbox.status()` now keeps its answer for 60 seconds, a failure included, and callers who arrive during a check share it. Taking the cache out fails 4 tests, and taking the lock out fails 1. A change to the mailbox can take up to a minute to show on the card.

## Not checked

- **The deployed desk.** `ORION_MAIL_*` are not on Vercel, so its card will read Not set up. Whether a Vercel Function can reach ports 993 and 465 is unknown.
- **Gmail's Sent folder.** "Nothing sent" rests on the adapter having no send method and on the fake's record of every command, not on a look at the folder.
- **Gmail's login limits.** The actual limit was not tested. The cache is held per running API, so several Vercel instances would each check once a minute.
