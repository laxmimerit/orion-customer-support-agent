## Creator decisions adopted 30 October 2026

These decisions supersede conflicting v4 stack, preparation and timing instructions.

- Prepare company facts, fictional datasets, visual brand assets and learner inputs before recording. Installation, configuration, first run, verification and actual troubleshooting are taught on camera. Do not hide the setup behind an already-working environment.
- Teaching sequence: why it is needed, install, configure, small example, connect to Orion, verify, troubleshoot. Expand or split lessons when needed; previous minutes are provisional estimates, not limits.
- Docker Desktop and Compose installation through working services is filmed separately on Mac and Windows, including WSL 2 where required.
- Anthropic API remains the main generative AI and agent provider. Classification uses a suitable available free OpenRouter model first. Jev is a paid decision-model alternative; request the creator's direct Jev access if needed. Evaluate classification against a held-out labelled set. Explain that model names, free availability and limits change while fundamentals remain.
- Embeddings run locally using Nomic Embed Text through Python/Sentence Transformers, without Ollama. Use one pinned model/configuration for documents and queries. PostgreSQL with pgvector stores/searches vectors.
- Separate optional Windows lessons demonstrate Ollama and LM Studio with Claude Code and Claude Desktop where actually supported. Neither is an active Orion dependency. Verify Windows Desktop integration before promising it. Local open models are not local Anthropic weights.
- Supplementary API examples use OpenRouter with the latest available OpenAI Luna and Google Gemini models at recording time. Show keys, request/response handling and differences; do not assume all APIs are interchangeable.
- Use rich six-month analytics data with customer segments, channels, queues, agent workloads, response/resolution times, SLA, satisfaction, billing and events. Dashboard calculations must come from records, with explicit denominators and snapshot dates.
- One learner resources repository: https://github.com/laxmimerit/orion-customer-support-agent-resources . Keep private through recording; public release is a later creator action. Keep instructor answer keys, credentials and recordings outside the repository.
- The dashboard mockup is an explicitly requested pre-production design reference. The working application is still built during the course.

## Dedicated Claude Design section — creator decision, 30 October 2026

The current dashboard is a rough starting point. The creator accepted its functional and analytics concept, not its visual quality. Preserve `dashboard/` and the baseline at commit `7bcd3ae`; do not polish or replace it during this plan update.

Teaching progression: rough design in Section 4 → working data-connected dashboard in Section 7 → a complete Claude Design redesign section in Section 8 → refined UI implemented and verified with Claude Code within that section. Later engineering, automation and API sections continue on that refined application.

Section 8 teaches deliberate critique and iteration: design brief; Sonnet/Opus comparison on identical inputs; information hierarchy and responsive grids; typography, spacing and component consistency; truthful analytics; tables and navigation; accessibility; realistic states; implementation handoff; rendered before/after review. Compare actual outputs without assuming either model is always better. Verify model availability and Claude Design's actual export/handoff workflow before recording.

The new section has ten lessons. Former Sections 8, 9 and 10 become 9, 10 and 11; Welcome and Sections 1–7 retain their lesson IDs. There are now 116 planned lessons across Welcome plus eleven sections. Duration remains to be estimated from complete walkthroughs. Original imported plans and existing pilot media remain historical sources.

The production-style UI is an outcome built and reviewed during the course, not a completed pre-recording deliverable or a claim that the application is deployed to production.

## Beginner opening — creator decision, 30 October 2026

Teach one complete section of Claude application fundamentals before discussing the Orion course project. Section 1 uses small, familiar tasks: a first conversation, summarising notes, rewriting an email, comparing model answers, uploading a simple document, personal instructions, memory and voice. Teach Claude Projects as an app feature using a small personal workspace; do not confuse it with introducing the Orion business/project.

Lesson 1.1 begins in Claude Chat with one approachable task and a visible follow-up. No Orion brief, finished dashboard, development workspace, architecture, terminal or API workflow in the opening. Explain the app as each control becomes useful. Broader surfaces may be named briefly later; hands-on Claude Code begins in Section 6.

Introduce Orion at the opening of Section 2, before the first research task. Explain the fictional company, its customers and one immediate research question in plain language. Add product and technical detail as the relevant features are taught. Keep Sections 1–5 accessible without programming knowledge.

Welcome also uses a gentle orientation and small examples; defer the detailed finished-product showcase to the later course outcome/capstone. Introduce project-specific resources when students first need them.

The existing 1.1 pilot needs a new opening and demonstration. The existing 1.6 pilot uses project positioning and also needs familiar-example revisions to fit Section 1. Keep previous media and narration as labelled history. The 3.1 lesson's approved visual treatment remains valid for its later placement. No replacement scripts, recordings or voice are claimed complete by this plan change.
