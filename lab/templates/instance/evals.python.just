# Merge gate: no green eval, no merge. pytest exits 5 when no eval is collected — the
# message says so and the run stays green; the orchestrator's anti-empty-gate decides
# whether evals SHOULD have existed.
evals:
    #!/usr/bin/env bash
    uv run pytest -q -m eval; rc=$?
    if [ "$rc" -eq 5 ]; then echo "[evals] no eval collected — nothing to gate"; exit 0; fi
    exit "$rc"
