# Orion Customer Support Agent — legacy system

This is the `orion-legacy` branch: the inherited support application and data used at the start of the course. Copy this branch first to set up your own legacy environment. Build the replacement separately on `main`; do not use this implementation as the new application's scaffold.

Repository: https://github.com/laxmimerit/orion-customer-support-agent
Hosted legacy reference: https://orion-legacy.vercel.app

The repository is private during preparation. Both `main` and `orion-legacy` are intended to become public when the creator publishes the course. No visibility change is made before that release.

## Copy the inherited environment

```sh
git clone --branch orion-legacy --single-branch https://github.com/laxmimerit/orion-customer-support-agent.git orion-legacy
cd orion-legacy
```

The branch contains Flask/Jinja2 source, a MySQL-compatible SQL snapshot, configuration placeholders and legacy setup helpers. Orion and the historical records are synthetic course material. The Classic desk has a working queue, filters, ownership, conversation/customer/subscription/invoice pages and knowledge articles. Subject search and status reporting remain deliberately limited.

Use your own empty MySQL-compatible TiDB database. Duplicate `.env.example` as `.env` in your editor and fill in your own connection values privately. No macOS Keychain is required. Never reuse the instructor's credentials. The `.env` file and other private environment variants are ignored by Git and Docker uploads.

```sh
python3 tools/lab.py verify-package
uv run --no-project --with-requirements requirements.txt python tools/lab.py restore
uv run --no-project --with-requirements requirements.txt python tools/lab.py check
uv run --no-project --with-requirements requirements.txt python tools/serve.py
```

Use `python` on Windows if `python3` is unavailable. The local reference listens on http://127.0.0.1:8080. Restore refuses a nonempty database; an interruption may leave a partial restore, so check the result and use a fresh empty personal database when needed. Setup commands restore the inherited system; they do not implement replacement features.

## Docker option

With an available Docker engine, build the legacy image and provide your own private runtime configuration:

```sh
docker build -t orion-legacy .
docker run --rm --env-file .env -p 8080:8080 orion-legacy
```

The database is external to the container. The image excludes private environment files, the seed, Git metadata and instructor tools. The Dockerfile is prepared; local Docker execution was not performed on the preparation Mac. The native Flask/TiDB runtime and Vercel deployment have separate recorded checks. Do not treat these as a claim that every learner platform/container is tested.

## Database tools and reset

The project MCP launcher reads the private `.env` and starts the TiDB server with compatibility pins `pytidb[mcp]==0.0.14` and `mcp==1.30.0`. Launch Claude Code from this branch's root, inspect the configuration and approve it only for the intended personal lab. Verify actual schema/count tool results; start investigations read-only.

To discard changes in a personal database named `orion_lab`:

```sh
uv run --no-project --with-requirements requirements.txt python tools/lab.py reset --confirm RESET_orion_lab
```

Reset drops/restores known baseline tables in that selected database. It refuses a wrong confirmation, wrong identity or unexpected tables. Keep replacement code and the later PostgreSQL-compatible target separate. Reset is not a backup or migration tool.

## Move into the course build

Use a second folder for `main`:

```sh
git clone --branch main --single-branch https://github.com/laxmimerit/orion-customer-support-agent.git orion-course
```

Create the replacement's configuration, backend, frontend, SQL reports, model tools and communication features during the course. The migration creates and connects a separate PostgreSQL-compatible target before transferring/reconciling records. The original source stays available for comparison and rollback.

Files named `check_*`, `live_database.py`, `package_database.py` and `rehearse_migration.py` are instructor maintenance/rehearsal tools, not commands required to complete legacy setup or substitutes for the code authored during teaching. Do not run provisioning/migration tools against a shared database. Course media and private runtime evidence are not in this branch.

Both branches and repository history will be visible at the planned public release. Credentials must remain excluded everywhere. Course integrations prefer supported connectors/OAuth/MCP for Gmail, Google Sheets, Drive and other services. Database/model configuration remains private. Authorise each actual connection and inspect its capabilities; Claude-hosted connections do not automatically authorise the replacement app. No mail-password setup workflow.
