# Orion desk frontend

Next.js app for the Orion Service Desk: the ticket queue (`/`), a case page per ticket (`/tickets/T00727`) and Settings (`/settings`). It follows `notes/DESIGN.md` and the Orion design system tokens in its "Ours: 4.5:1 text" theme.

- Every value comes from the read-only desk API in `api/`. No dates or times are shown, and there is no search yet.
- Pages render on the server. `lib/api.ts` is `server-only`: it reads `ORION_API_URL` (default `http://127.0.0.1:8000`) and `ORION_AGENT_TOKEN` from the environment, then from the repository's `.env`. The token is never sent to the browser, and the admin token is not read.
- Mail, language models and other connections are not set up; Settings says so and offers no controls.

Run the API first (`orion-api` in `.claude/launch.json`), then:

```sh
npm install --prefix web
npm run --prefix web dev
```

and open http://127.0.0.1:3000. `npm run --prefix web typecheck` and `npm run --prefix web build` check the code.
