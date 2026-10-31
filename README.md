# Orion Classic — instructor-only reference

Traditional Flask/Jinja2 support desk backed by MySQL-compatible TiDB. The deliberately limited interface provides ticket/customer/conversation lookup, subject-only keyword search, a knowledge base, company handbook, staff requests and a status-count report. It is a read-only historical reference, not a live messaging service. All records and company activity are fictional.

Live reference: https://orion-legacy.vercel.app

Learners receive `../orion-environment/`, the reference URL and their own seeded database. They do **not** receive this source, private environment files or instructor tools. They investigate and build a replacement from scratch. Preserve the original source/data/brand history in `../orion-course-resources/`; its old pre-launch brief is not the current learner scenario.

## Credentials

`.env` holds instructor database preparation credentials. `.env.vercel` holds the generated read-only reference account. Both have owner-only permissions, are excluded by `.gitignore`, and are excluded from deployment uploads. No Keychain dependency. `.mcp.json` contains a launcher, not credentials.

The launcher loads `.env` into its child environment and starts the TiDB MCP server. Tested compatibility pins: `pytidb[mcp]==0.0.14` and `mcp==1.30.0`. The vendor's unpinned command currently resolves MCP v2, which does not provide the FastMCP API this server imports. The API/migration and MCP reader checks are distinct: the deployed application never uses the instructor root account.

## Run this private repository

Copy `.env.example` to `.env`, fill in your own MySQL-compatible TiDB connection, and restore to an empty personal database if needed:

```sh
uv run --with PyMySQL==1.1.2 python tools/lab.py restore
uv run --with PyMySQL==1.1.2 python tools/lab.py check
uv run --no-project --with-requirements requirements.txt python tools/serve.py
```

The local preview listens on http://127.0.0.1:8080 . The supplied SQL is in `database/`. The server is intentionally read-only. Use a SELECT-only database account for a hosted reference; instructor provisioning and actual runtime tests create/check that boundary separately.

For a container, build the Dockerfile and provide runtime environment variables using an ignored environment file. The database remains outside the image. Vercel uses sensitive runtime environment variables configured on the project.

## Build and verification

The Dockerfile packages the application and uses `PORT`. No database files or `.env` are copied into the image. This Mac currently has no Docker engine, so no local container build is claimed. The actual Flask runtime has been tested against TiDB and deployed on Vercel's Python 3.12 runtime.

Instructor commands, from the course root:

```sh
python3 orion-legacy/tools/package_database.py
python3 -m unittest discover -s orion-legacy/tests -v
python3 orion-environment/tools/lab.py verify-package
```

`tools/live_database.py` connects/restores/verifies the dedicated lab and provisions a SELECT-only reference user. It refuses a nonempty restore target. `tools/check_runtime.py` exercises real Flask routes against TiDB. `tools/check_mcp.py` initializes the actual server and checks a read-only ticket-count query. Runtime packages come from `requirements.txt`; environment keys are `TIDB_HOST`, `TIDB_PORT`, `TIDB_USERNAME`, `TIDB_PASSWORD`, `TIDB_DATABASE`.

## Deployment boundary

Only `index.py`, `requirements.txt`, `pyproject.toml`, `vercel.json` and approved `app/` Python/template/CSS/SVG files are uploaded. Vercel runtime variables are sensitive values from the read-only environment. SQL seeds, tools, tests, review artifacts, MCP configuration and environment files are not uploaded. The source project is private.

The first Vercel runtime check caught missing dependencies because Vercel preferred `pyproject.toml` over `requirements.txt`. The project dependencies are now explicit in both. Browser review caught an inappropriate dark-surface logo and a missing In Progress filter; corrected source was redeployed. A successful build alone was not accepted.

See `review/` for actual database/MCP/runtime and browser evidence; `SOURCES.md` for provider documentation. No fresh course recording or narration was generated. Existing course media remain preserved.
