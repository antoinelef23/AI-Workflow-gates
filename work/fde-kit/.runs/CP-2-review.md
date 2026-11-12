# Review CP-2 — panel of 1 — aggregated verdict: WARN (WARN)

## Panelist 1 — claude-opus-5-5 — lens: full review
VERDICT: WARN

# CP-2 review: fde-kit, go/no-go for the examples migration (T5), full review

**Verdict: WARN. No blockers, and the T5 code is conformant.** Two things keep this from a PASS:
- The T5 commit also contains a file outside its scope.
- Two CP-2 checks needed approval and were not run: the open-PR check, and a real run of the T6 move.

CP-2 is `blocking`, so you decide either way.

## What I checked
- **Commit inspected:** `89d2532`, recovering the reasoning from its message and trailers.
- **Golden suite:** `uv run pytest -q tests/golden` gives 3 passed. This is the task's `verify`.
- **Test collection:** `pytest --collect-only` from the kit root collects 1307 tests, all under `tests/`. Nothing outside `tests/` is collected, so the `done_when` holds.
- **Lint and lockfile:**
  - `ruff check` and `ruff format --check` are clean on both T5 files.
  - `uv lock --check` is green, and `uv.lock` is unchanged.
- **Plan-lint:** `orchestrate.py work/fde-kit --validate` raises no errors.
- **Kit tests after the move:** I ran every kit test directory that stays put (`tests/fde_kit`, `tests/orchestrator`, `tests/sdlc_rework`, `tests/golden`, `tests/test_runner.py`).
  - **181 passed**, 50 of them evals. The kit's `just evals` keeps running real evals after the demos leave; pytest's rc 5 for "no tests" can't happen.
- **Untouched paths:** no changes between `2a04e35` and `89d2532` to `src/`, the demo tests, the 3 demo triplets, `docs/`, `.claude/`, `CLAUDE.md` or `uv.lock`.

## ✅ Conformant
- **Traceability:**
  - The subject carries `[INV-9]` and the `Spec-IDs: INV-9` trailer.
  - The auto `Why:` (title + `done_when`) is the form `docs/reference/commit-format.md` allows for `[auto]` commits.
  - INV-9 appears in the diff: `pyproject.toml:22` and `tests/golden/test_oracle_integrity.py:21-29`.
- **Design conformance (ADR-9):**
  - `testpaths = ["tests"]` (`pyproject.toml:22`) means the kit never collects `examples/*/tests`.
  - The golden lookup tries `examples/devis/src/devis/calc.py` first, which is ADR-9's target path. It falls back to the legacy `src/devis/calc.py` (`test_oracle_integrity.py:24-29`).
  - That legacy branch is marked TRANSITIONAL and is due for removal by T9, as the plan records in O-4.
- **Scope:** the code is exactly the two changes the prompt asks for. Nothing was moved and no dependency changed.
- **Hand-written code:** none (`Run: auto`).
- **Quality:** ruff is clean, with no TODOs and no secrets.
- **CP-2 preconditions:**
  - **Working tree:** clean (`git status --porcelain` is empty).
  - **Demo runs:** none of devis-pose, export-devis or salle-booking has a `.runs/` or `.approvals/` folder, so no run is in progress.
  - **Ignored files:** the move list holds no gitignored `assets/` folder that `git mv` would leave behind.
  - **Branches:** only the session branch and `main` exist locally, and `origin/main` has no commit touching the paths that move.
- **The T6 move list matches the tree:**
  - All 14 sources exist (`src/{devis,booking}`, 7 test entries, 3 triplets, 2 docs) and `examples/` doesn't exist yet.
  - No kit code or test hard-codes a path that moves. `justfile`, `lab/`, `.githooks/` and the kit tests are clean; the only mentions are in docstrings and comments, or in temporary test sandboxes.
  - The `evals` recipe uses plain `pytest -m eval`, so `testpaths` covers it.

## ⚠️ Deviations for the Owner
1. **The T5 commit includes a file outside `files_touched`.** `89d2532` also contains `work/fde-kit/.runs/CP-1-review.md` (+76/−36): the regenerated CP-1 review.
   - The cause is engine behavior: `scoped_commit` stages the whole feature directory (`lab/engine/orchestrate.py:378-380`). That file has been tracked since `7b32145`, so the `.runs/` ignore rule doesn't apply to it.
   - The content is harmless, but the second-pass CP-1 review now sits in history under a T5 subject with `Spec-IDs: INV-9`.
   - Options: accept it, or stop tracking `.runs/*-review.md` (a separate engine task, not T5).
2. **Not checked: open PRs on the remote.** `gh pr list` needed approval. I could only check local branches and `origin/main`. Please confirm there's no open PR on the 3 demo features.
3. **Not checked: an actual run of the T6 move.** Copying the repo to a scratch folder to run the `git mv` list and the kit evals needed approval. My green verdict rests on:
   - the 181-test run of the directories that stay;
   - the absence of hard-coded paths;
   - the golden lookup's first candidate matching T6's destination exactly.

   T6's own gate (kit `just evals` green, and `STATUS: blocked` if not) is the backstop.

## Minor notes, not deviations
- **`test_oracle_integrity.py:28`:** `next(...)` has no default. If neither candidate exists, collection fails with a bare `StopIteration` instead of a clear message. It fails closed; worth a clearer error when T9 removes the legacy branch.
- **After T6, `pythonpath = ["src"]` points at nothing in the kit `pyproject.toml`.** This is harmless, and `tests/fde_kit/test_kit_root.py:233` asserts it. T9 should decide whether to keep it.
- **After T6, `brand_guard` will scan the moved triplets.** Its exclusion is `work/` at the start of a path (`lab/engine/brand_guard.py:59`), and `examples/devis/work/…` doesn't match. ADR-9 wants exactly this. It's safe today because the denylist is empty (noted at CP-1), but a non-empty denylist would make T6's pre-commit fail on the demo triplets.
- **`.gitignore` is still `work/**/assets/` until ADR-9's `**/work/**/assets/` change.** No `assets/` folder exists in the move list, so nothing is exposed for now.

## ❌ Blockers
None.

## Recommendation
**Go for T6**, once the Owner confirms deviation #2 (no open PR on devis-pose, export-devis or salle-booking) and accepts or defers #1.

VERDICT: WARN