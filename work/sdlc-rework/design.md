---
type: design
feature: sdlc-rework
version: 1.2.0
status: validated
owner: Antoine (Owner)
validated_by: Owner — 2026-07-21 (amendments 1.1.0, 1.2.0: 2026-07-22)
spec: ./spec.md          # version : 1.2.0
---

# Design — SDLC rework

## 1. Technical picture

Five small, standalone modules under `lab/engine/`, in the exact shape of the existing
guards, plus one shared reader. No new dependency (stdlib only — `tomllib`, `json`,
`subprocess`). All wired as `just` recipes; only `check-deps` joins `gate`/`gate-ci`
(fast, deterministic); the rest are Owner-driven inspection tools.

| Module | Recipe | Gate? |
|---|---|---|
| `lab/engine/journal_io.py` | — (shared reader) | — |
| `lab/engine/run_report.py` | `just report [feature]` | no (read-only inspection) |
| `lab/engine/trajectory_guard.py` | `just check-trajectory <feature>` | no (feature-scoped, post-run) |
| `lab/engine/context_budget.py` | `just context-budget` | no (soft budget, fails only if declared) |
| — (uv lockfile, no lab module) | `just check-lock` | **yes** (gate + gate-ci) |

One minimal touch to `lab/engine/orchestrate.py`: journal `verify_fail` / `eval_fail`
events (one line each) so BHV-1b clustering has data. Event vocabulary stays additive —
existing consumers unaffected.

## 2. Reference patterns (anchoring)

Every choice points to a pattern already in the repo — nothing is invented:

- **Guard shape** (argv → scan → print offenders → rc 0/1, standalone + testable):
  `lab/engine/brand_guard.py`, `lab/engine/content_guard.py`.
- **Lockfile enforcement**: `uv sync --locked` / `uv lock --check` — uv's own
  documented CI pattern; the lockfile was already committed with sha256 hashes.
- **Git-based diffing** for BHV-2b: `content_guard.py --git` and
  `scoped_commit()`/`paths_overlap` in `orchestrate.py`.
- **tasks.md parsing**: reuse `lab/engine/plan.py::parse_tasks_md` (shared by
  orchestrator and plan-lint already) — the trajectory guard gets `files_touched` from
  the same parser, no second grammar.
- **Journal vocabulary**: `orchestrate.py::journal()` events (`task_attempt`,
  `task_done`, `task_failed`, `task_blocked`, `review`, `run_end`).
- **Registry read**: `tomllib` on `lab/models/registry.toml`, same as
  `lab/engine/registry.py`.
- External anchor: the *New SDLC With Vibe Coding* whitepaper (May 2026) — trajectory
  evaluation, quality flywheel, static/dynamic context boundary, slopsquatting risk.

## 3. ADRs

### ADR-1 — The journal is the only trajectory source (NG-2)
Claude sessions are not persisted by the lab; `.runs/journal.jsonl` is already written
under lock by the orchestrator and survives runs. Parsing session transcripts would add
a fragile dependency on a vendor format. Consequence: trajectory checks are limited to
what the journal + git history prove — accepted.

### ADR-2 — Token counting is `len(chars) / 4`, no tokenizer dependency
A real tokenizer (tiktoken & co.) would add a third-party dep for a number whose only
use is a *relative* budget. The chars/4 heuristic is stable, offline (INV-2), and
errs consistently. The budget in the registry is calibrated against the same heuristic,
so absolute accuracy is irrelevant.

### ADR-3 — Supply-chain integrity via the hash-pinned lockfile (supersedes the allowlist, spec 1.2.0)
Versions 1.0.0/1.1.0 shipped a dependency allowlist (`dep_guard.py`), refuted at
CP-1 review on three grounds, all verified: a nonexistent hallucinated dep already
fails mechanically (`uv sync` / test collection); an offline list is structurally
blind to a *registered* squat, and the agent writes the allowlist line itself — the
human's real review signal is the `pyproject.toml` diff, which the list merely
duplicated; an exact mirror of `pyproject.toml` is the second-source-of-truth
anti-pattern this design's own ADR-5 forbids.

The retained mechanism carries information that IS non-derivable: the resolved
hashes. `uv.lock` (committed, sha256) becomes the only install source —
`just install` runs `uv sync --locked`, and `just check-lock` (`uv lock --check`)
gates lockfile freshness in `gate`/`gate-ci`. A dep cannot be added without a
reviewable `uv.lock` diff, and a package cannot be silently swapped on the index
without breaking its hash. No lab-side list to maintain (NG-1).

### ADR-4 — Soft budget, hard only when declared (BHV-3)
Failing the gate on a budget nobody has calibrated yet would block every commit on day
one. The tool always *measures*; it only *gates* once the Owner declares
`[context] max_static_tokens` in the registry. Same fusible philosophy as
`content_guard` (mechanism first, enforcement by explicit opt-in).

### ADR-5 — `AGENTS.md` is a pointer, not a copy
Duplicating CLAUDE.md would create a second source of truth that drifts. The shim
carries only: what the lab is, where the rules live (CLAUDE.md), reading order
(spec → design → tasks). Enforced by EVAL-5 (must reference CLAUDE.md, must not
restate hard rules).

## 4. Compliance / constraints

- Brand guard scope: all new files are framework content ⇒ scanned (`work/sdlc-rework/`
  itself excluded as `work/**`). No proper noun anywhere in the new modules.
- `ruff` clean, tests under `tests/sdlc_rework/`, evals marked `@pytest.mark.eval`.
- Python ≥ 3.11 stdlib only (`tomllib` is 3.11+; repo targets 3.12).

## 5. History

| Version | Date | By | Change |
|---|---|---|---|
| 1.0.0 | 2026-07-21 | Owner + agent | Initial design, anchored on existing guard patterns |
| 1.1.0 | 2026-07-22 | Owner | ADR-3 extended: `--strict` orphan check in gate-ci (spec 1.1.0 / BHV-4a) |
| 1.2.0 | 2026-07-22 | Owner (CP-1 review) | ADR-3 superseded: allowlist dropped for hash-pinned lockfile enforcement (spec 1.2.0) |
