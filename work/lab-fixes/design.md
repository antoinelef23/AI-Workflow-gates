---
type: design
feature: lab-fixes
version: 0.1.0
status: validated        # draft | validated | superseded
owner: Antoine (Owner)
validated_by: Owner — 2026-11-13 (validé en session, ADR-1..7 acceptés)
spec: ./spec.md          # version : 0.2.0
---

# Design — Lab fixes before iteration 3

> Scope: spec 0.1.0, BHV-1..7, INV-1..5. Small, local changes to the engine (`lab/engine/`), the
> `justfile` and the docs. No new module except a tracked-process helper in `runner.py`.

## 1. Architecture overview

Nothing new at the architecture level. Three seams change:
1. **Agent process launch** (`runner.py`, `sandbox_runner.py`): one tracked launcher, so the engine
   can terminate every agent process it started.
2. **Run control** (`orchestrate.py` main loop): a stop flag set by the signal handler, checked
   before any agent turn and before any commit; worker threads drain instead of committing.
3. **Run record** (`orchestrate.py` `journal`, `scoped_commit`, budget stop): written only in real
   runs, trailers computed from what the commit actually stages.

## 2. Reference repositories — the foundation

### 2.1 Internal

| # | Problem | Internal pattern (file:line) | Reuse | Do not reproduce |
|---|---|---|---|---|
| I-1 | Atomic state | `orchestrate.py:186` `atomic_write_json` | `state.json` written atomically on interrupt too (BHV-1a) | — |
| I-2 | Run state save | `orchestrate.py:1291` `save()` guarded by `not args.dry_run` | Same guard for the journal (BHV-2) | `journal()` (`:230`) writing unconditionally |
| I-3 | Agent launch | `runner.py:178-191` `subprocess.run(..., timeout)` | Timeout semantics kept | A blocking call the engine cannot interrupt |
| I-4 | Staged paths | `scoped_commit` `git diff --cached --name-only` (`orchestrate.py`, oracle guardrail) | The same list feeds `Artifacts:` (BHV-3) | `_commit_message` reading `node.files` (`:639`) |
| I-5 | Policy origin | `policy.effective_policy` → `(value, origin)` | The budget message reads the origin (BHV-5) | Hard-coded `(LAB_BUDGET_USD)` (`:1298`) |
| I-6 | Non-mutating lint | `justfile:57` `lint-check` (CI) | `gate` depends on it (BHV-4) | `gate: lint …` (`:106`), which runs `ruff --fix` + `format` |
| I-7 | Dated scorecards | `lab/models/scorecards/2026-11-12-*.md` naming, EVOLUTION.md §6 | `<date>-<layer>` default (BHV-6) | `stamp = "latest"` (`eval_models.py:467`) |
| I-8 | Docs scanned by a test | `tests/fde_kit/test_doc_pointers.py` | Same shape for BHV-7 | — |

### 2.2 External

| # | Problem | Reference | Pattern borrowed | Source |
|---|---|---|---|---|
| E-1 | Signals in a threaded program | Python — `signal` module | Handlers run in the **main thread** only; set a `threading.Event` the workers poll | docs.python.org/3/library/signal.html |
| E-2 | Kill an agent and its children | POSIX process groups via `subprocess.Popen(start_new_session=True)` + `os.killpg` | One group per agent: SIGTERM, grace, then SIGKILL — children included | docs.python.org/3/library/subprocess.html ; docs.python.org/3/library/os.html#os.killpg |
| E-3 | Drop queued work | `concurrent.futures.Executor.shutdown(cancel_futures=True)` (3.9+) | Queued tasks never start after the interrupt | docs.python.org/3/library/concurrent.futures.html |
| E-4 | Interrupted exit status | Shell convention 128 + signal number (SIGINT = 2) | rc 130 | Bash manual, "Exit Status" |

## 3. Stack

Python 3.12 stdlib only (`signal`, `subprocess`, `threading`, `concurrent.futures`). No new dependency.

## 4. ADRs — Architecture Decision Records

### ADR-1 — Every agent process is launched through one tracked launcher
- **Status:** accepted
- **Decision:** `runner.py` gets `run_tracked(cmd, cwd, env, timeout) -> (rc, stdout, stderr)`:
  `Popen(..., start_new_session=True)`, registered in a module-level set while it runs,
  `communicate(timeout)`; on timeout the whole group is killed (existing semantics). `terminate_all(grace_s)`
  sends SIGTERM to every registered group, waits `grace_s` (default 5 s), then SIGKILL.
  `ClaudeCliRunner` and `SandboxedClaudeRunner` both use it (the sandbox's `docker run` is the
  tracked process; its container is started with `--rm` so it goes with it).
- **Anchored on:** I-3, E-2.

### ADR-2 — Interrupt = stop flag + drain, never a commit
- **Status:** accepted
- **Decision:** in a real run, `main()` installs SIGINT/SIGTERM handlers that set `STOP`
  (`threading.Event`) and call `terminate_all`. Workers check `STOP` before an agent turn, after it,
  and right before `scoped_commit`; when set they return `"interrupted"` without committing.
  The main loop cancels queued futures (E-3), waits for workers, writes in-flight tasks as `pending`
  (atomic, I-1), journals `run_interrupted` with the in-flight IDs, prints how to resume, exits 130.
  A second signal while shutting down exits at once (`os._exit(130)`) after the atomic state write
  already done. Checkpoint and Owner-lane waits poll `STOP` (they already sleep in a loop).
- **Anchored on:** E-1, E-3, E-4, I-1.

### ADR-3 — The journal is written by real runs only
- **Status:** accepted
- **Decision:** `journal()` becomes a no-op when the run is a dry run (module flag set from
  `args.dry_run` at start, like `save()`'s guard). Dry-run output to stdout is unchanged.
- **Anchored on:** I-2.

### ADR-4 — Trailers are computed after staging
- **Status:** accepted
- **Decision:** `scoped_commit` takes the message *without* `Artifacts:`, stages as today, reads
  the staged paths (I-4), appends `Artifacts: <sorted staged paths>` and commits. `_commit_message`
  no longer emits `Artifacts:`.
- **Anchored on:** I-4.

### ADR-5 — `gate` uses the non-mutating lint check; fixing is explicit
- **Status:** accepted
- **Decision:** `justfile`: `gate: lint-check test evals check-brand check-lock`. `just lint` stays,
  documented as the fixer.
- **Anchored on:** I-6.

### ADR-6 — Budget message and scorecard stamps carry their real source
- **Status:** accepted
- **Decision:** the budget stop message reads the cap's source resolved at start: `LAB_BUDGET_USD`
  if set, else `budget_usd, <origin>` from the effective policy (I-5). `eval_models.py` default
  stamp: `f"{date.today():%Y-%m-%d}-{layer}"`, suffixed `-2`, `-3`… if the `.md` exists; an explicit
  `--stamp` is used as given (I-7).
- **Anchored on:** I-5, I-7.

### ADR-7 — Documented `just eval-models` calls are positional, and a test keeps them so
- **Status:** accepted
- **Decision:** fix `README.md`, `docs/how-to/evaluate-models.md`, `lab/models/EVOLUTION.md` and the
  recipe comment in the `justfile`; a non-eval test scans those files and fails on `eval-models`
  followed by a `key=value` token.
- **Anchored on:** I-8.

## 5. Contracts & data

- Journal event `run_interrupted`: `{"event": "run_interrupted", "inflight": [<ids>], "signal": "SIGINT"|"SIGTERM"}`.
- `state.json` value for an interrupted in-flight task: `"pending"` (no new status).
- Engine commit trailer `Artifacts:` = sorted staged paths of that commit.

## 6. Design System & Global Ready

Not applicable (command-line tooling).

## 7. Observability & rollout

`run_interrupted` is the only new event. Rollout: merge; the next fde-kit run (iteration 3) runs on it.

## 8. Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| `docker run` client killed but container keeps running | M | M | `--rm` + container killed with its client's group; checked live at the iteration-3 Docker run |
| Signal handler races a commit already in `git commit` | L | M | `STOP` checked before `scoped_commit`; a commit already started completes (it is atomic in git) |
| Tests with real signals are flaky | M | L | Shim agent sleeps a fixed time; signal sent after the journal shows the attempt started |

## 9. Changelog

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1.0 | 2026-11-13 | Owner + Claude | Design for spec 0.1.0: ADR-1..7 |
