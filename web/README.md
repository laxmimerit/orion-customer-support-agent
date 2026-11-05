# Orion desk frontend

Next.js app for the Orion desk: the ticket queue (`/`), a case page per ticket (`/tickets/T00727`), Unlinked mail (`/mail/unlinked`), Customers, Knowledge, Reports, the Company handbook and Settings. It follows `notes/DESIGN.md`.

- Every value comes from the desk API in `api/`, never from `notes/design-data`. No emails, dates or times are shown.
- Pages render on the server. `lib/api.ts` is `server-only`: it reads `ORION_API_URL` (default `http://127.0.0.1:8000`) and `ORION_AGENT_TOKEN` from the environment, then from the repository's `.env`. The token is never sent to the browser, and the admin token is not read. The queue's preview reads through a server action for the same reason.
- Search on the queue uses the API's `/api/search`. It needs the API's local embedding model, so the first search after a start is slower.
- Settings shows whether the API can reach the customer mailbox, with the counts under its label. It offers no controls, and the desk can't send mail. Triage and the Ask panel pick a model from the API's allow-list, and Settings shows that list read-only.
- Customer mail shows on the case page it is linked to, and Unlinked mail lists the mail that matched no ticket. Both show it as plain text with a line saying the desk has not checked it. Sync mail copies new mail into the desk. It is the one button that writes, and it sends nothing.

Run the API first (`orion-api` in `.claude/launch.json`), then:

```sh
npm install --prefix web
npm run --prefix web dev
```

and open http://127.0.0.1:3000. `npm run --prefix web typecheck`, `npm test --prefix web` and `npm run --prefix web build` check the code. The tests sit beside the code in `lib/` and run on Vitest, with no API or database.
