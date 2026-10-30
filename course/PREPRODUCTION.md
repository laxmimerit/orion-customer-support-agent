# Orion pre-production readiness

Built and versioned in `orion-course-resources/`:

- Company brief, consistent fictional timeline, fixed seed and separate data pools.
- 4,000 historical tickets, 300 customers, nine agents, three plans, subscriptions, 1,800 invoices, message history, SLA/CSAT, releases and incident records.
- 300 held-out evaluation cases, 500 untriaged cases, duplicate groups, KB/known issues and isolated security/privacy fixtures.
- CSV/JSON/Parquet, reproducible core generator, validation and metric definitions.
- Brand SVG/PNG assets, DESIGN.md, brand reference PDF and reusable visual skill.
- Founder notes, personas, five interviews, pricing PDF/survey, contract, signups, cost/market inputs, email drafts, form specification, launch-metrics/notes inputs and messy assets.
- Interactive dashboard design reference with filters, exports and ticket detail.

Remaining before the relevant lesson:

- Create the live course-owned Google Form/Sheet/Doc from supplied inputs and identify owned test inboxes. EML files are drafts only; no messages have been sent.
- Publish the approved brand kit for the download demonstration. The resources repository stays private until recordings are complete.
- Record Python/Nomic setup and generate actual vectors; then teach PostgreSQL/pgvector loading and search. No placeholder vectors.
- Record installation through verification for Docker Desktop/Compose and every stack component. Add troubleshooting as encountered. Do not skip installation because the resource files exist.
- Verify current provider model IDs/free limits and Windows integration support. Optional Ollama and LM Studio lessons are Windows-only and outside the active Orion stack.
- Build application schema, seed command, migrations, API, frontend, tests and lesson checkpoints during the course. Prepare each later exercise from its actual preceding lesson state.
- Produce section cheat sheets from commands actually demonstrated, then Welcome from completed material. Timing remains provisional.

Windows assignments include 1.5 W, 5.9 W, 6.1 W, 7.1 W, 11.10, optional 11.11 and 11.16. Test cross-platform commands before course publication. Existing pilot approvals and recording status remain unchanged.

Open production choices: remote MCP demo endpoint, production-hosting scope, live account readiness and current plan feature limits. These do not block packaging local learner inputs.

## Dedicated Claude Design section — creator decision, 30 October 2026

The current dashboard is a rough starting point. The creator accepted its functional and analytics concept, not its visual quality. Preserve `dashboard/` and the baseline at commit `7bcd3ae`; do not polish or replace it during this plan update.

Teaching progression: rough design in Section 4 → working data-connected dashboard in Section 7 → a complete Claude Design redesign section in Section 8 → refined UI implemented and verified with Claude Code within that section. Later engineering, automation and API sections continue on that refined application.

Section 8 teaches deliberate critique and iteration: design brief; Sonnet/Opus comparison on identical inputs; information hierarchy and responsive grids; typography, spacing and component consistency; truthful analytics; tables and navigation; accessibility; realistic states; implementation handoff; rendered before/after review. Compare actual outputs without assuming either model is always better. Verify model availability and Claude Design's actual export/handoff workflow before recording.

The new section has ten lessons. Former Sections 8, 9 and 10 become 9, 10 and 11; Welcome and Sections 1–7 retain their lesson IDs. There are now 116 planned lessons across Welcome plus eleven sections. Duration remains to be estimated from complete walkthroughs. Original imported plans and existing pilot media remain historical sources.

The production-style UI is an outcome built and reviewed during the course, not a completed pre-recording deliverable or a claim that the application is deployed to production.
