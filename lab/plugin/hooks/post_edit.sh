#!/usr/bin/env bash
# PostToolUse (Edit|Write) hook — quick non-blocking lint on the modified Python files.
# Receives the event JSON on stdin. Always exits 0 (informative, never blocking).
set -uo pipefail

INPUT=$(cat)
FILE=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null || true)

case "$FILE" in
  *.py)
    if command -v uv >/dev/null 2>&1 && [ -f pyproject.toml ]; then
      uv run ruff check --fix "$FILE" >&2 || true
      uv run ruff format "$FILE" >&2 || true
    fi
    ;;
esac
exit 0
