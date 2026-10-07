# Automation surfaces

Every automated check in this repo lives on exactly one **surface**. This is the map
of what runs where, when, and why (issue #20). New scripts must declare their surface
and follow the convention below.

## The convention

| Surface | When it runs | Role | Lives in |
|---|---|---|---|
| **Claude hooks** | In-session, after the agent edits / tries to stop | Model-facing, fast/advisory; may re-prompt the agent | `.claude/hooks/`, wired in `.claude/settings.json` |
| **git pre-commit** | Every commit, on the author's machine (opt-in) | Cheap, deterministic local gate; blocks bad commits early | `.githooks/`, enabled via `git config core.hooksPath .githooks` |
| **CI** | Every PR + push to `main` | Authoritative, non-bypassable merge gate; the superset | `.github/workflows/gate.yml` |
| **human-invoked** (`just`) | On demand by a person (or reused by CI) | Control surface + dev entry points; never auto-triggered | `justfile` |
| **library** | Imported by other code, never executed directly | Pure logic | `lab/engine/registry.py`, `lab/engine/runner.py`, `lab/engine/approvals.py`, `lab/engine/content_guard.py` |

Rule of thumb: **CI is the superset** (it must catch everything). Pre-commit is the
fast local subset. Claude hooks are in-session nudges. `just` is how humans (and CI)
invoke the underlying logic.

## Inventory

### Claude hooks — `.claude/hooks/` (wired in `.claude/settings.json`)
- **`eval_gate.sh`** — `Stop` / `SubagentStop`: if Python changed, runs `just evals`;
  red evals → exit 2 (the agent is sent back to fix). Also warns when code changed but
  no eval is collected (empty-gate). *Why here:* must intercept the agent mid-session.
- **`post_edit.sh`** — `PostToolUse(Edit|Write)`: `ruff` the edited file (non-blocking).
  *Why here:* fast in-session formatting feedback.

### git pre-commit — `.githooks/pre-commit`
- For each changed `work/*` / `examples/*` feature: `content_guard --git` on spec/design
  (version-bump rule) + `orchestrate.py --validate` (plan-lint). *Why here:* cheap,
  deterministic, blocks the bad commit before it reaches CI (issues #15/#19). Enable
  with `git config core.hooksPath .githooks`; override a commit with `--no-verify`.

### CI — `.github/workflows/gate.yml`
- `just check-content-ci` → `lab/engine/ci_checks.sh`: `content_guard --against <base>` on
  changed features (blocking) + plan-lint (informative).
- `just gate-ci`: `lint-check` (non-mutating ruff) + `test` + `evals`.
  *Why here:* authoritative, non-bypassable; the superset of the local gates. Triggers
  on `pull_request` + push to `main` only (no double-run, issue #18).

### human-invoked — `justfile`
- `install`, `lint` (mutating, dev), `lint-check` (CI), `test`, `evals`, `gate`,
  `gate-ci`, `validate <feature>`, `run <feature> [supervised=1]`,
  `check-content <feature>`, `check-content-ci [base]`, `eval-models [layer] [live] [models]`.
  *Why here:* the control surface; never auto-triggered (CI and the orchestrator reuse
  these recipes rather than reimplementing them).
- **`lab/engine/approve.sh` / `reject.sh`** — human checkpoint decisions (signed approval /
  rejection). Owner-invoked only.

### orchestrator — `lab/engine/orchestrate.py`
- The DAG executor. Not a "gate" surface; it *drives* agents and internally calls
  `just evals` (the gate recipe) + the runner. Runs via `just run` or in the background.

### library — imported, never run directly
- `registry.py` (model↔role), `runner.py` + `sandbox_runner.py` (execution backends),
  `approvals.py` (HMAC tokens), `content_guard.py` (substance fingerprint).

## Same logic, three surfaces

`content_guard` and plan-lint are intentionally enforced on **all three** automatic
surfaces, each comparing against the right reference:

| Check | Claude hook | pre-commit (vs HEAD) | CI (vs base branch) |
|---|---|---|---|
| evals (`just evals`) | ✅ eval_gate.sh | — | ✅ gate-ci |
| content_guard | — | ✅ `--git` | ✅ `--against` |
| plan-lint | — | ✅ | ✅ (informative) |
| lint | ✅ post_edit (fix) | — | ✅ lint-check (verify) |
