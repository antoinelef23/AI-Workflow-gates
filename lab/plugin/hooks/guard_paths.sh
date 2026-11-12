#!/usr/bin/env bash
# PreToolUse guard — refuses writes under .approvals/ or .runs/ (INV-1, ADR-4).
# Exit 2 = deny; exit 0 = allow. Fails closed if the payload cannot be parsed.
# NotebookEdit sends its target as `notebook_path`, the other tools as `file_path`.
set -uo pipefail

INPUT=$(cat)
FILE=$(printf '%s' "$INPUT" | python3 -c "import sys,json; t=json.load(sys.stdin).get('tool_input',{}); print(t.get('file_path') or t.get('notebook_path') or '')" 2>/dev/null) || {
  echo "⛔ guard_paths: unreadable hook payload — blocking." >&2
  exit 2
}

case "/$FILE" in
  */.approvals/* | */.runs/*)
    echo "⛔ Writing under .approvals/ or .runs/ is reserved to the engine and the human Owner: $FILE" >&2
    exit 2
    ;;
esac
exit 0
