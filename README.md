# Orion Customer Support Agent

Course repository for rebuilding Orion's customer support application with Claude Code.

The repository is **private during preparation**. The creator intends to make both branches public when the course is published. No visibility change is authorised before that release.

## Branches

| Branch | Purpose |
| --- | --- |
| `orion-legacy` | Existing Flask/Jinja2 application, MySQL-compatible data and legacy-environment setup. Copy this first to prepare the inherited system. |
| `main` | Replacement built from scratch during the course. It currently contains documentation and ignore rules only. |

Start with the legacy branch in its own folder:

```sh
git clone --branch orion-legacy --single-branch https://github.com/laxmimerit/orion-customer-support-agent.git orion-legacy
```

Follow that branch's README to restore your personal legacy database and run the inherited app. Keep private configuration and credentials out of Git. The hosted reference is https://orion-legacy.vercel.app.

For the replacement, use a separate workspace on `main`:

```sh
git clone --branch main --single-branch https://github.com/laxmimerit/orion-customer-support-agent.git orion-course
cd orion-course
git switch -c my-orion-build course-start
```

`course-start` preserves the documentation-only starting point even after `main` contains the completed implementation. Build the new project and its configuration on your own branch during the course, carrying in your investigation notes and reviewed requirements/design. Do not copy the legacy application into `main` as the replacement scaffold. Course code progresses on `main`; lesson checkpoints will be added as the work is produced.

The course covers a new FastAPI backend, Next.js frontend, checked SQL analysis, a deliberate MySQL-to-PostgreSQL-compatible migration, evaluated retrieval and a reviewed email/communication workspace.

A branch is not an access boundary: people with repository access can inspect both branches and history. The release will deliberately provide the inherited legacy source as well as the course implementation. Never commit private environment files, account passwords, provider keys or mailbox tokens on either branch.

Orion and its historical records are synthetic course material. Recording and narration are currently on hold.
