#!/usr/bin/env bash
# PreToolUse on Bash: stop a git commit when a file going into it looks like an env file.
# Exit 2 blocks the command and sends stderr to Claude. Only file names are printed, never contents.
set -euo pipefail

input=$(cat)
command=$(jq -r '.tool_input.command // ""' <<<"$input")
cwd=$(jq -r '.cwd // "."' <<<"$input")

# A false match (git log --grep commit) costs nothing: it only runs the check below.
grep -Eq 'git[^;&|]*[[:space:]]commit([[:space:]]|$)' <<<"$command" || exit 0

top=$(git -C "$cwd" rev-parse --show-toplevel)
repo_git() { git -C "$top" -c core.quotePath=false "$@"; }

# Deletions are left out: removing a committed env file is the fix, not the problem.
candidates=$(repo_git diff --cached --name-only --diff-filter=d)

# This runs before the command, so `git add -A && git commit` and `git commit -a` have not
# staged anything yet. Count what they could add, including paths named in a forced add.
adds=$(grep -Eo 'git[[:space:]]+add[^;&|]*' <<<"$command" || true)
if [[ -n "$adds" ]] || grep -Eq '[[:space:]](-[a-zA-Z]*a[a-zA-Z]*|--all)([[:space:]]|$)' <<<"$command"; then
  candidates+=$'\n'"$(repo_git ls-files --modified --others --exclude-standard)"
  candidates+=$'\n'"$(tr -s '[:space:]' '\n' <<<"$adds" | tr -d "\"'")"
fi

# .env, .env.local, .env_backup, .envrc, prod.env, prod.env.local; templates such as .env.example pass.
blocked=$(grep -Ei '(^|/)(\.env(rc)?([._-][^/]*)?|[^/]+\.env(\.local)?)$' <<<"$candidates" \
  | grep -Eiv '\.(example|sample|template)$' | sort -u || true)

[[ -z "$blocked" ]] && exit 0

{
  echo "Commit blocked. These look like env files:"
  sed 's/^/  /' <<<"$blocked"
  echo "Unstage them with: git restore --staged <file>"
  echo "If the command stages files too, stage only the files you mean to commit, then commit separately."
} >&2
exit 2
