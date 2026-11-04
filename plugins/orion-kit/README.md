# Orion Kit

Claude Code skills, agents and hooks for working on the Orion customer support desk. Install it in a checkout of the Orion desk repository, so a team gets the same endpoint rules, review agents and safety hooks without copying `.claude` by hand.

## What's inside

| Type | Name | What it does |
| --- | --- | --- |
| Skill | `orion-kit:orion-endpoint` | The rules every `/api` route, model, query and report follows |
| Skill | `orion-kit:verify` | How to run and drive the desk to check a change |
| Skill | `orion-kit:orion-reply-voice` | Drafts customer replies for a named person to approve. It never sends them |
| Agent | `orion-kit:security-reviewer` | Reads code and reports security problems. It can't change files |
| Agent | `orion-kit:test-writer` | Writes and runs pytest tests in `api/tests` |
| Hook | `block-env-commit.sh` | Stops a `git commit` that would include an env file |
| Hook | `run-api-tests.sh` | Runs the offline API tests after an edit under `api/` |

## Before you install

- Claude Code 2.1.295 or later. Older versions ignore `onFailure`, so a commit check that crashes would let the commit through
- Read access to this private GitHub repository, with a git credential already stored on your machine. Claude Code can't prompt for one during install
- `git`, `jq` and `uv` on your `PATH`. Without `jq`, the commit hook blocks every commit and the test hook silently does nothing
- An Orion desk checkout: the rules, agents and test hook expect `api/orion_api/`, and the `verify` skill expects the `orion-api` and `orion-web` servers in `.claude/launch.json`

## Install

Run these from the root of your Orion checkout.

```bash
claude plugin marketplace add https://github.com/laxmimerit/orion-customer-support-agent.git#section-10
```

```bash
claude plugin install orion-kit@orion-desk-plugins --scope project
```

Project scope turns the plugin on for this repository only. It adds an entry to `.claude/settings.json`, which you commit. Each teammate still runs the two commands above.

Once the plugin reaches `main`, drop `#section-10` from the first command.

## Check it worked

```bash
claude plugin list
```

`orion-kit@orion-desk-plugins` should show as enabled. In a new session, `/agents` lists both agents, and committing a staged `.env` file is refused.

## What doesn't come with it

A plugin can't carry permission rules, so the read-only rules for the `tidb-lab` database server stay in this repository's `.claude/settings.json`. The server itself isn't bundled. Add both together if you need it, because the deny rules are what keep it read-only.

## Changing the plugin

This repository's own `.claude` folder keeps its working copies, so a change to a skill, agent or hook needs making in both places. The plugin copies differ on purpose in four ways:

- Agents and skills name each other as `orion-kit:<name>`, because plugin skills are namespaced.
- `hooks/hooks.json` uses `${CLAUDE_PLUGIN_ROOT}` where `.claude/settings.json` uses `$CLAUDE_PROJECT_DIR`.
- `run-api-tests.sh` exits early unless the repository has `api/orion_api/`.
- `orion-reply-voice` lives here only. Its source is a skill on the creator's account, not in `.claude`.

Raise `version` in `.claude-plugin/plugin.json` with every change, because teammates only receive an update when that number changes. Then check it from the repository root:

```bash
claude plugin validate .
```

```bash
claude plugin validate plugins/orion-kit
```
