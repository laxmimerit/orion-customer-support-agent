---
name: verify
description: How to run and drive the Orion desk to verify a change at the running app.
---

# Verify the Orion desk

Start `orion-api` (port 8000) and `orion-web` (port 3000) from `.claude/launch.json` with `preview_start`.

## Flows worth driving

- Search: type in the top box on `/` (filters the page), press Enter (goes to `/?q=...`, calls `/api/search`). Open a ticket and an article result. Press `/` on `/reports` to reach the box from another page.
- Reports: `/reports`, then Show tables. Check phone width too, because strip notes are placed for a 375px layout.
- API calls need `Authorization: Bearer` with `ORION_AGENT_TOKEN` from the repo's `.env`. Never print it.

## Comparing against main

To prove "rendered output is unchanged", run a second copy of `web` from `git archive`, and compare it with the same page on this branch:

- Copy `node_modules` with `cp -Rc`. Turbopack rejects a symlink and answers 500.
- `next dev` locks its folder, so use one copy per running server.
- Put the `ORION_AGENT_TOKEN` line in `.env` one level above the copy's `web`, where `settings()` in `web/lib/api.ts` looks. Without it the page shows `missing_token`.
- Pages stream: the `<main>` in curl output is only the loading fallback. Compare the `<div hidden id="S:n">` blocks, or `main.innerHTML` in the browser.
- Check the size first. A tiny matching diff usually means both sides failed or only the fallback was compared.
- Front a tab before clicking: background tabs may not have hydrated, so a click does nothing.

## Error paths

Set `ORION_API_URL` on a copy to a stub that answers 200 with HTML to reach the non-JSON failure in `web/lib/api.ts`.

Add temporary servers to `.claude/launch.json`, then restore it. Keep secrets out of that file.
