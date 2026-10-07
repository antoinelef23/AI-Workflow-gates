#!/usr/bin/env bash
# Stop + SubagentStop hook — THE automatic merge gate.
# When an agent (main or sub-agent) wants to finish while Python code has changed,
# we run the evals. Red → exit 2: the agent is sent back to fix (with the output in context).
# Infinite loop avoided via stop_hook_active.
set -uo pipefail

INPUT=$(cat)

# If we are already in a re-run triggered by this hook, do not loop again.
ACTIVE=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('stop_hook_active',False))" 2>/dev/null || echo False)
[ "$ACTIVE" = "True" ] && exit 0

# Nothing to gate unless a gateable project exists (Python or a JS front/).
[ -f pyproject.toml ] || [ -f front/package.json ] || exit 0

# Only gate if code changed since the last commit (avoids paying for the evals on every turn).
# --untracked-files=all: a NEW untracked package directory otherwise shows as a
# single line "?? newpkg/" that the grep would miss — the gate would then skip a feature
# delivered as a new module (finding H7).
if git rev-parse --git-dir >/dev/null 2>&1; then
  git status --porcelain --untracked-files=all | grep -qE '\.(py|toml|ts|tsx|js|jsx|mjs|cjs)$' || exit 0
fi

OUT=$(just evals 2>&1)
STATUS=$?
if [ $STATUS -ne 0 ]; then
  echo "⛔ EVAL GATE RED — fix before finishing (spec.md §7: no green eval, no merge)." >&2
  echo "$OUT" | tail -40 >&2
  exit 2
fi

# `just evals` masks pytest rc=5 (nothing collected) as 0: "green" can mean
# "nothing ran" (findings H8/M5). We flag it — NON blocking here: the hard rule
# "no eval = no done" belongs to the orchestrator (scoped per task to the IDs
# actually implemented); blocking in this generic hook would break a legitimate
# scaffolding task with no eval written yet.
if command -v uv >/dev/null 2>&1; then
  COLLECTED=$(uv run pytest -m eval --collect-only -q 2>/dev/null | grep -c '::' || true)
  if [ "${COLLECTED:-0}" -eq 0 ]; then
    echo "⚠️  eval-gate: code changed but NO eval is collected — \`just evals\` is green by ABSENCE, not by success (spec.md §7)." >&2
  fi
fi
exit 0
