# Review CP-3 — panel of 1 — aggregated verdict: BLOCK (BLOCK)

## Panelist 1 — claude-opus-5-5 — lens: full review
VERDICT: BLOCK

# CP-3 review: fde-kit migration audit (T6–T10), full review

**This is a BLOCK.** The T9 commit `e8da4a2` turns `just gate-ci` red. That commit removed `pythonpath` from the kit `pyproject.toml`. The test that still requires it, `tests/fde_kit/test_kit_root.py:233`, was fixed only in the working tree and never committed. `gate-ci` is both T9's `done_when` and a CP-3 review item, and the T9 commit fails it.

Two limits on this review:
- Partway through, every Bash call started requiring approval, including plain `git status`. So I could not run `just gate-ci`, `uv run lab run … --dry-run`, `uv run lab validate`, or `git show -M` on the original move commit. Everything after that point comes from reading files.
- The blocker below is established by reading the code, not by running it.

## ❌ Blockers

1. **The T9 commit fails `gate-ci` (`just test` is red).**
   - At `e8da4a2`, `pyproject.toml:21-25` no longer has `pythonpath`. That removal was intended (O-4).
   - But the committed `tests/fde_kit/test_kit_root.py:233` still asserts `p["tool"]["pytest"]["ini_options"]["pythonpath"] == ["src"]`. On the committed tree that raises a `KeyError`.
   - The module has no `eval` marker (`test_kit_root.py:1-20`). So `just evals` stays green, which is all the run log records ("evals green"), while `just test` fails. `just test` is a dependency of `gate-ci` (`justfile:121`).
   - The fix exists only as an uncommitted change (`git status`: ` M tests/fde_kit/test_kit_root.py`).
   - That file is outside T9's `files_touched` (`tasks.md:436`), so the scoped commit left it out. This is also a scope gap in the plan: T9 could not finish its cleanup within its declared files.
   - The working tree is therefore not clean going into T11, which deletes `.claude/`. The orphaned change could be swept into an unrelated commit.
   - **To fix:** `lab/engine/reject.sh CP-3 work/fde-kit "T9: test_kit_root.py:233 asserts the removed pythonpath — gate-ci red at e8da4a2; add the file to files_touched and commit the fix" T9`. Amend T9's `files_touched` in a separate plan-delta commit, as was done in `e86d8c4`.

## ⚠️ Deviations for the Owner

1. **The commits the CP-3 audit points at are empty.**
   - The replay commits `74868ac` (T6), `d7b434a` (T7), `e90bc5f` (T8) and `0b09785` (T10) each change only one or two lines of run log in `work/fde-kit/tasks.md`.
   - Their `Artifacts:` trailers are wrong. This is the same pattern as deviation 2 in the CP-2 report (`c864c14`).
   - The real migration is in the first-run commits: T6 `90fb9f9` + `c2aebe2`, T7 `192203b` (committed by hand), T8 `6f3948d`, T10 `a44e003`.
   - Running `git show -M --stat` on the "T6 commit" (`tasks.md:467`) would compare an empty commit. The purity re-read has to target `90fb9f9` **and** `c2aebe2`. That T6 produced two commits is itself worth checking: the second must also be rename-only.
   - I could not run that check. **The 100%-similarity audit (ADR-9 / design §8) is still to be done by a human.**
2. **T7 was committed by hand (`192203b`).**
   - The plan delta `e86d8c4` and the CP-2 report explain the context (the sandbox refused `just`).
   - I could not read that commit's `Why:` to confirm it justifies the hand-written lines (checklist item 4). Check this during the audit.
3. **Rollout checks not executed:**
   - `lab run work/devis-pose --project examples/devis --dry-run`
   - `lab run work/salle-booking --project examples/booking --dry-run`
   - `lab validate` on the three demo triplets
   - `uv lock --check` inside each example

   None of these have been run by me. They must be green before signing.
4. **The journal is inconsistent.** `work/fde-kit/.runs/journal.jsonl:1` contains a `run_end` event (14:04:09) that marks every node `done`, including CP-3, CP-4 and CP-5. Meanwhile `state.json:14` has CP-3 as `pending`. `just report` and the trajectory guard read this file, so that line will skew their output. It probably comes from a dry-run or an earlier replay.
5. **The two examples name their projects inconsistently.** devis is `devis-lab` (`examples/devis/pyproject.toml:2`) and booking is `booking` (`examples/booking/pyproject.toml:2`). This is harmless, but the T8 prompt says "same as T7".

## ✅ Conformant

- **T9 content follows ADR-9:**
  - `examples-gate` (`justfile:111-118`) runs `uv sync --locked` + `just evals` per example, stops at the first failure (`set -euo pipefail`, subshell), and is wired into `gate-ci` only (`justfile:106,121`).
  - `.gitignore:34` uses `**/work/**/assets/`.
  - The brand-guard scope (`lab/engine/brand_guard.py:8-14,61-62`) excludes kit-root `work/` and every `**/assets/**`, and scans `examples/**`.
  - The legacy `src/devis` golden lookup is gone (`tests/golden/test_oracle_integrity.py:21-23`). This also resolves the bare `StopIteration` noted at CP-2.
- **EVAL-8** (`tests/fde_kit/test_eval_8_examples.py`) covers every point in the T9 prompt:
  - the wheel contains only `lab/` and includes `plugin.json` and `registry.toml`, with no devis or booking modules (`:49-72`)
  - tracked-ness is checked with `git ls-files` (`:30-34,75-109`)
  - kit `work/` holds only `sdlc-rework` and `fde-kit` (`:112-118`)
  - each example's pin equals the kit version (INV-7, `:121-130`)
  - `gate-ci` depends on `examples-gate` and `gate` does not (`:133-141`)
  - brand scope and gitignore (`:144-156`)
  - the transitional bits are gone (`:159-165`)

  It carries the `eval` marker, and the test names follow `test_eval_8_*`.
- **T7 and T8 instances:**
  - each has its own `pyproject.toml` with `pythonpath = ["src"]` and the `eval` marker
  - each has a `uv.lock` whose root package matches its project
  - `.lab/lab.toml` pins `kit_version = "0.1.0"` with `profile = "squad"`, matching OQ-11 and the kit `pyproject.toml:3`
  - the justfile has the `evals` / `evals-collect` recipes generated by `lab init`
- **T10:** `tests/fde_kit/test_doc_pointers.py` enforces the `examples/` prefix. Its exemption for `--project examples/<x>` lines is explicitly allowed by the prompt (`tasks.md:419`). The test is not an eval, as required.
- **Traceability:**
  - All five commits carry `[INV-9]` / `[INV-7, INV-9]` / `[INV-9, EVAL-8]` in the subject and a matching `Spec-IDs:` trailer, all valid IDs.
  - The `Why:` lines use the auto form allowed for `Run: auto`.
  - Nothing in T9's committed diff falls outside the spec.

## Before approving, after the T9 fix

1. Re-read `90fb9f9` and `c2aebe2` with `git show -M --stat`: renames only, 100% similarity.
2. Run `just gate-ci` on a **clean** tree.
3. Run the two `lab run … --dry-run` checks and `lab validate` on the three demo triplets.
4. Do the mandatory orchestrator restart (`tasks.md:468`), then read the review it re-generates.

VERDICT: BLOCK