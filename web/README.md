# Orion desk frontend

Next.js app for the Orion Service Desk: the ticket queue with search (`/`), a case page per ticket (`/tickets/T00727`) and Reports (`/reports`). It follows `notes/design-brief.md`.

- Every value comes from the read-only desk API in `api/`. No dates or times are shown.
- The queue ranks the 25 tickets on the current page by status and priority (`lib/ranking.ts`). Which tickets are on a page stays as the API returns them.
- Pages render on the server. `lib/api.ts` is `server-only`: it reads `ORION_API_URL` (default `http://127.0.0.1:8000`) and `ORION_AGENT_TOKEN` from the environment, then from the repository's `.env`. The token is never sent to the browser, and the admin token is not read.
- Settings (`/settings`) is not in the top bar. Mail, language models and other connections are not set up; it says so and offers no controls.

Run the API first (`orion-api` in `.claude/launch.json`), then:

```sh
npm install --prefix web
npm run --prefix web dev
```

and open http://127.0.0.1:3000. `npm run --prefix web typecheck` and `npm run --prefix web build` check the code.
