# AI-Native Lab — standard targets (human entry points; CI, hooks and the
# orchestrator reuse them). Tolerant: with no pyproject.toml the targets no-op
# cleanly so hooks don't break on the empty skeleton.   Run `just` to list.

# Plan-lint of a feature:  just validate work/my-feature
validate feature:
    python3 lab/engine/orchestrate.py "{{feature}}" --validate

# Orchestrated run in foreground:  just run work/my-feature [supervised=1]
run feature supervised="":
    #!/usr/bin/env bash
    args=""; [ -n "{{supervised}}" ] && args="--supervised"
    caffeinate -i python3 lab/engine/orchestrate.py "{{feature}}" $args

# Plan-lint a feature living in an EXTERNAL project:
#   just validate-project /path/to/proj work/my-feature
validate-project project feature:
    python3 lab/engine/orchestrate.py "{{feature}}" --project "{{project}}" --validate

# Orchestrated run against an EXTERNAL project (work/, code, evals, git live there):
#   just run-project /path/to/proj work/my-feature [supervised=1]
run-project project feature supervised="":
    #!/usr/bin/env bash
    args=""; [ -n "{{supervised}}" ] && args="--supervised"
    caffeinate -i python3 lab/engine/orchestrate.py "{{feature}}" --project "{{project}}" $args

# Substance/form guardrail:  just check-content work/my-feature
# Fails if the SUBSTANCE of spec/design changed without a version bump.
check-content feature:
    #!/usr/bin/env bash
    set -euo pipefail
    python3 lab/engine/content_guard.py --git "{{feature}}/spec.md"
    if [ -f "{{feature}}/design.md" ]; then python3 lab/engine/content_guard.py --git "{{feature}}/design.md"; fi

# Substance/form guardrail in CI: compares changed features to a base branch.
check-content-ci base="origin/main":
    BASE="{{base}}" bash lab/engine/ci_checks.sh

# Model eval:  just eval-models [layer=all] [live=1] [models=a,b]
# Without live: refuses (billed campaign). live=1 calls the real models.
eval-models layer="all" live="" models="":
    #!/usr/bin/env bash
    extra=""; [ -n "{{live}}" ] && extra="$extra --live"; [ -n "{{models}}" ] && extra="$extra --models {{models}}"
    python3 lab/engine/eval_models.py --layer "{{layer}}" $extra

# Hash-pinned install: refuses an out-of-sync uv.lock instead of resolving anew.
install:
    #!/usr/bin/env bash
    if [ -f pyproject.toml ]; then uv sync --locked; else echo "[install] no pyproject.toml — skip"; fi

# Dev lint (mutating): auto-fix + format. Local/agent path only.
lint:
    #!/usr/bin/env bash
    if [ -f pyproject.toml ]; then uv run ruff check --fix . && uv run ruff format .; else echo "[lint] no pyproject.toml — skip"; fi

# CI lint (NON-mutating): fails on drift instead of auto-fixing it.
lint-check:
    #!/usr/bin/env bash
    if [ -f pyproject.toml ]; then uv run ruff check . && uv run ruff format --check .; else echo "[lint-check] no pyproject.toml — skip"; fi

test:
    #!/usr/bin/env bash
    if [ -f pyproject.toml ]; then uv run pytest -q -m "not eval"; else echo "[test] no pyproject.toml — skip"; fi

# Merge gate: no green eval, no merge (spec.md §7). pytest exits 5 when no eval is
# collected — not an error here; the orchestrator (anti-empty-gate) decides whether
# evals SHOULD have existed. NB: no `set -e` — we must capture pytest's rc.
evals:
    #!/usr/bin/env bash
    if [ -f pyproject.toml ] && ls tests evals 2>/dev/null | grep -q .; then
      uv run pytest -q -m eval; rc=$?
      if [ "$rc" -eq 5 ]; then echo "[evals] no eval collected — nothing to gate"; exit 0; fi
      exit "$rc"
    else echo "[evals] no evals yet — skip"; fi

# Brand guard: the lab stays generic — no client/brand proper nouns in committed
# framework content. Scope excludes work/ and **/assets/ (usage a posteriori).
check-brand:
    python3 lab/engine/brand_guard.py --all

# Lockfile guard: pyproject and the committed uv.lock must agree — a dep cannot
# be added (or swapped on the index: sha256-pinned) without a reviewable uv.lock
# diff. A nonexistent hallucinated dep fails `uv lock` outright.
check-lock:
    #!/usr/bin/env bash
    if [ -f pyproject.toml ]; then uv lock --check; else echo "[check-lock] no pyproject.toml — skip"; fi

# Run telemetry report across features:  just report [work/my-feature] [json=1]
# First-pass rate, attempts, cost per role/model, failure clusters (read-only).
report feature="" json="":
    #!/usr/bin/env bash
    args=""; [ -n "{{json}}" ] && args="--json"
    python3 lab/engine/run_report.py {{feature}} $args

# Trajectory guard: HOW the run happened (journal + git), not what it produced.
#   just check-trajectory work/my-feature
check-trajectory feature:
    python3 lab/engine/trajectory_guard.py "{{feature}}"

# Static-context payload per role. Gates only once [context] max_static_tokens
# is declared in lab/models/registry.toml (soft budget).
context-budget:
    python3 lab/engine/context_budget.py

# Local merge gate (mutating lint).
gate: lint test evals check-brand check-lock
    @echo "✅ gate OK"

# CI merge gate (non-mutating lint — drift fails CI instead of being auto-fixed).
gate-ci: lint-check test evals check-brand check-lock
    @echo "✅ gate-ci OK"
