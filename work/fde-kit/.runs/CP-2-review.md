# Review CP-2 — panel of 1 — aggregated verdict: WARN (WARN)

## Panelist 1 — claude-opus-5-5 — lens: full review
VERDICT: WARN

# CP-2 review: fde-kit, go/no-go for the examples migration (T5), full review

**The T5 code is conformant and green, and I found no blockers. But the go/no-go question at this checkpoint no longer applies: the migration already happened.** `src/` is gone, `examples/{devis,booking}` exist, and T6, T7, T8 and T10 are committed (`90fb9f9`/`c2aebe2`, `192203b`, `6f3948d`, `a44e003`). Even so, `.runs/state.json` still lists T6, T7, T8, T9 and T10 as `pending`. If you approve CP-2 as it stands, the live engine (pid 899) will send a "pure move" T6 to a tree where none of its sources exist.

## What I checked
- **Commits:** the replay commit `b73f6ee` and the original T5 code commit `89d2532`, including their messages and trailers.
- **Drift:** `git diff 89d2532 HEAD -- pyproject.toml tests/golden/` is empty, so the T5 code is unchanged since it was first committed.
- **T5 verify:** `uv run pytest -q tests/golden` gives **3 passed**. The lookup now resolves to its first candidate, `examples/devis/src/devis/calc.py`, so it exercises the ADR-9 target and not the legacy path.
- **`done_when`:** `pytest --collect-only` from the kit root collects 182 tests, and none of them are outside `tests/`.
- **Lint and lockfile:**
  - `ruff check` and `ruff format --check` are clean on both T5 files.
  - `uv lock --check` is green.
- **Plan-lint:** `orchestrate.py work/fde-kit --validate` reports no errors.
- **CP-2 preconditions:**
  - **Working tree:** clean (`git status --porcelain` is empty).
  - **Demo runs:** no `.runs/` or `.approvals/` folder exists under any demo triplet.
  - **Branches:** the only other branch, `origin/ccr-d4884d69-odjnuk`, is the previous session's and is already an ancestor of HEAD, so nothing is in flight.

## ✅ Conformant
- **INV-9 / ADR-9:**
  - `testpaths = ["tests"]` is set at `pyproject.toml:22`.
  - The golden reference lookup is at `tests/golden/test_oracle_integrity.py:21-29`. It tries the ADR-9 target first, then the legacy path. The legacy path is marked TRANSITIONAL and is due for removal by T9 (plan O-4).
- **Scope:** `89d2532` contains exactly the two changes the prompt asks for. Nothing was moved and `uv.lock` is unchanged.
- **Traceability:** both T5 commits have `[INV-9]` in the subject and a `Spec-IDs: INV-9` trailer. Their `Why:` uses the auto form (title + `done_when`), which `docs/reference/commit-format.md` allows for `[auto]` commits.
- **Hand-written code:** none (`Run: auto`).
- **Quality:** no TODOs and no secrets.
- **The T6 destination is already in place:**
  - Every path in T6's `verify` `ls` exists.
  - No files are still tracked at the old locations (`git ls-files` returns 0).

## ⚠️ Deviations for the Owner
1. **Approving CP-2 will replay the migration, which is already done.** This is the main issue. The CP-1 replay review flagged it as deviation 1, and CP-1 was approved anyway at 14:40.
   - After CP-2, the engine will send T6 out with the prompt "Move, without changing a single byte… `src/devis/` → …" (`work/fde-kit/tasks.md:343-355`). None of those sources exist.
   - The best case is an empty "done" commit, as happened for T1–T5. The worst case is an agent improvising on a tree that doesn't match its prompt.
   - T7 would then be re-run. It was committed by hand (`192203b`) because the agent lacked tool rights, and per `e86d8c4` its verify is left to the orchestrator.
   - **Recommendation:** stop pid 899 before you sign. Then mark T6, T7, T8, T10 and CP-2 as `done` in `.runs/state.json` (a human decision on an engine file) and restart, so the run resumes at T9. The other option is to approve and supervise each re-dispatch. Either way, don't sign CP-2 on the live run without deciding this.
2. **The replay commit `b73f6ee` carries a false `Artifacts:` trailer.**
   - It lists `pyproject.toml` and `tests/golden/test_oracle_integrity.py`, but its diff is two lines of run log in `work/fde-kit/tasks.md:630-631`.
   - `git log --grep 'T5 Move-readiness'` now returns two commits, and the real code is in `89d2532`. This is the same pattern as the T1–T4 replays (`15f628c`…`2bad205`).
   - A note commit or a `git notes` entry pointing to `89d2532` would keep "the why lives in git" accurate.
3. **`work/fde-kit/.runs/CP-2-review.md` is still the first-run report.** It is tracked and reviews `89d2532` against a tree that hadn't been moved yet, and its "examples/ doesn't exist yet" statement is now false. This report replaces it. As in the earlier run, `scoped_commit` (`lab/engine/orchestrate.py:378-380`) will commit it under the next task's subject.

## Minor notes, not deviations
- **`tests/golden/test_oracle_integrity.py:28`:** `next(...)` has no default. If neither path exists, it fails with a bare `StopIteration`. It fails closed; worth a clearer message when T9 removes the legacy branch.
- **The legacy `src/devis/calc.py` branch is now dead code.** T9 is still pending to remove it, and nothing else needs doing until then.
- **`brand_guard` now scans `examples/*/work/**`** because its exclusion only matches `work/` at the start of a path. This is what ADR-9 intends. It is harmless while the denylist is empty, but a non-empty denylist would flag the demo triplets.

## ❌ Blockers
None. T5 is correct, and sending it back would not fix deviation 1, which is a question of the engine's run state, not of T5's code.

**Recommendation:** go on T5's content. On the checkpoint itself, settle deviation 1 (fix `state.json` or supervise the replay) before approving, since the migration it was meant to gate has already happened.

VERDICT: WARN