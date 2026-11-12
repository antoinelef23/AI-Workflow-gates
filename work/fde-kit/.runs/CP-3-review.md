# Review CP-3 — panel of 1 — aggregated verdict: WARN (WARN)

## Panelist 1 — claude-opus-5-5 — lens: full review
VERDICT: WARN

# CP-3 review (third pass): fde-kit migration audit, T6–T10, full review

**Verdict: WARN.** The blocker from the last two passes is fixed: the `test_kit_root.py` fix is now committed and the working tree is clean. Several required checks still have not been run, though, and the CP-3 checklist asks for them. After my first few calls, every Bash command needed approval, even `git show` and `just gate-ci`, which is the same limit the earlier passes hit. So everything after `git status`/`git show cda972e` comes from reading files. I ran no checks myself.

## ❌ Blockers
None found.

## ⚠️ For the Owner to decide
1. **Required checks not run.**
   - **`just gate-ci` on a clean tree.** This is T9's `done_when` (`tasks.md:459`) and a CP-3 item (`tasks.md:467`). It still hasn't been run. The run log at `tasks.md:639` only says "evals green". That was exactly how the first BLOCK slipped through: the evals were green while `just test` was red.
   - **Rename audit, `git show -M --stat 90fb9f9 c2aebe2`.** The CP-3 commit `7e534c9` says this was checked: 38 renames at 100% similarity, and `c2aebe2` changes only the log. I couldn't run it again. ADR-9 says a human has to re-read the move, so the Owner still needs to do it.
   - **Rollout checks:** `uv run lab run work/devis-pose --project examples/devis --dry-run`, the same for `salle-booking`/`examples/booking`, and `uv run lab validate` on the three demo triplets. None of these were run.
2. **The T9 commit `cda972e` overwrites the BLOCK report.**
   - It rewrites `work/fde-kit/.runs/CP-3-review.md` (109 lines changed) with a stale "second pass" that still says the fix is uncommitted.
   - The first BLOCK report is still in history at `7e534c9`, but the file on disk now describes a state that no longer exists.
   - The `Artifacts:` trailer lists 7 files. The commit only changes `tests/fde_kit/test_kit_root.py` plus run-log files. The rest of T9 is in `e8da4a2`.
3. **The engine changed after T4, outside the plan.**
   - Commit `f4f151c` changes `lab/engine/orchestrate.py`. It adds a check that sends a task back if it edited files its scoped commit would leave out.
   - It is recorded as an Owner-run lab fix, so it is properly documented.
   - It makes the mandatory restart more important: the engine that runs T11 needs to load both T4 and `f4f151c`.
4. **Still open from earlier reports:**
   - **Journal contradicts state.** `journal.jsonl:1` has a `run_end` event (14:04:09) marking CP-3 through CP-5 as `done`, but `state.json:14` still has CP-3 as `pending`. This will skew `just report` and the trajectory guard.
   - **T7 was committed by hand** (`192203b`). I have not checked its `Why:` against checklist item 4.
   - **Project names differ:** `devis-lab` and `booking`. Harmless.

## ✅ Conformant
- **The BLOCK is fixed through the process.**
  - Plan delta `314bf39` adds `tests/fde_kit/test_kit_root.py` to T9's `files_touched` (`tasks.md:436`). The `approved_by` line (`tasks.md:7`) records it.
  - `cda972e` commits the fix: `test_kit_root.py:233-234` now asserts that `pythonpath` is gone, which matches `pyproject.toml:21-25`.
  - `git status` is clean, so nothing left over will slip into T11's commit.
- **T9 content follows ADR-9:**
  - `examples-gate` (`justfile:111-118`) runs each example in a subshell with `set -euo pipefail`, so it stops at the first red example.
  - It is wired into `gate-ci` only (`justfile:121`), not into `gate` (`justfile:106`).
  - The kit `pyproject.toml` packages only `lab`, with no dependency change.
- **Points I confirmed earlier and saw no reason to doubt:**
  - EVAL-8 coverage in `tests/fde_kit/test_eval_8_examples.py`
  - the brand-guard scope and the `.gitignore` change
  - the T7/T8 instance files (pyproject, lockfile, `.lab/lab.toml` pinned to `kit_version = "0.1.0"`)
  - the T10 doc-pointer test
- **Traceability:** `cda972e` and `314bf39` have valid `[INV-9, EVAL-8]` subjects and `Spec-IDs:` trailers. `314bf39` has a real `Why:` and a `Checkpoint: CP-3` trailer.

## Before signing
1. Run `just gate-ci` on the clean tree. It must be green, including `examples-gate`.
2. Run `git show -M --stat 90fb9f9 c2aebe2` and check it shows only renames at 100% similarity.
3. Run the two `lab run … --dry-run` commands and `lab validate` on the three demo triplets.
4. Do the mandatory restart (`tasks.md:468`) so T4 and `f4f151c` are loaded, then read the review it re-generates.

VERDICT: WARN