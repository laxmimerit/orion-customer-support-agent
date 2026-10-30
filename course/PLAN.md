# Claude Masterclass: Tool-First Course Plan (v6 working revision)

Oct 30, 2026 · @Laxmi Kant

This plan is the full brief for the agent that builds the course. It covers what is taught, how it is filmed, and how the sample data and brand assets are prepared. Resource build status is tracked in PREPRODUCTION.md. Company inputs, core datasets, brand assets and a dashboard design reference now exist; application construction and installation remain on-camera lessons.

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

## Course at a glance

| Item | Decision |
| --- | --- |
| Working title | Claude Masterclass: Every Claude Feature, from Chat and Design to Claude Code and the API |
| Course promise | Use every part of Claude with confidence: research, documents, decks, sheets, designs, dashboards, skills, plugins, Claude in your browser and office apps, Claude Code, and building with the API |
| Course style | **Tool-first.** Each lesson teaches one Claude feature (or a small group of related ones) on the Orion story. It is not a deep production-project course: lessons stand alone from a provided starting state |
| Structure | Welcome section (built last) + 11 sections. Part 1, the Claude app: Sections 1 to 5. Part 2, Claude Code and the API: Sections 6 to 11 |
| Length | 116 planned lessons; duration to be re-estimated for complete setup walkthroughs |
| Audience | Part 1: any professional. Part 2: developers, or Part 1 graduates ready to build |
| Plan target | **Claude Pro** (the paid individual plan). Free users can follow most of Part 1 and watch the rest to learn the fundamentals. Max is never required |
| Main surface | **GUI-first:** the Claude desktop app (chat, and the Code tab for Claude Code). The terminal only where no app screen can show the feature |
| Project | Orion, a fictional startup's AI customer support desk: launched as a business in Part 1, its product built in Part 2 on a multi-stack codebase |
| Recording | macOS for most lessons; Windows lessons are separate lessons (as in the Codex course), recorded on the Windows PC |

## Historical changes from v3 to v4

This table preserves the earlier comparison and its original lesson numbers. Current structure and numbering are in the v6 sections below.

| Area | v3 | v4 |
| --- | --- | --- |
| Main surface for Part 2 | Slash commands and the CLI | GUI-first: the desktop app's Code tab. Every feature kept; the terminal only where no app screen can show it (each such lesson states why) |
| Welcome | 1.1 toured the finished product inside Section 1 | New Welcome section, built last, no lesson or section counts; the only place the finished Orion appears |
| Sections | 10 | 10 + Welcome. Old Section 9 (teams, gateways, other models) split: teams lessons into Section 9, gateways into Section 10 after the API lessons |
| The stack | Used, never introduced | New Section 7 introduces every stack piece properly (Docker Compose, PostgreSQL and Alembic, FastAPI, Next.js, pgvector with nomic-embed-text, Polars and DuckDB, GitHub Actions) |
| Models | Named in 1.2 only | 1.2 introduces Fable, Opus, Sonnet and Haiku with numbers, strengths and weaknesses; a course-wide model policy (Sonnet default, Opus on failure, Haiku for small tests, Fable reminders) |
| Lesson titles | Casual ("Asking well", "Prove it works") | Industry-standard terms; lessons that use a slash command start with it (`/code-review: …`) |
| Slack | In 1.3, 2.3, 8.9 | Removed everywhere |
| 5.6 Claude in Chrome | Submit Orion to a real startup directory | Fill the course-owned partner signup Google Form |
| Windows | 1.5, 6.1, 6.2, 9.3, 9.4 recorded on Windows; 6.1 and 5.9 side by side | Separate Windows lessons: 1.5 W, 5.9 W, 6.1 W, 7.1 W, plus the Windows-only gateway and local-model lessons 10.10 and 10.11 |
| Embeddings | Open question | nomic-embed-text (free, local), run locally through Python/Sentence Transformers (no Ollama) |
| Brand assets | Pre-made brand sheet | Orion brand kit + brand skill prepared before recording and published on designmd.ai; 4.3 downloads it on camera |
| Cheat sheets | Not planned | One PDF per section with every command, prompt and shortcut |
| Plan target | Pro or Max | Pro; Free can follow most of Part 1 and watch the rest |
| Length | 90 lessons, 362 min | 105 lessons, about 437 min (the stack section, the Windows lessons and the longer models lesson) |

## Course rules for the building agent

### 1. Tool-first, standalone lessons

- Each lesson opens on its own feature, does one Orion task with it, and stops. No repeated ship/PR routines, no side tours.
- Related features may share a lesson (for example `/context`, `/compact`, `/recap`, `/focus`), as listed in the tables.
- Every Part 2 lesson starts from a tagged state of the starter repo (`lesson-6.3-start`, `lesson-9.1-start`, …), so a learner can jump into any lesson. The lesson's end state is tagged too (`lesson-6.3-end`).

### 2. GUI-first

- **Part 1:** the Claude desktop app (with claude.ai on the web where a feature lives only there), the mobile app where taught.
- **Part 2:** the Claude desktop app's **Code tab** is the main surface. Slash commands are typed in the Code tab's prompt; modes, model and effort are picked in the app; worktrees come from the app's per-session worktrees; parallel work uses side sessions and split view; the app's built-in browser pane shows the running app; scheduled tasks, connectors and plugins use the app's own screens.
- **VS Code** (light theme) shows the files Claude writes: open the project once per lesson and watch it change. Never show files one by one in a terminal.
- **The terminal appears only where no app screen can show it**, and the lesson says why in one line. Expected cases: 6.2 (Claude Code in the terminal and VS Code, taught as a surface), 9.12 (status line), 10.7 (headless `claude -p` in CI), and commands whose dialog is terminal-only (for example `/hooks`, `/permissions`). For a terminal-only dialog, prefer asking Claude in the Code tab to make the change and showing the settings file in VS Code; show the terminal dialog only briefly.
- **Before filming each section, check every listed command in the Code tab** against the current commands page. Anything that turns out terminal-only gets the one-line reason; nothing is dropped.

### 3. The stack, introduced properly

Learners should meet many stacks. Each stack piece gets its own unhurried lesson in Section 7: what it is, why Orion uses it, the small part of it Orion needs, how to run it, and how Claude builds it. Claude writes the code; the lesson explains the piece and shows it working (the FastAPI docs page, a table in the database, the dashboard in the browser, a green CI run). Later lessons reuse a stack piece without re-teaching it.

### 4. Models: names, strengths and the course policy

Model names always carry their numbers (Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 5.5). App, editor and CLI versions are never spoken: they teach nothing. Say once (in 1.2) that models change and the learner picks the current ones in the model picker.

What Anthropic's models overview says (checked 2026-10-30; re-check before recording 1.2):

| Model | Anthropic's positioning | Speed | Relative cost |
| --- | --- | --- | --- |
| Fable 5.1 | Demanding reasoning and long-horizon agentic work | Slower | Highest |
| Opus 5.5 | Long-running agentic coding and knowledge work | Moderate | High |
| Sonnet 5.5 | The best combination of speed and intelligence | Fast | Medium |
| Haiku 5.5 | High-volume, latency-sensitive work: classification, extraction, routing | Fastest | Lowest |

**The course policy, said in 1.2 and 6.7, and applied in every lesson:**

- **Sonnet is the default** for day-to-day work and for development in Claude Code.
- **Switch to Opus when Sonnet gets it wrong** (a wrong fix, a missed bug, a weak plan). If a real Sonnet miss happens on camera, keep it as a teaching beat and redo the step on Opus. Never stage a fake failure.
- **Haiku for small test tasks**: quick checks, small subagents (a test runner), and small agent checks. Orion classification follows the free-first OpenRouter/Jev policy above.
- **Fable reminders:** whenever a lesson talks about output quality or a hard task, remind learners that Fable is the top tier for the hardest reasoning and long-horizon agent work, and that it costs more and is slower. Planned reminder points: 1.2, 2.2, 3.1, 6.7, 9.2, 10.3, 10.5, 11.6, 11.7.
- Be honest once: Anthropic's own docs suggest starting with Opus for most workloads. The course defaults to Sonnet because it is faster and lasts longer within a Pro plan's usage limits, and Opus stays one click away.

### 5. Plans

- The course is recorded on **Pro**. 1.4 compares Free, Pro and Max and says plainly: Pro is the target; Free users can follow most of Part 1 and should watch the rest to learn the fundamentals.
- Mark lessons whose features need a paid plan with a small on-screen badge ("Pro"). Check which features Free lacks before recording (Claude Code, some artifact types, connectors, scheduled tasks).
- Section 11 needs Claude Console API credits, billed separately from the Claude plan: say so at the start of 11.1.

### 6. Titles

- Lecture titles use the industry-standard term for what the lesson really teaches (prompt engineering, multimodal input, context engineering, vector search, CI/CD, code review, security review, function calling, structured outputs). No term the lesson doesn't deliver.
- Every lesson that uses a slash command on camera starts its title with it: `/code-review: …`. Titles are 80 characters or less.
- The section titles and the Udemy "What you'll learn" name the slash commands too.

### 7. Welcome section and promo

- Built **last**, from the finished lessons: real clips, real resources, real durations.
- Never say or show how many lessons or sections there are; player replicas show titles only.
- The finished Orion (launch kit and app) appears only in the Welcome section, the promo and the listing.
- 0.2 explains the timer ring: when it appears, stop the video and read the screen and diagram. It also says where the cheat sheets are.

### 8. Cheat sheets

- One KGP Talkie-branded PDF per section, attached to the section's first lecture.
- It holds every slash command, every prompt typed on camera (word for word, as in the lesson), and every shortcut, with Mac and Windows keys.
- Collect them as you go: every lesson build appends its commands, prompts and shortcuts to a running log; the PDFs are built from the log at the end, before the Welcome section.

### 9. Narration and editing

Follow the `calm-lecture-edit` skill and the Codex course rules:

- Explain, never read the screen. The voice says what a thing means and why.
- Standard voice with no delivery tags; natural pauses only.
- Reading holds are a 2 to 3 second hold with a soft tick inside a real pause, at most 3 per lecture.
- Highlights are drawn boxes, with no dimming.
- One app at a time at 110 % app zoom, and the window is never cut by a crop.
- App switches use native macOS window moves.
- Finals at 1080p first, then a 4K pass.
- Assets that enter a lesson are made on camera from a described brief, or downloaded from a public source shown on camera (as the Orion brand kit is in 4.3).

### 10. Privacy and accounts

- The founder inbox is **the course-owned test inbox** (fine on screen). Beta-user emails go only to the course's test Gmail accounts, never to real people. Claude confirms before each send.
- Keys and tokens never appear on screen: redact them in the source capture, not with a moving blur. API keys live in `.env`.
- Project and demo folders live under `~/Documents/Claude/<name>/` (for example `~/Documents/Claude/orion/`), never in the home folder.
- Lessons that teach Claude in Chrome (5.6, 10.9) film it driving Chrome on purpose. The glow and the agent cursor are the feature. Every other browser beat uses plain Chrome or the app's browser pane.

### 11. Listing

- The Udemy description's first line is exactly: "This course contains the use of artificial intelligence."

## The running project: Orion

Orion is a fictional startup's AI customer support desk. Part 1 uses the Claude app to launch it as a business. Part 2 uses Claude Code and the API to build the product.

| Part | What Claude produces |
| --- | --- |
| Part 1, the Claude app | Market research report, product requirements doc, investor deck, pricing sheet, brand design system (from the published Orion brand kit), landing page and dashboard designs, launch board, signups dashboard, waitlist page, a brand-voice skill, and launch emails |
| Part 2, Claude Code and the API | The Orion app: ticket API, agent dashboard, similar-ticket search, nightly analytics, CI with agent reviews, and an AI triage agent on the API and Agent SDK |

**Part 2 stack**

| Layer | Tool | Introduced in |
| --- | --- | --- |
| Run everything | Docker Compose (Docker Desktop; WSL 2 on Windows) | 7.1 M / 7.1 W |
| Database | PostgreSQL with Alembic migrations | 7.2 |
| API | FastAPI (Python, uv, pytest) | 7.3 |
| Web app | Next.js (App Router, TypeScript) | 7.4 |
| Vector search | pgvector + **nomic-embed-text** embeddings run locally through Python/Sentence Transformers (no Ollama) | 7.5 |
| Analytics | Polars and DuckDB on a Parquet export | 7.6 |
| CI/CD | GitHub Actions (tests on every PR; headless `claude -p` review added in 10.7) | 7.7 |
| AI | Claude API, Claude Agent SDK, Managed Agents | Section 11 |
| Email | Signups in PostgreSQL; beta-user emails sent from the course-owned test inbox through the Gmail connector | 5.7 |

Nomic embeddings run through Python. Ollama and LM Studio are separate optional Windows demonstrations; neither belongs to the active Orion stack.

## Welcome (built last, 11 min)

| # | Lesson title | Content | Min |
| --- | --- | --- | --- |
| 0.1 | Welcome: What You Will Build with Claude | The finished Orion launch kit and app in real clips; what the course covers | 4 |
| 0.2 | How This Course Works: Plans, Models, Timer Ring and Cheat Sheets | Pro target / Free path, the model policy in one line, the timer ring means stop and read, where the cheat sheets are | 4 |
| 0.3 | Course Resources: Sample Data, the Orion Brand Kit and the Starter Repo | Where each resource is, the lesson tags, the brand kit on designmd.ai | 3 |

## Part 1: the Claude app (Sections 1 to 5, 186 min)

Surface key: **App** = Claude desktop app (chat); **Web** = claude.ai in the browser; **Mobile**; **Chrome** = Claude in Chrome; **Win** = recorded on the Windows PC.

### Section 1: Claude Essentials: Models, Prompt Engineering, Projects and Memory (46 min)

| # | Lesson title | Claude feature | Surface | Orion task | Min |
| --- | --- | --- | --- | --- | --- |
| 1.1 | Claude Platform Overview: Chat, Design, Claude Code and the API | Platform map | App | Map each part of Claude to a launch job | 3 |
| 1.2 | Claude Models Compared: Fable, Opus, Sonnet and Haiku | Model picker; strengths, weaknesses, speed, cost; the course model policy | App | One positioning question on Haiku, Sonnet and Opus side by side; when Fable is worth it | 6 |
| 1.3 | Claude Everywhere: Web, Desktop, Mobile, Chrome and Office Apps | Surfaces | App | Which surface for which launch job | 3 |
| 1.4 | Claude Plans, Usage Limits and Settings: Free, Pro and Max | Plans, limits, web search, memory, guided setup | App | Account ready for the course | 4 |
| 1.5 M | Install the Claude Desktop and Mobile Apps on Mac | Desktop + mobile apps, continuity | App, Mobile | Start on the Mac, continue on the phone | 3 |
| 1.5 W | Install the Claude Desktop App on Windows | Windows installer and first run | Win | Same account on Windows | 3 |
| 1.6 | Prompt Engineering Basics: Clear Asks, Examples and Output Formats | Prompting | App | Product naming and positioning brief | 4 |
| 1.7 | Multimodal Input: PDFs, Spreadsheets and Images | Uploads | App | Read a competitor's pricing PDF | 4 |
| 1.8 | Claude Projects: Knowledge Base and Custom Instructions | Projects | App | The Orion project | 5 |
| 1.9 | Memory, Chat Search and Incognito Chats | Memory, past chats | App | Claude remembers the product | 5 |
| 1.10 | Memory Import: Bring Your Context from Another AI Assistant | Importing memory | App | Import the founder's notes export | 3 |
| 1.11 | Voice Mode: Hands-Free Conversations with Claude | Voice | Mobile | Talk through the launch plan | 3 |

### Section 2: AI Research, Connectors and MCP (22 min)

| # | Lesson title | Claude feature | Surface | Orion task | Min |
| --- | --- | --- | --- | --- | --- |
| 2.1 | Web Search with Citations | Web search | App | Current help desk software pricing | 3 |
| 2.2 | Deep Research: Multi-Source Research Reports | Research | App | Competitor landscape report (Fable reminder for hard research) | 4 |
| 2.3 | Connectors: Gmail and Google Drive | Connectors | App | Customer interview emails summarised | 5 |
| 2.4 | Custom Connectors: Remote MCP Servers | Custom connectors | App | Connect the Orion demo MCP server (see open questions) | 4 |
| 2.5 | Data Visualization in Chat: Charts, Diagrams and Image Search | Inline visuals | App | Market size chart in the reply | 3 |
| 2.6 | Fact-Checking AI Research: Sources, Claims and Hallucinations | Checking sources | App | Verify three figures | 3 |

### Section 3: Agentic Work: Documents, Presentations and Spreadsheets (28 min)

| # | Lesson title | Claude feature | Surface | Orion task | Min |
| --- | --- | --- | --- | --- | --- |
| 3.1 | Agentic Tasks: A Full Launch Plan from a One-Paragraph Brief | Longer tasks, task list, working while away | App | Launch plan (one take; the trailer; Fable reminder) | 5 |
| 3.2 | AI Document Editing: Write, Comment and Revise a PRD | Docs | App | PRD revised by comment | 5 |
| 3.3 | AI Presentations: A Ten-Slide Investor Pitch Deck | Slides | App | Investor deck | 5 |
| 3.4 | AI Spreadsheets: Formulas, Pricing Model and Cash Runway | Sheets | App | Pricing model and runway | 5 |
| 3.5 | Editing Office Files In Place: Word, Excel and PowerPoint | Editing uploaded Office files | App | Correct the old customer contract | 4 |
| 3.6 | Export to Word, PowerPoint and PDF | Export | App | Deck exported for an investor email | 4 |

### Section 4: AI Design, Artifacts and Sharing (46 min)

| # | Lesson title | Claude feature | Surface | Orion task | Min |
| --- | --- | --- | --- | --- | --- |
| 4.1 | AI UI Design: Landing Page and Dashboard in Three Directions | Design canvas | App | Landing page and rough agent-dashboard concepts; establish the starting point for Section 8 | 5 |
| 4.2 | Design Systems: Colors, Typography and Components | Design System | App | Brand applied to every design | 5 |
| 4.3 | Design System from a Brand Kit: Import the Orion DESIGN.md | Design System from brand assets | App, Web | Download the published Orion brand kit from designmd.ai on camera and build the system from it | 3 |
| 4.4 | Whiteboard: Flowcharts and Process Maps | Whiteboard | App | Ticket flow and launch flowchart | 4 |
| 4.5 | Task Boards: Kanban with Owners and Due Dates | Tasks | App | Launch tasks | 3 |
| 4.6 | KPI Dashboards: Weekly Signups | Dashboard | App | Signups dashboard | 4 |
| 4.7 | Motion Graphics: A 15-Second Product Teaser | Motion | App | Product teaser | 2 |
| 4.8 | Interactive Artifacts: Build an ROI Calculator | Hand-built artifacts | App | Support cost savings calculator | 4 |
| 4.9 | Stateful Artifacts: A Waitlist Page That Stores Signups | Shared state, data, files | App | Beta waitlist page | 6 |
| 4.10 | Sharing and Access Control: Private Links and Comments | Sharing, comments | App | Share the deck with a reviewer | 4 |
| 4.11 | Artifact Gallery, Pinning and Versioning | Gallery, pins, revising | App | Update last week's dashboard | 4 |
| 4.12 | Collaboration: Share a Chat Link | Chat link sharing | App | Share a planning chat with the co-founder | 2 |

### Section 5: Agent Skills, Plugins, Automation and Claude in Your Apps (44 min)

| # | Lesson title | Claude feature | Surface | Orion task | Min |
| --- | --- | --- | --- | --- | --- |
| 5.1 | Agent Skills: Built-In Skills in Action | Ready-made skills | App | Morning brief and file skills | 4 |
| 5.2 | Custom Skills: Build a Brand-Voice SKILL.md | Writing a skill | App | `brand-voice` skill (text voice; the visual brand kit is the separate published one) | 5 |
| 5.3 | Plugins: Install a Role Plugin from the Catalog | Plugins | App | Marketing plugin | 4 |
| 5.4 | Scheduled Tasks: Automate a Weekly Signups Report | Scheduled tasks | App | Monday signups summary | 4 |
| 5.5 | Personalization: Writing Styles and Saved Preferences | Styles, preferences | App | Emails that sound like the founder | 5 |
| 5.6 | Browser Agent: Claude in Chrome Fills a Web Form | Claude in Chrome | Chrome | Fill the course-owned partner signup Google Form | 5 |
| 5.7 | Email Automation: Triage, Reply and Send with the Gmail Connector | Gmail connector | App | Triage beta feedback in the course-owned test inbox, reply in the brand voice, send a beta update to the test waitlist | 5 |
| 5.8 | Google Workspace: Claude in Google Sheets and Docs | Claude for Google Workspace | Web | Update a Google Sheet and Doc | 5 |
| 5.9 M | Computer Use: Desktop Automation on Mac | Computer use | App | Organise the messy launch assets folder | 4 |
| 5.9 W | Computer Use on Windows | Computer use, Windows permissions | Win | The same folder task on Windows | 3 |

## Part 2: Claude Code and the API (Sections 6 to 11, duration TBD)

Surface key: **Code** = the desktop app's Code tab; **VS Code** = files shown in VS Code; **Term** = terminal, with the reason; **Win** = Windows PC.

### Section 6: Claude Code Foundations in the Desktop App (40 min)

| # | Lesson title | Claude Code feature | Surface | Orion task | Min |
| --- | --- | --- | --- | --- | --- |
| 6.1 M | Claude Code in the Desktop App: Code Tab Setup on Mac | Code tab, Git, opening a project | Code | Open the Orion starter repo | 4 |
| 6.1 W | Claude Code on Windows: Desktop App and Git for Windows | Windows setup | Win | Same repo on Windows | 4 |
| 6.2 | Claude Code in the Terminal and VS Code: CLI, IDE Extension, Web and Mobile | Other surfaces | Term (the lesson is about the surfaces), VS Code | Same session continued in three surfaces | 4 |
| 6.3 | /init, /memory: CLAUDE.md Project Memory | CLAUDE.md | Code, VS Code | Orion's CLAUDE.md | 4 |
| 6.4 | Plan Mode and Permission Modes: Design Before You Code | Plan mode, auto mode, mode switching (Shift+Tab mentioned for the CLI) | Code | Ticket schema and vector design planned before any code | 5 |
| 6.5 | /rewind, /resume, /fork: Checkpoints and Session Management | Checkpointing, sessions | Code | Recover from a bad refactor | 4 |
| 6.6 | /context, /compact, /recap, /focus: Context Engineering | Context control | Code | A long session kept sharp | 4 |
| 6.7 | /model, /effort, /fast: When to Use Sonnet, Opus, Haiku and Fable | Model, effort, fast mode | Code | The course model policy applied; Sonnet default, Haiku for a quick check, Opus on a miss, Fable reminder | 5 |
| 6.8 | /sandbox, /fewer-permission-prompts: Permission Rules and Sandboxing | Settings files, permission rules, sandbox | Code, VS Code | Team settings checked into the repo | 6 |

### Section 7: The Orion Stack: Docker, PostgreSQL, FastAPI, Next.js, Vector Search and CI/CD (44 min)

Each lesson introduces one stack piece properly (rule 3). Claude builds it in the Code tab; the lesson shows it working.

| # | Lesson title | Stack piece | Surface | Orion task | Min |
| --- | --- | --- | --- | --- | --- |
| 7.1 M | Docker Compose: Run Orion's Stack Locally on Mac | Containers, Compose file, seed command | Code, VS Code, Docker Desktop | Start the stack and load the sample data | 5 |
| 7.1 W | Docker Desktop on Windows with WSL 2 | WSL 2 backend, file paths | Win | The same stack on Windows | 5 |
| 7.2 | PostgreSQL and Alembic: Database Schema and Migrations | Tables, keys, migrations | Code, VS Code | Customers, agents, tickets, waitlist tables | 6 |
| 7.3 | FastAPI: Build the Ticket REST API | Routes, models, OpenAPI docs, pytest | Code, browser pane | Ticket endpoints with tests | 6 |
| 7.4 | Next.js: Build the Basic Dashboard from the Rough Design | App Router, pages, components | Code, browser pane | Working dashboard from the rough Section 4 design; final visual refinement follows in Section 8 | 6 |
| 7.5 | Vector Search: pgvector and nomic-embed-text Embeddings | Embeddings, cosine similarity, vector index | Code, VS Code | Install local Nomic through Python; generate embeddings and find similar tickets for one new ticket | 6 |
| 7.6 | Polars and DuckDB: Ticket Analytics on Parquet | DataFrames, SQL on files | Code, VS Code | Weekly ticket report from the Parquet export | 5 |
| 7.7 | CI/CD with GitHub Actions: Tests on Every Pull Request | Workflows, checks | Code, browser | Green checks on a PR | 5 |

### Section 8: Claude Design — From a Working Dashboard to a Production-Style UI (duration TBD)

Prerequisite: the basic dashboard, data contracts and analytics from Section 7 work. Section 4 introduces rough designs; this separate section develops a complete design and implementation workflow. Begin with the supplied rough mockup and the actual working application, not a prebuilt polished answer.

| # | Lesson title | Design focus | Surface | Orion task | Min |
| --- | --- | --- | --- | --- | --- |
| 8.1 | Critique the Rough Dashboard and Write the Design Brief | Design audit and acceptance criteria | Design, browser | Inspect the existing dashboard; define users, primary decisions, pain points and measurable design acceptance criteria | TBD |
| 8.2 | Sonnet and Opus: Compare Two Design Approaches | Controlled model comparison | Design | Use the same brief, brand and dataset with available Sonnet and Opus models; inspect strengths and failures and choose a direction | TBD |
| 8.3 | Information Hierarchy and Responsive Layout Grids | Navigation, hierarchy, columns and breakpoints | Design | Prioritise support decisions; establish a consistent grid, page structure and responsive reading order | TBD |
| 8.4 | Typography, Spacing and a Reusable Component System | Type scale, density, tokens and components | Design | Refine the Orion visual system and reusable controls while preserving brand identity | TBD |
| 8.5 | Design Trustworthy KPIs and Analytics Charts | Chart selection, scales, labels and denominators | Design | Redesign trend, SLA, CSAT, billing and backlog views without changing metric definitions or inventing numbers | TBD |
| 8.6 | Design the Ticket Table, Filters and Detail Flow | Dense tables and interaction flows | Design | Improve scanning, sorting, filtering, pagination, ticket detail and export discoverability | TBD |
| 8.7 | Responsive Design and Accessibility | Narrow layouts, contrast and keyboard access | Design, browser | Inspect desktop, tablet and mobile layouts; design focus, readable labels and accessible status cues | TBD |
| 8.8 | Loading, Empty, Error and Partial-Data States | State design and realistic prototypes | Design | Design the whole experience including no results, slow requests, failures and missing observations; distinguish zero from unavailable | TBD |
| 8.9 | Bring the Refined Design into Claude Code | Design handoff and frontend implementation | Design, Code, browser | Carry approved layouts, components and interaction notes into the working app; implement without replacing the data or API contracts | TBD |
| 8.10 | Review the Before and After and Verify the Redesign | Visual critique and regression checks | Design, Code, browser | Compare the same records and viewport sizes, refine the rendered result, verify keyboard/mobile flows and reconcile metrics, filters and exports | TBD |

**Teaching method:** show the brief, generation, critique, corrections and the rendered result. Keep unsuccessful iterations when they explain a useful correction. Compare Sonnet and Opus using the same constraints and evaluate hierarchy, usability, consistency and factual accuracy rather than assuming a model winner. Do not rush the process to fit earlier time estimates.

**Section deliverables:** annotated before/after captures, a design brief and critique rubric, refined tokens/components and responsive layouts, interaction/state specifications, and the implemented dashboard. Keep the original mockup as the before reference. Capture design assets through the workflow actually supported at recording time; explain the handoff instead of implying automatic production-ready code.

**Completion checks:** inspect real desktop, tablet and mobile renders; keyboard navigation and focus; contrast/readability; loading/empty/error/partial-data states; filters, sorting, pagination, detail and CSV export. For identical selected records, verify counts, medians, SLA denominators, CSAT coverage and billing totals match before and after. Treat a successful build as one check, not visual approval. Use the refined result for subsequent lessons and the final showcase after review.

### Section 9: Built-In Power Tools and Extending Claude Code (56 min)

| # | Lesson title | Claude Code feature | Surface | Orion task | Min |
| --- | --- | --- | --- | --- | --- |
| 9.1 | /code-review: AI Code Review with Effort Levels and Auto-Fix | `/code-review`, `--fix`, `--comment` | Code | Planted bugs found and fixed in the ticket API | 5 |
| 9.2 | /security-review: Find Vulnerabilities and Prompt Injection | `/security-review` | Code | The planted SQL injection and injected tickets found (Fable reminder) | 5 |
| 9.3 | /simplify: Refactoring and Code Cleanup | `/simplify` | Code | A messy change tidied | 3 |
| 9.4 | /verify: Verify Changes in the Running App | `/verify` | Code, browser pane | Dashboard run and checked, not just tested | 4 |
| 9.5 | /batch: Large-Scale Codebase Changes in Parallel | `/batch` | Code | Rename the ticket model across the codebase | 4 |
| 9.6 | /deep-research: Technical Research from Claude Code | `/deep-research` | Code | Embedding model comparison with sources | 4 |
| 9.7 | /skills, /skill-doctor: Claude Code Skills for Migrations and Endpoints | `.claude/skills/`, `/skills`, `/skill-doctor` | Code, VS Code | `db-migration` and `api-endpoint` skills, first used for the signup endpoint | 5 |
| 9.8 | /agents: Subagents for Security Review and Test Writing | Subagents | Code, VS Code | `security-reviewer` (Sonnet) and `test-writer` (Haiku) | 5 |
| 9.9 | /hooks: Lifecycle Hooks for Formatting, Tests and Secrets | Hooks | Code, VS Code (`/hooks` dialog shown briefly if terminal-only) | Format and test after each edit; block secrets and migrations on `main` | 5 |
| 9.10 | /mcp: MCP Servers for PostgreSQL and GitHub | MCP | Code | PostgreSQL and GitHub connected | 5 |
| 9.11 | /plugin: Plugins and Private Marketplaces | Plugins | Code | `orion-kit` shared with the team | 5 |
| 9.12 | Output Styles and the Status Line | Output styles, status line | Code; Term for the status line (it lives only in the CLI) | Cost and context in the status line | 3 |
| 9.13 | /design, /design-sync, /artifacts: Design and Artifacts from Claude Code | Design and artifacts | Code | Dashboard mockup and design system synced from the repo | 3 |

### Section 10: Parallel Agents, Automation and Teams (41 min)

| # | Lesson title | Claude Code feature | Surface | Orion task | Min |
| --- | --- | --- | --- | --- | --- |
| 10.1 | Git Worktrees: Parallel Sessions Side by Side | Per-session worktrees, split view | Code | Ticket API and dashboard worked on side by side | 3 |
| 10.2 | /background: Background Agents and Agent View | Background sessions | Code | Similar-tickets panel in the dashboard built while you work | 4 |
| 10.3 | Agent Teams: Multi-Agent Collaboration on One Feature | Shared tasks, inter-agent messaging | Code | SLA timers end to end (Fable reminder) | 5 |
| 10.4 | /workflows: Multi-Agent Workflows | Dynamic workflows | Code | Rerunnable test-writing fan-out across modules | 4 |
| 10.5 | /goal: Long-Running Autonomous Tasks | `/goal` | Code | Run until all tests pass (Fable reminder) | 3 |
| 10.6 | /teleport: Remote Control, Mobile and Cloud Sessions | Moving between devices | Code, Mobile | Start on the Mac, approve on the phone, finish in the cloud | 4 |
| 10.7 | Headless claude -p: AI Code Review in GitHub Actions | `claude -p`, GitHub Actions | Term (headless has no app screen), browser | Agent review on every PR | 4 |
| 10.8 | /schedule: Cloud Scheduled Tasks for a Nightly Report | Cloud scheduled tasks | Code | Nightly support report with Polars and DuckDB | 3 |
| 10.9 | /chrome and Computer Use: Browser Testing of the Dashboard | Claude in Chrome from Claude Code, computer use | Code, Chrome | End-to-end test of the dashboard in Chrome | 3 |
| 10.10 | /insights: Usage Analytics for Claude Code | `/insights` | Code | Where sessions go wrong | 4 |
| 10.11 | Managed Settings: Organization-Wide Policies | Managed settings file | VS Code | Orion rules enforced on every machine | 4 |

### Section 11: The Claude API, Agent SDK and Model Gateways (59 min)

Lessons 11.10 to 11.14 use setups Anthropic does not support for Claude Code ([source](https://code.claude.com/docs/en/llm-gateway.md)): say so on camera, and check each provider's terms and free tiers right before recording. They come after the API lessons because the learner then knows what a base URL and a key are.

| # | Lesson title | Feature | Surface | Orion task | Min |
| --- | --- | --- | --- | --- | --- |
| 11.1 | Claude API Quickstart: Console, API Keys and the Python SDK | Console, keys, SDK (API billing is separate from the plan) | Web, Code | Ticket service calls Claude | 4 |
| 11.2 | Tool Use (Function Calling): search_tickets and similar_tickets | Client tools, tool runner | Code | Two tools on Orion's data | 4 |
| 11.3 | Server Tools: Web Search, Web Fetch, Code Execution and Memory | Server tools | Code | Known product issues looked up inside the API | 4 |
| 11.4 | Structured Outputs and Citations: Typed Ticket Triage | Structured outputs, citations | Code | Category, priority, draft reply, sources; scored on the labelled test set | 4 |
| 11.5 | Prompt Caching, Batch API and Files API: Cost at Scale | Caching, batch, Files API | Code | Batch API demonstrated for reply drafting; classification uses the free-first route | 4 |
| 11.6 | Adaptive Thinking, Effort and Compaction: Hard Tickets and Long Threads | Thinking, effort, compaction, context editing | Code | Escalations and very long threads (Fable reminder) | 3 |
| 11.7 | Claude Agent SDK: A Triage Agent inside FastAPI | Agent SDK (API key, not a claude.ai login) | Code | Triage agent service (Fable reminder) | 6 |
| 11.8 | Managed Agents: The Same Agent on Anthropic's Hosted Harness | Managed Agents | Web, Code | Hosted triage agent | 4 |
| 11.9 | Agent Skills and the MCP Connector in the Claude API | Skills in the API, MCP connector | Code | Brand-voice skill used for reply drafts | 3 |
| 11.10 | LLM Gateways: How Claude Code Reaches a Model | `ANTHROPIC_BASE_URL`, gateway credentials, `/status` | Win | See exactly where requests go | 3 |
| 11.11 | Optional: Local Models with Ollama on Windows | Ollama's Anthropic-compatible API, a local coding model with at least 32K context | Win (RTX 5090 PC) | Fix a small bug offline | 4 |
| 11.12 | OpenRouter: Route Subagents to Cheaper Models | Base URL, per-role model variables | Code | Subagent work on a cheaper model | 3 |
| 11.13 | NVIDIA NIM through a Community Proxy | Community proxy to NVIDIA Build | Code | The same task on a NIM-hosted model | 3 |
| 11.14 | Choosing Honestly: Claude vs Local vs Hosted Open Models | Quality, tool-use reliability, privacy, terms, free-tier limits | Code | One task on three setups, compared | 2 |
| 11.15 | Capstone: Launch Day, Orion End to End | App, Claude Code and API together | App, Code | Research, deck, design, app, CI and triage agent in one recorded run (the closer) | 8 |

## Pre-production: sample data, brand assets and starter repo

Resource inputs are built and checked **before recording starts** and shipped with the course. Introduce their fictional scenario and structure on camera. Installation, configuration, imports, embedding generation and application setup are taught step by step on camera.

### General rules for every dataset

- **Fictional and fixed.** All companies, people, emails, phone numbers and addresses are invented. Use a fixed random seed so a rebuild gives identical files; every student works on the same records and gets results close to the video.
- **One consistent story.** The same companies, agents, plans, dates and products appear across Part 1 and Part 2 (the Part 1 waitlist signups become the Part 2 waitlist table; the brand colours in the dashboard match the brand kit).
- **One story timeline.** Orion's history runs 1 Jan to 30 Jun 2026 (tickets), with the beta launch in July 2026. Data dates may show on screen; the voice never reads them.
- **Safe "sensitive" data.** Personal data planted for the privacy lessons uses obviously fake formats: 555 phone numbers, `example.com` addresses, and the payment providers' published test card numbers. Never a real identifier.
- **Planted patterns, documented.** Every planted pattern listed below is written into `data/ANSWERS.md` (not shipped to students), so lessons can be checked against the expected finding.
- **Formats.** CSV and Parquet for tables, JSON for nested data, `.docx` / `.xlsx` / `.pdf` / `.pptx` where a lesson edits an Office file, `.eml` or seeded Gmail messages for email. UTF-8 everywhere.
- **Validation.** A `tools/validate.py` script checks counts, foreign keys, date ranges, planted patterns and that no real-looking personal data slipped in. It runs before every resources export.
- **Delivery.** `resources/part1/<lesson>/…` for Part 1 files; Part 2 data loads into PostgreSQL with one seed command (`make seed` or `docker compose run seed`), introduced in 7.1.

### Part 1 data

| Data | Spec | Used in |
| --- | --- | --- |
| Founder notes export | A text export from "another assistant": 20 to 30 short memory lines about Orion, the founder and the launch | 1.10 |
| Customer personas and sales call transcripts | 4 personas (support lead, CX director, founder of a small SaaS, IT manager); 5 call transcripts of 800 to 1,500 words each, with real-sounding objections | 1.6, 3.2 |
| Competitor pricing PDF | 2 pages, 3 fictional competitors, 3 tiers each, per-seat prices, feature table, one footnote with a catch | 1.7 |
| Customer interview emails | 8 emails seeded into the course-owned test inbox from the test accounts, each with one clear pain point; 2 mention the same feature request | 2.3 |
| Help desk market figures | CSV of market size by year and segment, clearly labelled illustrative in the file, used only for the chart lesson | 2.5 |
| Pricing survey responses | 200 prospects: company size, current tool, willingness to pay per seat, most-wanted feature; one clear price cliff | 3.4 |
| Old customer contract | `.docx`, 4 to 5 pages, with 4 planted errors (wrong renewal date, a price that contradicts the schedule, a missing data-processing clause, a misspelt party name) | 3.5 |
| Signups data | CSV of daily waitlist signups for 12 weeks, by source (search, social, referral); a launch-week spike and one source that stalls | 4.6, 5.4 |
| Support cost benchmarks | CSV of illustrative cost per ticket and tickets per agent by company size, for the ROI calculator | 4.8 |
| Beta feedback emails | 12 emails from the test accounts to the course-owned test inbox: 5 bugs, 4 praise, 2 feature asks, 1 angry; seeded right before recording 5.7 | 5.7 |
| Partner signup Google Form | Owned by the course account: company, contact, size, use case | 5.6 |
| Google Sheet and Doc | A launch-metrics Sheet and a launch-notes Doc, owned by the course account, each with gaps for Claude to fill | 5.8 |
| Messy launch assets folder | About 60 files: images, drafts, duplicates (`final_final_v2`), screenshots, PDFs, with inconsistent names | 5.9 M, 5.9 W |
| Test Gmail accounts | 3 to 5 Gmail accounts owned by the creator, used as beta users, interviewees and waitlist recipients. Never send to anyone else | 2.3, 5.7 |

### Part 2 data

| Data | Spec | Used in |
| --- | --- | --- |
| Customers | About 300 fictional companies: name, size, industry, country, plan, signup date | 7.1 onward |
| Support agents | 9 agents with role, team, shift (including one weekend-only shift), skills; one agent planted as consistently slow | 7.1 onward |
| Plans, subscriptions and invoices | 3 plans; subscriptions per customer; monthly invoices; one month with a pricing change that causes a billing-ticket spike | 7.6, 10.8 |
| Tickets | About 4,000 tickets over 6 months: subject, body, category (billing, bug, how-to, account access, feature request, outage), priority P1 to P4, status, agent, timestamps, SLA due time, first-response and resolution times, threads of 1 to 15 messages | 7.1 onward |
| Planted ticket patterns | The billing spike (pricing-change month), one slow agent, weekend SLA breaches, a ticket surge on the outage day | 7.6, 10.3, 10.8 |
| Product releases and one outage | Release log (about 12 releases) and one outage with start and end times that explains the surge | 10.8 |
| SLA policy and CSAT | SLA targets per priority and plan; a 1 to 5 satisfaction rating on resolved tickets | 10.3, 10.8 |
| Duplicate and near-duplicate tickets | About 150 tickets in clusters of 2 to 6 that say the same thing in different words | 7.5, 10.2 |
| Precomputed embeddings | One 768-dimension vector per demonstration ticket from local nomic-embed-text through Python, using the same pinned model and configuration as query generation. Stored documents use the model's document prefix (`search_document:`) and queries use the query prefix (`search_query:`); verify the current prefixes and tag before generating. Stored as Parquet and loaded into a `vector(768)` column with a cosine index | 7.5, 10.2 |
| Help center articles and known issues | About 40 knowledge-base articles and 10 known product issues | 11.3, 11.4 |
| Labelled test set | 300 tickets with the correct category and priority (kept out of the training/demo pool) | 11.4, 11.7 |
| Untriaged backlog | About 500 tickets with no category or priority | 11.5 |
| Very long ticket threads | 10 threads of 60 to 120 messages | 11.6 |
| Ticket attachments | About 40 product screenshots (mock UI images in the Orion brand) and 30 PDF invoices | 11.5 |
| Prompt-injection and personal-data tickets | 6 tickets with hidden instructions (white text, HTML comments, "ignore previous instructions" in a quoted email) and 10 with fake personal data | 9.2, 11.7 |
| Waitlist signups | The Part 1 signups, as a table | 9.7 |
| Parquet export | The tickets and invoices as Parquet files | 7.6, 10.8 |

### Brand assets and the Orion brand kit (published on designmd.ai before the course starts)

The brand kit gives every lesson the same predefined look and avoids surprises in live recording. It is prepared in full before recording, published publicly on designmd.ai, and downloaded on camera in 4.3, so learners see exactly where it comes from.

- **Contents:**
  - a `DESIGN.md` (brand story in two lines, colour tokens with hex values for light and dark, type scale with font families and weights, spacing and radius scale, component rules for buttons, cards, tables, badges and charts, logo usage, do and don't examples);
  - the logo (SVG and PNG, light and dark, icon-only version);
  - the font names, using free fonts available on Google Fonts;
  - a 1-page brand sheet PDF.
- **As a skill:** package the same kit as an installable skill (`orion-brand`), so Claude applies the brand automatically in designs, decks, artifacts and the Next.js dashboard. Publish it with the kit.
- **Separate from the brand-voice skill:** the brand-voice skill (how Orion writes) is built on camera in 5.2; the brand kit (how Orion looks) is the pre-published one.
- **Check before publishing:** contrast meets WCAG AA for text tokens, the logo reads at 16 px, every component rule is used by at least one lesson, and the Next.js dashboard and the Section 4 designs look like one product.
- The finished launch kit and app shown in the Welcome section come from the lessons themselves, never made separately.

### Starter repo

- One repo, `orion`, under `~/Documents/Claude/orion/` on the recording Mac; public on GitHub for students, with the commit identity set per repo (never the creator's private email).
- Tags for every Part 2 lesson's start and end state (`lesson-7.3-start`, `lesson-7.3-end`). The start state of 6.1 is a near-empty repo with the Compose file, the seed data and a README.
- Planted for the review lessons:
  - 3 bugs: an off-by-one in SLA time, a timezone error that hides weekend breaches, and an N+1 query in the ticket list;
  - 1 vulnerability: SQL built from user input in the search endpoint;
  - 2 failing tests.
  - All of them are documented in `ANSWERS.md`. Used in 9.1, 9.2 and 10.5.
- A `.env.example` with placeholder names only. Keys are never committed.

### Optional Windows extension

| # | Lesson title | Feature | Surface | Task | Min |
| --- | --- | --- | --- | --- | --- |
| 11.16 | Optional: Local Models with LM Studio on Windows | Local server and compatible Claude clients | Win | Install, connect, verify and troubleshoot a local-model example | 10 |

## Timing

116 planned lessons across Welcome plus eleven sections. All duration estimates are provisional; complete setup and design iterations take priority. The original v4 timing remains in the preserved source plan and is not a delivery commitment. Section-header minutes outside the new section are inherited estimates pending revision.

| Section | Focus | Lessons | Duration |
| --- | --- | --- | --- |
| Welcome | Built last | 3 | TBD |
| 1 | Claude essentials | 12 | TBD |
| 2 | Research, connectors and MCP | 6 | TBD |
| 3 | Agentic work: docs, decks, sheets | 6 | TBD |
| 4 | Rough design, artifacts and sharing | 12 | TBD |
| 5 | Skills, plugins, automation, Claude in your apps | 10 | TBD |
| 6 | Claude Code foundations | 9 | TBD |
| 7 | Orion stack and basic working dashboard | 8 | TBD |
| 8 | Claude Design: production-style dashboard redesign | 10 | TBD |
| 9 | Built-in power tools and extending Claude Code | 13 | TBD |
| 10 | Parallel agents, automation and teams | 11 | TBD |
| 11 | Claude API, Agent SDK and model gateways | 16 | TBD |
| Total | | 116 | To be re-estimated |

Part 1 (Sections 1 to 5) remains self-contained for non-developers. Part 2 (Sections 6 to 11) assumes basic coding, terminal and Git familiarity.

## Recording plan

- **macOS** for every lesson except the Windows ones.
- **Windows PC:**
  - the separate Windows lessons 1.5 W, 5.9 W, 6.1 W and 7.1 W. Each one is complete on its own and shows only what differs, plus enough to finish the task;
  - 11.10, 11.11 and 11.16, the gateway and optional local-model lessons, on the RTX 5090 workstation.
- One take each for 3.1 (the trailer) and 11.15 (the closer).
- Name features, not menu positions. Re-check the help center, the Claude Code commands page and the models overview right before each section.
- Before publishing, test every Part 2 lesson's commands on Windows. Add a short on-screen note wherever shortcuts or paths differ (Cmd vs Ctrl), and put both keys in the cheat sheets.

## Availability caveats to state on camera

- Artifact types (Docs, Slides, Sheets, Design, Whiteboard, Dashboard, Motion and others) are set per account, so a student may not see every type.
- Features differ by plan. The course is recorded on Pro; check what Free lacks before recording and badge those lessons.
- Some Claude Code commands depend on plan or setup (for example `/teleport` needs a claude.ai subscription). Re-check the commands page before each section.
- Lessons 11.10 to 11.14 use setups Anthropic does not support; say so, and check each provider's free-tier terms right before recording.
- Agents built on the Agent SDK must use API keys or a cloud provider, not a claude.ai login ([source](https://code.claude.com/docs/en/agent-sdk/overview.md)).
- Claude for Outlook needs a Microsoft 365 business tenant with admin consent; mention it only as an option in 5.7.

## Still open

1. **Where Orion runs in production.** Recommendation: don't deploy. Orion runs locally in Docker Compose, and the capstone shows CI green plus the app running locally. A live deployment adds accounts and costs and teaches nothing about Claude.
2. **2.4 custom connector target.** A remote MCP server needs a public URL. Options:
   - host a small read-only "Orion demo" MCP server on a free host, serving the fictional ticket data;
   - connect a public remote MCP server instead.
   - Decide before recording Section 2.
3. **Free plan limits.** Confirm which Part 1 features and which artifact types Free users lack, for the badges and for 1.4.

## Sources

- [Claude help center](https://support.claude.com)
- [Claude models overview](https://platform.claude.com/docs/en/about-claude/models/overview)
- [Claude Code commands](https://code.claude.com/docs/en/commands.md)
- [Claude Code docs index](https://code.claude.com/docs/llms.txt)
- [Claude Code: other LLM gateways](https://code.claude.com/docs/en/llm-gateway.md)
- [Claude API docs index](https://platform.claude.com/llms.txt)
- [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview.md)
