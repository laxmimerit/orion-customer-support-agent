# Orion desk frontend

Next.js app for the Orion desk: the ticket queue (`/`), a case page per ticket (`/tickets/T00727`), Customers, Knowledge, Reports, the Company handbook and Settings. It follows `notes/DESIGN.md`.

- Every value comes from the read-only desk API in `api/`, never from `notes/design-data`. No emails, dates or times are shown.
- Pages render on the server. `lib/api.ts` is `server-only`: it reads `ORION_API_URL` (default `http://127.0.0.1:8000`) and `ORION_AGENT_TOKEN` from the environment, then from the repository's `.env`. The token is never sent to the browser, and the admin token is not read. The queue's preview reads through a server action for the same reason.
- Search on the queue uses the API's `/api/search`. It needs the API's local embedding model, so the first search after a start is slower.
- Mail, language models and other connections are not set up; Settings says so and offers no controls.

Run the API first (`orion-api` in `.claude/launch.json`), then:

```sh
npm install --prefix web
npm run --prefix web dev
```

and open http://127.0.0.1:3000. `npm run --prefix web typecheck` and `npm run --prefix web build` check the code.
