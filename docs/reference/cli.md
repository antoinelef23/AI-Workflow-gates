# CLI reference

Technical description of the command-line surface: the orchestrator
(`lab/engine/orchestrate.py`), the `just` recipes, and the helper scripts.
Facts only. For workflows, see the how-to guides linked at each section.

Related reference pages: [environment.md](environment.md) (environment
variables), [commit-format.md](commit-format.md) (commit shape produced by the
orchestrator), [status-line.md](status-line.md) (live run state),
[agents-and-skills.md](agents-and-skills.md).

---

## orchestrate.py

Background orchestrator. Reads a feature's `tasks.md`, builds the
`depends_on` DAG, runs ready tasks in parallel via the configured runner,
applies the eval gate after each task, and handles checkpoints.

### Usage

```
python3 lab/engine/orchestrate.py <feature> [--dry-run] [--validate] [--supervised] [--force]
```

`<feature>` is a feature directory (relative to the repo root) containing
`tasks.md`, e.g. `work/my-feature`.

How-to: [run-the-orchestrator.md](../how-to/run-the-orchestrator.md).

### Flags

| Flag | Effect | Default |
|---|---|---|
| `feature` (positional) | Feature directory containing `tasks.md`. Resolved against the repo root. | required |
| `--dry-run` | Print the plan and per-node actions; run nothing. Skips the orchestrator lock, state persistence, and the checkpoint-secret requirement. | off |
| `--validate` | Plan-lint `tasks.md` and exit. Prints node count, frontmatter status, warnings, errors, and the `verify` commands. Exit 1 if errors, else 0. | off |
| `--supervised` | Force every checkpoint to `blocking` (ignore `mode: auto`). | off |
| `--force` | Ignore `status: approved` and plan-lint errors. Not recommended. | off |

### Behavior constants

These are fixed in `lab/engine/orchestrate.py` (not CLI flags); some are
overridable by environment variable (see [environment.md](environment.md)).

| Constant | Value | Meaning |
|---|---|---|
| `MAX_EVAL_RETRIES` | 3 | Attempts per task before it is marked `failed`. |
| `MAX_PARALLEL` | 3 | Max concurrent tasks per wave (`ThreadPoolExecutor`). |
| `MAX_CP_REJECTS` | 2 | Rejections of one checkpoint before it is marked `failed`. |
| `MAX_TURNS` | 100 | Max agent turns per `claude` call. |
| `TASK_TIMEOUT_S` | 2400 | Wall-clock per agent call (`LAB_TASK_TIMEOUT`, seconds). |
| `BUDGET_USD` | 0 | Campaign cost cap; 0 disables (`LAB_BUDGET_USD`). |

### Exit codes

| Code | Condition |
|---|---|
| 0 | All nodes `done`; or `--validate` with no errors. |
| 1 | Plan-lint errors (no `--force`); `status` not `approved` (no `--dry-run`/`--force`); checkpoint present but `LAB_APPROVAL_SECRET` unset and no opt-in; orchestrator lock already held; deadlock; budget reached; run finished with any node not `done`; `--validate` with errors. |

### Run artifacts

Written under `<feature>/`:

| Path | Content |
|---|---|
| `.runs/orchestrator.lock` | Inter-process `flock` held for the run duration. |
| `.runs/state.json` | Per-node status; read on resume (done tasks skipped). |
| `.runs/journal.jsonl` | One JSON line per event (`task_attempt`, `review`, `run_end`, …). |
| `.runs/<CP>-review.md` | Reviewer panel report per checkpoint. |
| `.approvals/<CP>` | Signed approval token (written by `approve.sh` or auto-path). |
| `.approvals/<CP>.rejected` | Rejection record (written by `reject.sh`). |
| `tasks.md` (appended) | Run-log table rows. |

---

## just recipes

Run `just` with no argument to list recipes. Each recipe delegates to a
script; recipes no-op cleanly when `pyproject.toml` is absent.

| Recipe | Command | Purpose |
|---|---|---|
| `validate feature` | `python3 lab/engine/orchestrate.py "{{feature}}" --validate` | Plan-lint a feature's `tasks.md`. |
| `run feature supervised=""` | `caffeinate -i python3 lab/engine/orchestrate.py "{{feature}}" [--supervised]` | Orchestrated run in foreground; `--supervised` added when `supervised` is non-empty. |
| `check-content feature` | `python3 lab/engine/content_guard.py --git "{{feature}}/spec.md"` (and `design.md` if present) | Substance/form guardrail vs `HEAD`; fails if substance changed without a version bump. |
| `check-content-ci base="origin/main"` | `BASE="{{base}}" bash lab/engine/ci_checks.sh` | CI substance/form guardrail + plan-lint vs a base branch. |
| `check-brand` | `python3 lab/engine/brand_guard.py --all` | Brand/proper-noun guard: fails if committed framework content contains a denied name. Scope excludes `work/` + `**/assets/`. |
| `check-lock` | `uv lock --check` | Lockfile guard: fails when `pyproject.toml` and the committed hash-pinned `uv.lock` disagree (anti hallucinated/swapped dependency). |
| `report feature="" json=""` | `python3 lab/engine/run_report.py [feature] [--json]` | Run-telemetry report: first-pass rate, attempts, cost per role/model, failure clusters. Read-only. |
| `check-trajectory feature` | `python3 lab/engine/trajectory_guard.py "{{feature}}"` | Trajectory guard: journal integrity + commit scope of a feature run (HOW, not WHAT). |
| `context-budget` | `python3 lab/engine/context_budget.py` | Static-context payload per role; gates only once `[context] max_static_tokens` is declared in the registry. |
| `eval-models layer="all" live="" models=""` | `python3 lab/engine/eval_models.py --layer "{{layer}}" [--live] [--models {{models}}]` | Run the model-eval harness; `--live` calls real (billed) models. |
| `install` | `uv sync --locked` (if `pyproject.toml`) | Install dependencies, hash-pinned; refuses an out-of-sync `uv.lock`. |
| `lint` | `uv run ruff check --fix . && uv run ruff format .` | Mutating lint: auto-fix + format. Local/agent path. |
| `lint-check` | `uv run ruff check . && uv run ruff format --check .` | Non-mutating lint: fails on drift instead of fixing. |
| `test` | `uv run pytest -q -m "not eval"` | Run unit/integration tests (excludes evals). |
| `evals` | `uv run pytest -q -m eval` | Merge gate: run evals. Exit 5 (no eval collected) is treated as success. |
| `gate` | `lint test evals check-brand check-lock` | Local merge gate (mutating lint). |
| `gate-ci` | `lint-check test evals check-brand check-lock` | CI merge gate (non-mutating lint). |

How-to: [evaluate-models.md](../how-to/evaluate-models.md),
[commit-with-rationale.md](../how-to/commit-with-rationale.md).

---

## Helper scripts

### approve.sh

```
lab/engine/approve.sh <CP-n> <feature_dir>
```

Creates the signed (HMAC) approval token the orchestrator waits for, by
calling `lab/engine/approvals.py sign`. Author is `git config user.name` or
`whoami`. Requires `LAB_APPROVAL_SECRET` to produce a forgery-resistant
token. Both arguments are required.

### reject.sh

```
lab/engine/reject.sh <CP-n> <feature_dir> "reason" [Tn ...]
```

Writes `<feature_dir>/.approvals/<CP-n>.rejected` with `reason=`, optional
`tasks=` (the trailing `Tn` IDs; default: all the checkpoint's tasks), `by=`,
`at=`. The orchestrator reopens the targeted tasks with the reason passed
verbatim, then re-presents the checkpoint. `reason` is required. Beyond
`MAX_CP_REJECTS` (2) rejections of the same checkpoint, the run stops.

### content_guard.py

```
content_guard.py <old.md> <new.md>              # compare two files
content_guard.py --git <path.md>                # working tree vs HEAD (advisory)
content_guard.py --against <ref> <path.md>      # working tree vs <ref> (CI)
```

Extracts a substance fingerprint (per-ID assertions INV/BHV/EX/EVAL/NG/OQ/ADR
with continuation lines, glossary names, KPI lines), normalized to ignore
form. Exit 1 if substance changed without a `version:` bump. Invoked by
`just check-content` and `lab/engine/ci_checks.sh`.

### ci_checks.sh

```
[BASE=origin/main] bash lab/engine/ci_checks.sh
```

For each feature changed under `work/` or `examples/` vs `BASE` (default
`origin/main`): runs `content_guard.py --against "$BASE"` on `spec.md` and
`design.md` (blocking, exit 1 on substance drift) and `just validate`
(informative, non-blocking). Skips with exit 0 if `BASE` is not found or no
feature changed. Invoked by `just check-content-ci`.

### eval_models.py

```
python3 lab/engine/eval_models.py [--layer L] [--models a,b] [--runs N] [--live] [--stamp S] [--budget USD]
```

| Flag | Effect | Default |
|---|---|---|
| `--layer` | One of `behavioral`, `chain`, `scorecard`, `all`. | `all` |
| `--models` | Comma-separated model IDs. | registry models |
| `--runs` | Trials per golden task (scorecard). | 3 |
| `--live` | Call the real (billed) models. | off |
| `--stamp` | Scorecard name. | `latest` |
| `--budget` | Campaign `$` cap; 0 = none. | 0.0 |

Without `--live` and without `LAB_MODEL_SHIM`, refuses to run (exit 2).
Exit 2 also if no model resolves. Invoked by `just eval-models`.

How-to: [evaluate-models.md](../how-to/evaluate-models.md). Methodology:
[okf-evaluation.md](../explanation/okf-evaluation.md).

### brand_guard.py

```
brand_guard.py --all                 # all tracked in-scope files (CI gate)
brand_guard.py --staged              # staged in-scope files (pre-commit)
brand_guard.py <file> [<file> ...]   # explicit files
```

Enforces the "no client/brand proper nouns" rule mechanically: scans committed
framework content against `lab/engine/brand_denylist.txt` (word-boundary,
case-insensitive). **Scope** excludes usage a posteriori — `work/**` and
`**/assets/**` — plus the denylist itself and data/binary files. Exit 1 on any
hit (prints `file:line` + term), 0 if clean. Override the denylist path with
`LAB_BRAND_DENYLIST`. Invoked by `just check-brand` (wired into `gate`/`gate-ci`)
and the pre-commit hook. Never list a lab spec-ID prefix (INV/BHV/EX/EVAL/NG/OQ/ADR)
in the denylist — they are vocabulary, not brands.
