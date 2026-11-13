# Review CP-1 — panel of 1 — aggregated verdict: WARN (WARN)

## Panelist 1 — claude-opus-5-5 — lens: full review
VERDICT: WARN

Tests and lint are green. I'm finishing the report now, and I found one small issue in the new T2 code.

# CP-1 review, second pass: lab-fixes (T1, T2, T4, T5), full review

**Verdict: WARN.** The T2 rework fixes all three points from the CP-1 rejection. The checks I ran pass: 164 tests, ruff lint and the format check. I found one small new problem: a task that never started can still be listed as in-flight in `run_interrupted`. It only happens if a wave has more tasks than run in parallel, and only in a timing race. T1, T4 and T5 have not changed since the first CP-1 pass (`f5c11d9`), and its findings on them still hold.

## ✅ Conformant

**What the T2 rework (`787be0e`) fixed**
- **BHV-1b (Owner-lane wait):** if the run is interrupted while an Owner-lane task waits for its signature, `run_owner_task` now returns a separate result, `interrupted_waiting` (`lab/engine/orchestrate.py:795-796`). The main loop skips it instead of adding it to `inflight` (`orchestrate.py:1435-1436`). The task stays `pending`.
- **BHV-1c (interrupt after signing):** an interrupt after the Owner signs is caught in two places: before verify (`orchestrate.py:806`) and after verify plus the eval gate (`:810`). Both happen before `scoped_commit`, so nothing is committed (INV-1). The signature is used up when it is accepted: the approval file is renamed to `.handled-*` (`orchestrate.py:1188-1190`). So after a restart the engine waits for a new signature.
- **Public kill function:** `runner.kill_all_now()` (`lab/engine/runner.py:108-115`) copies the list of running processes under `_TRACKED_LOCK`, then sends SIGKILL. The signal handler calls it (`orchestrate.py:208`) and no longer touches runner's private names.
- **EVAL-1 now covers both Owner-lane cases:**
  - Interrupt while waiting: rc 130, no new commit, task `pending`, and `inflight == []` (`tests/lab_fixes/test_eval_1_interrupt.py:243-261`).
  - Interrupt after signing: no commit, task `pending`, `inflight == ["T1"]`. After a restart the engine waits again and commits only after a new `approve` (`test_eval_1_interrupt.py:264-303`).

**Scope**
- In `787be0e`, the only change to `runner.py` is adding `kill_all_now`, which the plan delta allows. Everything else is in `orchestrate.py` and the EVAL-1 test.

**Traceability**
- `787be0e` uses the canonical subject. Its tags and `Spec-IDs` (BHV-1, 1a, 1b, 1c, INV-1, EVAL-1) match T2's `implements` list.
- Its `Why:` body records why the task was reworked: the CP-1 rejection.
- The spec 0.3.0 amendment (`55ca955`) and its coherence pass (`ac26b3a`) are separate commits. The `version :` pointers in design.md and tasks.md say 0.3.0.

**Rest of BHV-1 still holds:** stop flag set from a helper thread (E-1), queued work cancelled and the pool shut down with `cancel_futures` (E-3), state written atomically, one `run_interrupted` event, resume instructions printed, rc 130, and an immediate `os._exit(130)` on a second signal (BHV-1a).

**Quality**
- `ruff check` and `ruff format --check` pass on `lab` and `tests`.
- `pytest tests/lab_fixes tests/test_runner.py tests/orchestrator tests/fde_kit/test_sandbox_external.py tests/fde_kit/test_eval_8_examples.py`: **164 passed**. This includes EVAL-1 (6 cases, with real signals), EVAL-4 and EVAL-6.
- No new TODOs, no secrets, no new dependency.

## ⚠️ Deviations to arbitrate

1. **A task that never started can be listed as in-flight.**
   - **Where:** `orchestrate.py:848` (a queued task picked up after the interrupt) and `orchestrate.py:889` (just before attempt 1's agent turn) both return `"interrupted"`. The main loop then adds the task to `inflight` (`orchestrate.py:1432-1434`).
   - **Why it's wrong:** the glossary defines an in-flight task as one whose agent turn or judging has started. BHV-1 says `run_interrupted` lists the in-flight tasks. The CP-1 rejection was about exactly this: only agent turns and judging count as in-flight.
   - **How it happens:** when a wave has more tasks than `MAX_PARALLEL` (3), a worker that has just returned `interrupted` immediately takes the next queued task. That happens before the main loop cancels the queue, which it does only on its next 0.2 s check (`:1428-1429`). The queued task then reaches `:848` and is listed even though its agent never ran.
   - **Impact:** `state.json` is still correct, because the task is `pending` either way. Only the journal is wrong, and iterations 3–4 read that journal.
   - **Tests:** EVAL-1 doesn't cover this because its wave has 2 tasks, fewer than `MAX_PARALLEL`.
   - **Fix:** return `interrupted_waiting` (or a similar "not started" result) at `:848`, and at `:889` when `attempt == 1`. This is small and should go back to T2. The Owner can also accept it as is.

## Not verified here

- **Known issue from before T3:** the `Artifacts:` trailers of `52015e8`, `089930d`, `787be0e`, `4052e13` and `211b04a` leave out `work/lab-fixes/tasks.md`, even though each commit includes it. This is the INV-3 defect T3 is planned to fix, produced by the engine as it was before T3. Under NG-4 those commits stay as they are, so I don't count it against these tasks.
- **CP-1 checks the Owner does by hand; I did not run them:**
  - a live Ctrl-C on a real run in a scratch instance, checking that no `claude` process is left;
  - the real Docker case: the container should go away with its client's process group (design risk R-1);
  - `just gate` on a seeded drift in the kit itself;
  - `just gate-ci`;
  - the mandatory engine restart (`self_hosting`).
- **Trajectory guard:** after a BHV-1c restart, the journal holds two `owner_signed` events for one `task_done`. EVAL-1 checks the restart succeeds, but I did not run `just check-trajectory` on that journal.

VERDICT: WARN