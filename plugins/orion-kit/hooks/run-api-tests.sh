#!/usr/bin/env bash
# PostToolUse on Write|Edit: after an edit under api/, run the API tests that need no database.
# Same command as CI. Silent on success; exit 2 sends the failure to Claude.
set -uo pipefail

file=$(jq -r '.tool_input.file_path // empty')
[[ -n "$file" ]] || exit 0

# Ask git where the file sits, so an edit inside a worktree tests that worktree.
dir=$(dirname "$file")
prefix=$(git -C "$dir" rev-parse --show-prefix 2>/dev/null) || exit 0
top=$(git -C "$dir" rev-parse --show-toplevel)

case "$prefix" in
  api/.venv/* | api/.pytest_cache/* | */__pycache__/*) exit 0 ;;
  api/*) ;;
  *) exit 0 ;;
esac

# A user-scope install reaches every repo, so leave any other project's api/ folder alone.
[[ -d "$top/api/orion_api" ]] || exit 0

cd "$top/api" || exit 2
output=$(uv run --locked pytest -m "not live" -q --tb=short 2>&1) && exit 0

{
  echo "API tests failed after editing ${file#"$top"/}:"
  tail -n 40 <<<"$output"
} >&2
exit 2
