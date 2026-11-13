# Review CP-1 — panel of 1 — aggregated verdict: WARN (WARN)

## Panelist 1 — claude-opus-5-5 — lens: full review
VERDICT: WARN

# CP-1 review, third pass: lab-fixes (T1, T2, T4, T5), full review

**Verdict: WARN.** I found one minor deviation, and the Owner needs to decide on it. T1, T4 and T5 match the spec and design. T2 fixes all three points from the CP-1 rejection, and the checks I ran pass:

- **Tests:** 164 passed (`tests/lab_fixes`, `tests/orchestrator`, `tests/test_runner.py`, `tests/fde_kit/test_sandbox_external.py`, `tests/fde_kit/test_eval_8_examples.py`).
- **Lint:** `ruff check` and `ruff format --check` are clean.

The deviation: in one very short window, an Owner-lane task is listed as in-flight before its checks have started. That is the same kind of problem as the queued-task gap the Owner already moved to T3. The only code commit since the second pass (`9e355a1`) is none: only `tasks.md` changed, in `f61a47b`.

## ✅ Conformant

**Traceability**
- The commits `52015e8` (T1), `4052e13` (T4), `211b04a` (T5) and `787be0e` (T2 rework) all use the canonical subject `[IDs]`, have a `Why:` body, and carry the `Spec-IDs:` and `Run: auto` trailers. Their IDs match each task's `implements` list. `787be0e` adds BHV-1c, as plan delta (b) requires.
- Every BHV/INV of the four tasks is in the diff:
  - **BHV-1 / INV-1:** `orchestrate.py:889-966` checks the stop flag before the agent turn, after it, after verify, after the eval gate and just before `scoped_commit`.
  - **BHV-1a:** `orchestrate.py:209` exits at once on a second signal.
  - **BHV-1b:** `orchestrate.py:795-796` returns `interrupted_waiting`; `orchestrate.py:1094-1100` and `:1156` return from the checkpoint and token waits.
  - **BHV-1c:** `orchestrate.py:806-811`. The token is already consumed at `:1191`, so restarting requires a new signature.
  - **BHV-4:** `justfile:107`.
  - **BHV-6 / INV-5:** `eval_models.py:334-342` and `:484`.
  - **BHV-7:** the `eval-models` comment in the `justfile`.

**Design conformance**
- **ADR-1:** `run_tracked` uses `Popen(start_new_session=True)` and a registry protected by a lock. On timeout it kills the whole process group and re-raises, so callers keep their timeout messages. `terminate_all` waits on the group, not just the leader, before SIGKILL. Both runners use it, and `docker run --rm` is kept.
- **ADR-2:** the signal handler only appends to `_SIGNALS_SEEN` and starts a helper thread, so it takes no lock in handler context (E-1). On interrupt:
  - Queued futures are cancelled at `:1427` (E-3).
  - State is written atomically through `save()` (I-1).
  - One `run_interrupted` event is journaled with the signal name, matching design §5.
  - The process prints how to resume and returns 130.
  - Plan delta (c) is applied: the handler calls the public `runner.kill_all_now()` and no longer touches the private `_TRACKED` / `_killpg`.
- **ADR-5:** `gate: lint-check …`, and the `lint` comment calls it the explicit fixer.
- **ADR-6 (stamps):** the default stamp is `<date>-<layer>`, with `-2`, `-3`… added when the `.md` already exists. An explicit `--stamp` is used as given, and the date can be injected through `_today()`.

**Scope**
- Each commit touches only its task's `files_touched`, including the OQ-1 and OQ-2 deltas. `runner.py` is in T2's diff only for `kill_all_now`, which delta (c) allows. Nothing outside the spec, and nothing from T3 or T6, was pulled in.

**EVAL-1 covers the full spec 0.3.0 row**
- EX-1 under both SIGINT and SIGTERM.
- A second signal exits within 4 s, well under the 5 s grace.
- A blocking checkpoint is interrupted with `inflight == []`.
- An Owner-lane task interrupted while waiting has `inflight == []` (BHV-1b).
- A task interrupted after its signature, during verify, ends with `inflight == ["T1"]`, and restarting requires a new signature before the commit (BHV-1c).

**EVAL-4 and EVAL-6** match the spec rows, including EX-4 file names exact.

**Quality:** no secrets, no orphan TODOs, and dry runs install no signal handler (`:1376-1377`).

## ⚠️ Deviation to arbitrate (minor)

1. **`lab/engine/orchestrate.py:806-807`: an Owner-lane task can be listed in-flight before its checks have started.**
   - The spec glossary defines an in-flight task as one whose agent turn or judging has started.
   - If the signal arrives after the signature is consumed (`:1191`) and `owner_signed` is journaled (`:800`), but before `_run_verify` starts, the task returns `"interrupted"` and is listed in `run_interrupted.inflight`.
   - The state is still correct: the task is `pending` and the Owner must sign again (BHV-1c). Only the journal entry is wrong.
   - The window is only a few instructions wide, and EVAL-1 cannot reach it.
   - It is the same kind of gap as the queued-task one the Owner deferred to T3 in `f61a47b`.
   - **Suggestion:** extend T3's existing delta to cover it. Return the same "not started" outcome at `:806`, and keep `"interrupted"` for `:810`, which runs after verify and the eval gate.

## Already decided (not findings)

- **`orchestrate.py:848`, the never-started queued task:** the Owner approved deferring this to T3 (`f61a47b`, T3 plan delta plus `test_eval_1_interrupt_queue.py`). It is conformant here.
- **T1–T5 `Artifacts:` trailers omit `tasks.md`:** this is the INV-3 defect that T3 fixes. These commits were written by the engine before T3, and NG-4 says history is never rewritten.

## Not verified here

- `just gate` on a seeded drift, and `just gate-ci` green: I was not allowed to run `just` here. EVAL-4 covers the seeded-drift case on a temporary copy.
- The live Ctrl-C on a real run with no stray `claude` process, and the mandatory engine restart: both are human checkpoint actions. `f61a47b` records that the live Ctrl-C reproduced EX-1.
- `check-brand` and `check-lock`: I did not run them.
- Interrupt latency: verify and the eval gate are not agent processes, so `terminate_all` does not stop them. An interrupt during the judging stage waits for the running verify or eval to finish. The spec only requires agent processes to be terminated, so this is information, not a deviation.

## Proposed OQs

None. BHV-1c settles what happens to a task interrupted after its signature; the item above only concerns how it is journaled.

VERDICT: WARN