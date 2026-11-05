# MCP route and reply voice, 2026-11-05

Arun asked for the agent to write like the team and reach Orion from anywhere.

**Result: the agent reaches a ticket on a Vercel preview, with two secrets.** It sends the automation bypass secret to pass Vercel's login wall and `ORION_MCP_TOKEN` to pass the route. No protection setting was changed.

## The login wall

The project has Vercel Authentication on every deployment (`ssoProtection.deploymentType: all`). Checked on the newest section-12 preview, `orion-customer-support-agent-iv71kryib-kgp-talkie.vercel.app`, commit `f361eb8`, which doesn't contain this route:

| Request | Answer |
|---|---|
| `GET /`, `/docs`, `/api/snapshot`, `/api/tickets/T00727`, no credentials | 302 to `vercel.com/sso-api`, `server: Vercel` |
| `GET /api/snapshot`, made-up bearer token | 302 to `vercel.com/sso-api` |
| `POST /api/mcp`, made-up bearer token | 401, `server: Vercel` |

**That last 401 is Vercel's, not the route's.** This deployment has no such route. While the wall is up, a 401 from a preview says nothing about the bearer check, so it can't be used as proof of refusal.

## On the preview

Deployment `dpl_41yWLxwrGoqdMMx8sucmEJhskM5B`, commit `d0816fd`, `orion-customer-support-agent-npiow2rsb-kgp-talkie.vercel.app`. `ORION_MCP_TOKEN` is set for preview on `section-12` only, so production doesn't have it.

| Request | Who answered | Answer |
|---|---|---|
| POST `/api/mcp`, nothing sent | Vercel | 401 "Protected by Vercel Authentication" |
| Bearer token, no bypass | Vercel | The same |
| **Bypass, no bearer token** | **The route** | **401 `missing_token`** |
| Bypass, wrong bearer token | The route | 401 `invalid_token` |
| Bypass and bearer token, `GET` | The route | 405 `method_not_allowed` |
| Bypass and bearer token, `/api/tickets/T00727` | The web service | 404, so the rewrite opens `/api/mcp` alone |
| Bypass and bearer token, `tools/list` | The route | 200, `read_ticket` only |
| Bypass and bearer token, `read_ticket` T00727 | The route | 200, subject "Invite link expired", 5 messages, no `@` in the text |

The refusal is the third row: the body is the route's own error, not Vercel's.

`python -m triage_agent draft T00727 --approver "Arun"` then ran with the preview as its only MCP server. The draft passed every check, and no secret appeared in its output. "Arun" was a test input, not an approval. Vercel's runtime logs for this deployment were empty, as the app logs nothing per request, so they neither confirm nor contradict the agent's fetch.

## On this machine

The real route on a local socket, reading the real `orion_desk` through the read-only login, with a throwaway token.

| Request to `POST /api/mcp` | Answer |
|---|---|
| No token | 401 `missing_token` |
| Wrong token | 401 `invalid_token` |
| The desk's agent token | 401 `invalid_token` |
| The right token, `tools/list` | 200, `read_ticket` only |
| The right token, `read_ticket` T00727 | 200, subject "Invite link expired", 5 messages, no `@` in the text |
| `GET` with the right token | 405 `method_not_allowed` |

## The agent, end to end

`draft` for T00727 on `nvidia/nemotron-3-ultra-550b-a55b:free`: the skill loaded from `plugins/orion-kit`, the ticket came through the route, 4 turns, no other model answered, real spend $0.00 within the run's limit.

| Run | Approver given | Result |
|---|---|---|
| 1 | "Rehearsal only, no approver named" | `draft_invalid`, text not captured |
| 2 | The same | Output lost to a mistake in the command that filtered it, so its result is unknown |
| 3 | The same | `draft_invalid`. The model left the approval line as a question, as the skill says to when nobody is named |
| 4 | "Arun", as a rehearsal input only | Passed the form check |
| 5 | "Arun", after the security fixes below | Passed the form check, 4 turns |
| 6 | "Arun", through the preview | Passed the form check |

The draft in run 4 answered the customer's question about their other team by saying it isn't known yet, which both earlier replies skipped. Run 3's draft said "We're tracking this internally", which no note supports. The form check can't catch that, so the person approving still has to.

One passing run on one ticket shows the wiring works. They don't measure how often the free model keeps to the skill.

## Security review

The project's `security-reviewer` read the change and found nothing Critical or High. Fixed: a read of any ticket but the requested one now fails the draft (`unexpected_read`), `ORION_MCP_TOKEN` must be at least 32 characters, the body limit applies while reading, nested JSON no longer gives a 500, and `draft` needs no database login.

Open: the token reads every ticket, and `/api/mcp` has no rate limit. It is also unknown whether the CLI re-sends the bearer token if the route answers with a redirect.

The bypass secret passes the wall for the whole deployment, not only this route. The desk's pages have no login of their own, so whoever holds it can read the desk on that deployment. It now sits in `.env.triage-agent` as well as `.env`.

## Not checked

- Reaching the route from another machine. Every request here came from this one.
- Production, which has no `ORION_MCP_TOKEN`, so the route refuses everyone there.
- How often the free model keeps to the skill.
