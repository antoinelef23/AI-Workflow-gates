---
type: spec
feature: lab-fixes
version: 0.1.0
status: validated        # draft | validated | superseded
owner: Antoine (Owner)
validated_by: Owner — 2026-11-13 (validée en session, telle que proposée)
---

# Spec — Lab fixes before iteration 3: run control, honest journal and commits, non-mutating gate

## 1. Intent

The fde-kit iterations 1 and 2 surfaced engine flaws that make the run record untrustworthy or the
operator's actions unsafe: stopping a run leaves worker threads committing on their own, a dry run
pollutes the journal, commit trailers list files the commit does not contain, verifying the kit
rewrites files, and a few messages and docs mislead. Iteration 3 (failure routes, targeted reset)
and iteration 4 (retro) read exactly that record — the journal, the commit trailers — so it must be
exact first. This feature fixes those flaws and nothing else (lab-fix batch items 5, 16, 21, 22,
28, 29, 31 in `progress.md` §8).

**Target KPI:** known run-record and run-control defects from the lab-fix batch: 7 open → 0, each
locked by an eval.

## 2. Glossary

| Business term | Canonical name (code) | Definition |
|---|---|---|
| Interrupt | `run_interrupt` | SIGINT or SIGTERM received by the orchestrator process during a real run |
| In-flight task | `inflight_task` | A task whose agent turn or judging (verify, gate, scope check) has started and not ended |
| Dry run | `dry_run` | `orchestrate.py … --dry-run`: shows the plan, executes nothing |
| Run record | `run_record` | `.runs/journal.jsonl` and `.runs/state.json` of a feature |
| Commit trailer | `commit_trailer` | `Key: value` lines at the end of a commit message (`Spec-IDs`, `Artifacts`, `Run`…) |
| Gate recipe | `gate_recipe` | `just gate` (local) and `just gate-ci` (CI): the merge gate |
| Scorecard stamp | `scorecard_stamp` | The name under which `eval_models.py` writes `lab/models/scorecards/<stamp>.md|jsonl` |

## 3. Invariants

- **INV-1** — After an interrupt, the engine MUST NOT create any commit nor start any agent turn.
- **INV-2** — A dry run MUST NOT write anything under `.runs/` (no journal event, no `state.json`).
- **INV-3** — The `Artifacts:` trailer of an engine commit MUST list exactly the paths the commit
  changes (its staged paths), no more, no fewer.
- **INV-4** — No gate recipe MUST modify a tracked file: verifying never rewrites the work it checks.
- **INV-5** — A scorecard file MUST NOT be overwritten by a later campaign run unless the operator
  passed that same stamp explicitly.

## 4. Behaviors

### BHV-1 — Interrupting a run stops it entirely
- **Given** a real run with in-flight tasks
- **When** the orchestrator receives SIGINT or SIGTERM
- **Then** it stops dispatching, terminates the running agent processes (and their children),
  does not commit, writes every in-flight task back as `pending` in `state.json` (done tasks keep
  `done`), journals one `run_interrupted` event listing the in-flight tasks, prints how to resume,
  and exits with rc 130. A restart resumes from `state.json` as usual.
- **Edge cases:**
  - **BHV-1a** — A second signal during the shutdown: exits at once (rc 130), the same state and
    journal guarantees hold for what was already written (no partial `state.json`: atomic write).
  - **BHV-1b** — Interrupt while waiting at a checkpoint or an Owner-lane task: same as BHV-1, with
    no in-flight task; the checkpoint stays `pending`.

### BHV-2 — A dry run leaves no trace
- **Given** a feature with or without a run record
- **When** `--dry-run` runs
- **Then** it prints the plan as today, and `.runs/journal.jsonl` and `.runs/state.json` are
  byte-identical before and after (or still absent).

### BHV-3 — Commit trailers describe the commit
- **Given** an engine commit (task or Owner-lane)
- **When** it is written
- **Then** `Artifacts:` lists the commit's staged paths, sorted, one comma-separated line —
  including the feature's `tasks.md` run-log line when it is staged — and nothing that is not in the
  commit. A commit whose only change is the run log says so: `Artifacts: work/<f>/tasks.md`.

### BHV-4 — The local gate does not rewrite files
- **Given** a tree with a lint or format drift
- **When** `just gate` runs
- **Then** it fails on the drift like `just gate-ci` (non-mutating lint check) and no tracked file
  changes. Fixing stays an explicit action: `just lint`.

### BHV-5 — The budget message names where the cap comes from
- **Given** a run that reaches its budget cap
- **When** the engine stops before the next wave
- **Then** the message names the actual source of the cap: `LAB_BUDGET_USD` when the env var is
  set, otherwise `budget_usd` with its origin from the effective policy (floor or override).

### BHV-6 — Campaign layers do not overwrite each other
- **Given** `eval_models.py` run without `--stamp`
- **When** it writes its scorecard
- **Then** the default stamp is `<YYYY-MM-DD>-<layer>` (layer as passed, `all` included); if that
  file already exists, `-2`, `-3`… is appended. An explicit `--stamp` is used as given.

### BHV-7 — Documented commands run as written
- **Given** the repository docs (`README.md`, `docs/**`, `lab/models/EVOLUTION.md`) and the
  `justfile` recipe comments
- **When** they show a `just eval-models` invocation
- **Then** it uses the recipe's positional parameters (`just eval-models <layer> <live> <models>`),
  never `key=value`, which `just` passes through as a literal value.

## 5. Examples

### EX-1 — Interrupt during a parallel wave
```yaml
input:
  wave: [T1 (agent turn running), T2 (judging)]
  done_before: [T0]
  signal: SIGINT
expected_output:
  exit_code: 130
  new_commits: 0
  agent_processes_left: 0
  state: {T0: done, T1: pending, T2: pending}
  journal_last_event: {event: run_interrupted, inflight: [T1, T2]}
covers: [BHV-1, INV-1]
```

### EX-2 — Replay commit that only logs
```yaml
input:
  task: T6 (work already committed earlier; this attempt changes only the run log)
  files_touched: [examples/devis, examples/booking]
expected_output:
  trailer: "Artifacts: work/fde-kit/tasks.md"
covers: [BHV-3, INV-3]
```

### EX-3 — Budget message from the policy
```yaml
input:
  env: {}                      # LAB_BUDGET_USD not set
  lab_toml: {profile: squad, overrides: {budget_usd: 5}}
  spent: 5.12
expected_output: "⛔ Budget reached: $5.12 ≥ $5.00 (budget_usd, override) — stopping before the next wave."
covers: [BHV-5]
```

### EX-4 — Two campaign layers the same day
```yaml
input:
  - eval_models.py --layer behavioral --live      # 2026-11-13
  - eval_models.py --layer chain --live           # same day
expected_output:
  files: [2026-11-13-behavioral.md, 2026-11-13-behavioral.jsonl, 2026-11-13-chain.md, 2026-11-13-chain.jsonl]
covers: [BHV-6, INV-5]
```

## 6. Non-goals

- **NG-1** — No new workflow capability (failure routes, `lab next`, targeted reset, retro): that is
  iteration 3 and 4 of `work/fde-kit`.
- **NG-2** — The other open lab-fix items (1–3, 6–8, 10–12, 15, 19, 20, 23–26, 33) stay open; this
  feature does not touch them.
- **NG-3** — No change to policy semantics, profiles or checkpoint rules.
- **NG-4** — Old commits keep their trailers; history is never rewritten.

## 7. Evals — merge gate

| ID | Type | Description | Covers | Success threshold |
|---|---|---|---|---|
| EVAL-1 | deterministic | shim agent sleeping in a 2-task wave; SIGINT ⇒ EX-1 exactly (rc 130, 0 new commit, no agent process left, state, `run_interrupted`); second signal exits at once; interrupt at a checkpoint keeps it pending | BHV-1, BHV-1a, BHV-1b, INV-1 | 100% |
| EVAL-2 | deterministic | `--dry-run` on a feature with and without a run record: `.runs/` byte-identical / still absent | BHV-2, INV-2 | 100% |
| EVAL-3 | deterministic | engine commits (task, Owner-lane, run-log-only) carry `Artifacts:` = their staged paths; EX-2 exact | BHV-3, INV-3 | 100% |
| EVAL-4 | deterministic | `gate` depends on the non-mutating lint check; on a seeded drift `just gate` fails and `git status` is unchanged | BHV-4, INV-4 | 100% |
| EVAL-5 | deterministic | EX-3 exact; with `LAB_BUDGET_USD` set the message names it | BHV-5 | 100% |
| EVAL-6 | deterministic | shim campaign: EX-4 file names exact; same layer twice ⇒ `-2`; explicit `--stamp` honored | BHV-6, INV-5 | 100% |
| EVAL-7 | deterministic | no `just eval-models` invocation with `key=value` in README, docs, EVOLUTION.md, justfile comments | BHV-7 | 100% |

## 8. Open questions

*None — the behaviors come from incidents already observed and recorded in `progress.md` §8.*

## 9. Changelog

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1.0 | 2026-11-13 | Owner + Claude | From the lab-fix batch (items 5, 16, 21, 22, 28, 29, 31); validated by the Owner |
