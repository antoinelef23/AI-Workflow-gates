# Review CP-1 — panel of 1 — aggregated verdict: WARN (WARN)

## Panelist 1 — claude-opus-5-5 — lens: full review
VERDICT: WARN

# Reviewer report: lab-fixes, CP-1 (T1, T2, T4, T5)

**Verdict: WARN.** I found one deviation from the spec. In T2, interrupting a run while it waits on an Owner-lane task records that task as in-flight, but spec BHV-1b says such an interrupt has no in-flight task. Everything else in T1, T2, T4 and T5 matches the spec and design, and the tests and lint I ran are green.

## ✅ Conformant

**Traceability**
- All 4 commits (`52015e8`, `089930d`, `4052e13`, `211b04a`) use the canonical subject `[IDs]`, include a `Why:` body, and carry the `Spec-IDs:` and `Run: auto` trailers. Their IDs match the `implements` list of each task.
- Each commit touched only its task's `files_touched`, plus the `tasks.md` run-log line. Both OQ deltas from spec 0.2.0 were applied:
  - OQ-2: the two test stubs now patch `run_tracked`.
  - OQ-1: `test_eval_8_kit_work_holds_no_demo_feature`.

**T1 (ADR-1)**
- `lab/engine/runner.py:58` `run_tracked` uses `Popen(start_new_session=True)`, keeps a registry protected by a lock, and kills the whole process group on timeout before re-raising. Both runners keep their timeout messages.
- `runner.py:89` `terminate_all` sends SIGTERM, waits a grace period while polling the whole group (not just its leader), then sends SIGKILL and returns the count. This follows E-2.
- `lab/engine/sandbox_runner.py:195` uses `run_tracked`, and `--rm` is still on the `docker run` (`:97`).

**T2 (ADR-2)**
- The signal handler only sets things up and does the actual work in a helper thread (`orchestrate.py:202`), which follows E-1.
- `STOP` is checked before the agent turn, after it, after settling, after verify, after the eval gate, and right before `scoped_commit`. This satisfies INV-1.
- Futures are cancelled and the pool shuts down with `cancel_futures` (`:1439`), following E-3.
- `finish_interrupted` (`:1356`) does what BHV-1 asks: it resets tasks to pending, writes state atomically through `save()`, writes the `run_interrupted` event with `inflight` and `signal` (matching the design §5 contract), prints how to resume, and returns rc 130.
- A second signal calls `os._exit(130)` (BHV-1a).
- The checkpoint wait is interruptible: `STOP.wait(20)` at `:1196` and the `interrupted` check at `:1450` (BHV-1b, checkpoint case).
- Handlers are installed only on real runs (`:1376`).
- `_set_active(False)` in `run_task`'s `finally` makes sure an interrupted task never leaves a sibling stuck in `_settle`/`_set_active`.

**T4 (ADR-5, ADR-7)**
- `justfile:107` is `gate: lint-check …` and `lint` is documented as the explicit fixer. The comment at `justfile:39` uses positional parameters.
- EVAL-4 checks the dependency through `just --dump` and runs a seeded-drift case on a temporary project. It does not run `just gate` on the kit, as the plan required.

**T5 (ADR-6)**
- `lab/engine/eval_models.py:334` `default_stamp` builds `<date>-<layer>` and appends `-2`, `-3`… when the `.md` already exists. An explicit `--stamp` is used as given (`:484`).
- EVAL-6 covers EX-4 exactly, the collision suffix, and the explicit stamp, all using the shim and never `--live`.

**Quality**
- `ruff check` and `ruff format --check` are clean on `lab` and `tests`.
- No new TODOs, no secrets, no new dependency.
- I ran `pytest tests/lab_fixes tests/test_runner.py tests/orchestrator tests/fde_kit/test_sandbox_external.py tests/fde_kit/test_eval_8_examples.py`: **162 passed**, 0 skipped. This includes EVAL-1 (with real SIGINT and SIGTERM), EVAL-4 and EVAL-6.

## ⚠️ Deviations to arbitrate

1. **An interrupt while waiting on an Owner-lane task reports that task as in-flight, which contradicts BHV-1b.**
   - `lab/engine/orchestrate.py:796`: `_await_token` returns `interrupted`, and `run_owner_task` passes it up as `"interrupted"`.
   - The main loop then adds the task to `inflight` (`orchestrate.py:1432`), so `run_interrupted` lists it.
   - The spec says "Interrupt while waiting at a checkpoint or an Owner-lane task: same as BHV-1, **with no in-flight task**". The glossary also defines in-flight as a task whose agent turn or judging has started, and a pure wait is neither.
   - State is still correct (the task ends up `pending`), but the journal is wrong. That matters because iterations 3 and 4 read this journal.
   - EVAL-1 only tests the checkpoint case, so this path is not covered.
   - **Fix options:** a separate outcome for "interrupted while waiting" that is not counted as in-flight, or an Owner amendment to BHV-1b. This goes back to T2.

2. **Minor, quality only, not blocking:** `_on_signal` reaches into the private names `runner._TRACKED` and `runner._killpg` (`orchestrate.py:208-209`) without taking the lock. Under CPython the `list(set)` copy is effectively atomic, so this is a coupling smell rather than a bug. A public `runner.kill_all_now()` would be cleaner.

## Not verified here

- The `Artifacts:` trailers of these 4 commits leave out `work/lab-fixes/tasks.md`, which each commit does stage. This is exactly the INV-3 defect that T3 fixes after CP-1, produced by the pre-T3 engine. Under NG-4 those commits stay as they are, so I am not counting it as a T1–T5 deviation.
- These CP-1 items are for the Owner to check by hand, and I did not run them:
  - a live Ctrl-C on a real run in a scratch instance, including checking that no `claude` process is left;
  - the real Docker case, where the container should be removed along with its client's process group (design risk R-1);
  - `just gate-ci`;
  - `just gate` on a seeded drift in the kit itself;
  - the mandatory engine restart (`self_hosting`).
- Whether design ADR-1 / E-2 is anchored on reference repos beyond what design.md §2 cites.

## Proposed OQs

- **OQ-3:** An interrupt after an Owner-lane task was approved but before its verify/gate finished (`orchestrate.py:797-810`) returns the task to `pending`, after `owner_signed` has already been journaled and the approval token consumed. On restart, should the Owner have to sign again, or should the engine honour the existing `owner_signed`? The spec does not say.

VERDICT: WARN