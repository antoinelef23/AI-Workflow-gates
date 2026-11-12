# Review CP-3 — panel of 1 — aggregated verdict: BLOCK (BLOCK)

## Panelist 1 — claude-opus-5-5 — lens: full review
VERDICT: BLOCK

# CP-3 review (second pass): fde-kit migration audit, T6–T10, full review

**This is still a BLOCK.** The Owner rejected CP-3 back to T9 (`.approvals/CP-3.rejected`, 15:28:59). That rejection has not been processed yet: T9 was not re-run and nothing was committed after it. The tree being reviewed is the same as at the first BLOCK, plus the plan delta.

**Limits on this review:** after the first few calls, every Bash command needed approval, including `git -C … show`. So I could not run `just gate-ci`, `git show -M` on `90fb9f9`/`c2aebe2`, the `lab run … --dry-run` checks, `lab validate`, or `uv lock --check`. Everything below comes from git output gathered before that point, plus reading the files.

## ❌ Blockers

1. **The fix for the first BLOCK exists only in the working tree. It is not committed.**
   - At HEAD (`314bf39`), `git status` still shows ` M tests/fde_kit/test_kit_root.py`. `git diff` shows the fix as an uncommitted change:
     - removed: `assert p["tool"]["pytest"]["ini_options"]["pythonpath"] == ["src"]`
     - added: `assert "pythonpath" not in …` (`tests/fde_kit/test_kit_root.py:233-234`)
   - The kit `pyproject.toml:21-25` no longer has `pythonpath`. So the committed `test_kit_root.py` raises a `KeyError`, and `just test`, and with it `gate-ci` (`justfile:121`), are red at HEAD. T9's `done_when` (`tasks.md:452`) and the CP-3 review item "`just gate-ci` green" both fail on the committed tree.
   - The plan delta `314bf39` does fix the scope gap: the file is now in T9's `files_touched` (`tasks.md:436`).
   - But the reopened T9 has not run:
     - `journal.jsonl` has no T9 attempt 2; the last event is the CP-3 BLOCK review at 14:48:53.
     - `state.json` still shows `"T9": "done"` and `"CP-3": "pending"`.
     - No commit carries the change.
   - **To unblock:** restart the orchestrator, which is the mandatory CP-3 restart anyway (`tasks.md:468`). It will consume `CP-3.rejected` and reopen T9. With the new scope-leak check (`f4f151c`), T9 can only go `done` if its commit carries `test_kit_root.py`. Then CP-3 is presented again on a clean tree.

## ⚠️ Deviations for the Owner (carried over, still open)

1. **The 100%-similarity audit of the pure move is still not done** (ADR-9 / design §8).
   - The replay commits `74868ac`, `d7b434a`, `e90bc5f` and `0b09785` contain only run-log lines. The real move is in `90fb9f9` and `c2aebe2`.
   - The earlier report (`7e534c9`) records that these were independently checked as 38 renames at R100 plus a log-only commit. I could not re-run that check here, so a human should confirm it with `git show -M --stat 90fb9f9 c2aebe2`.
2. **Rollout checks are still not run by a reviewer:**
   - `uv run lab run work/devis-pose --project examples/devis --dry-run`
   - `uv run lab run work/salle-booking --project examples/booking --dry-run`
   - `lab validate` on the three demo triplets
   - `uv lock --check` in each example
3. **The journal is still inconsistent.** `work/fde-kit/.runs/journal.jsonl:1` is a `run_end` event (14:04:09) that marks every node `done`, including CP-3, CP-4 and CP-5. This contradicts `state.json`, and it will skew `just report` and the trajectory guard.
4. **T7 was committed by hand (`192203b`).** Confirm during the audit that its `Why:` justifies the hand-written lines (checklist item 4). The background is in `e86d8c4`.
5. **The two examples name their projects inconsistently:** `devis-lab` vs `booking`. This is cosmetic.

## ✅ Conformant

- **The plan delta `314bf39` follows the process:**
  - it is a separate `docs` commit with the `Why:`, `Spec-IDs` and `Checkpoint: CP-3` trailers
  - the `approved_by` line records the delta (`tasks.md:7`)
  - the rejection goes back to T9 rather than being fixed by a hand commit
- **The `f4f151c` engine fix** closes the gap that caused the first BLOCK: a task can no longer go green on edits its commit leaves out.
- **The working-tree fix itself is correct.** It inverts the assertion to match O-4 (`test_kit_root.py:233-234`) and touches nothing else.
- **T9 content follows ADR-9:**
  - `examples-gate` (`justfile:111-118`) stops on the first failure (`set -euo pipefail`, subshell per example) and is wired into `gate-ci` only (`justfile:106,121`)
  - `pythonpath` is removed (`pyproject.toml:21-25`)
  - brand scope, `.gitignore` `**/work/**/assets/`, and EVAL-8 coverage are as described in `7e534c9`
- **Traceability:** every T6–T10 commit and the delta carry valid `[INV-9]`, `[INV-7, INV-9]` or `[INV-9, EVAL-8]` tags with a matching `Spec-IDs:` trailer.

## Before approving

1. Restart the orchestrator. It reopens T9, and T9 must commit `test_kit_root.py`.
2. Run `just gate-ci` on a clean tree (`git status` empty).
3. Run `git show -M --stat 90fb9f9 c2aebe2`: renames only, R100.
4. Run the two `--dry-run` pre-flights, `lab validate` on the three demo triplets, and `uv lock --check` in each example.
5. Read the review re-generated after the restart, then approve.

VERDICT: BLOCK