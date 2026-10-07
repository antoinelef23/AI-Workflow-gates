#!/usr/bin/env bash
# CI substance/form guardrail + plan-lint on the changed features (findings M11 + L5).
# Compares spec/design of the modified features to a BASE (≠ HEAD: on a clean checkout
# tree==HEAD, --git would pass trivially — cf. content_guard --against).
#
# BASE (env)   : comparison ref (default origin/main).
# Blocking     : content_guard (substance changed without version bump) → exit 1.
# Informative  : plan-lint (just validate) — non-blocking (the Owner already approved).
# Fail-safe    : base not found → skip (no spurious CI red).
set -uo pipefail
BASE="${BASE:-origin/main}"

if ! git rev-parse --verify --quiet "$BASE" >/dev/null 2>&1; then
  echo "ℹ️  base '$BASE' not found — skip content-guard/plan-lint CI (non-blocking)."
  exit 0
fi

# Feature dir = the nearest ancestor of a changed file that holds ANY triplet member
# (spec.md / design.md / tasks.md). Depth-agnostic (work/<feature>/ and
# work/<domain>/<feature>/) AND robust to a missing spec.md — so a design.md change
# is still guarded even when its spec.md is absent or deleted in the same commit.
features=$(git diff --name-only "$BASE"...HEAD -- work/ examples/ 2>/dev/null \
  | while IFS= read -r f; do
      d=$(dirname "$f")
      while [ "$d" != "." ] && [ "$d" != "work" ] && [ "$d" != "examples" ]; do
        if [ -f "$d/spec.md" ] || [ -f "$d/design.md" ] || [ -f "$d/tasks.md" ]; then
          echo "$d"; break
        fi
        d=$(dirname "$d")
      done
    done | sort -u)

if [ -z "$features" ]; then
  echo "✅ no feature changed vs $BASE — nothing to check."
  exit 0
fi

rc=0
for feat in $features; do
  guarded=0
  if [ -f "$feat/spec.md" ]; then
    echo "🔎 content-guard: $feat/spec.md"
    python3 lab/engine/content_guard.py --against "$BASE" "$feat/spec.md" || rc=1
    guarded=1
  fi
  if [ -f "$feat/design.md" ]; then
    echo "🔎 content-guard: $feat/design.md"
    python3 lab/engine/content_guard.py --against "$BASE" "$feat/design.md" || rc=1
    guarded=1
  fi
  [ "$guarded" = 0 ] && { echo "⏭  $feat: no spec.md/design.md, skip"; continue; }
  if [ -f "$feat/tasks.md" ]; then
    echo "🔎 plan-lint (informative): $feat"
    just validate "$feat" || echo "⚠️  plan-lint $feat: see above (non-blocking)"
  fi
done
exit $rc
