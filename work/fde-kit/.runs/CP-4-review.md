# Review CP-4 — panel of 1 — aggregated verdict: WARN (WARN)

## Panelist 1 — claude-opus-5-5 — lens: full review
VERDICT: WARN

# CP-4 review, third pass: fde-kit, T11 to T13 (full review)

The rework in `ac9aed9` does both things the second rejection asked for: trials now get read access to the agents folder only, and the role path is filled in through `.format()`. One gap is left, and you should settle it before the billed scorecard campaign. Narrowing `--add-dir` does not stop a trial from reading the hidden evals, because its own allowed tools can still read any file. The prompt now also gives the model the kit's absolute path.

**Checks I ran**
- **Tests:** `uv run pytest -q tests/orchestrator tests/sdlc_rework tests/fde_kit` gives **202 passed**.
- **Lint and lockfile:** `ruff check` and `ruff format --check` are clean (80 files), and `uv lock --check` is green.
- **Brand guard:** green, but the denylist is empty, so it checks nothing.
- **spec.md and design.md:** unchanged since `2be6b62`, so no version bump was needed.
- **Trajectory guard:** red with 2 violations plus 1 warning (details under ⚠️ 4).
- **Not run:** `just` recipes were refused by this session's permissions, so I ran each guard's script directly. `examples-gate` and the billed live campaign were not run (the campaign is human-only).

## ✅ Conformant

**T11 (`50f9c61`) and T12 (`a243a5d`):** unchanged since the first pass, and those findings still hold.

**T13 rework (`ac9aed9`), checked against the second reject note (`tasks.md:671`):**
- **Grant narrowed:** `lab/engine/eval_models.py:92` now passes `add_dirs=[_AGENTS]`, which is `<kit code root>/lab/plugin/agents`. It no longer grants the kit root. The comment cites the EVOLUTION.md fairness rule.
- **Brace-safe role path:** the line that baked the path into the template is gone. `{agents}` is now a `.format()` argument in `:174-175` (behavioral and chain) and in `:227-229` (scorecard). A path containing `{` or `}` can no longer crash a trial.
- **One source for the path:** `ROLE_PROMPT` and `kit_options()` both read the same `_AGENTS` value (`:80`), resolved with `kit_root(honor_env=False)` and never `LAB_ROOT`.
- **Tests:** `tests/fde_kit/test_eval_models_argv.py:76-81` covers both the behavioral and chain layers. It checks that there is exactly one `--add-dir`, that it ends with `lab/plugin/agents`, that `evals/` is not under it, that it is not the repo root, and that the prompt still cites the absolute role file. This is what the note asked for.
- **Scope:** only `eval_models.py`, the test file and the `tasks.md` journal changed, all inside `files_touched` (`tasks.md:557`). `orchestrate.py` was not touched by T13. Its diff since `2be6b62` comes from the Owner commits `94f273e` and `2f3fe92`.
- **Traceability:** the subject is tagged `[BHV-2]` and the `Spec-IDs: BHV-2` trailer is present.
- **Quality:** no TODO or FIXME, and no secrets.

**`2f3fe92`** (an Owner engine fix, outside T11 to T13): auto commits now add the rejection reason to their `Why:` line. The commit explains why and comes with `tests/orchestrator/test_commit_why.py`. This deals with item 5 of the second pass, for future commits.

## ⚠️ To arbitrate

1. **Trials can still read the answer keys, now by a path the prompt gives them.** This matters most for `layer=scorecard`.
   - **Why the narrower grant doesn't close it:** `--add-dir` only limits what the file tools can read. The allowed tools at `eval_models.py:58` include `Bash(python3:*)`, `Bash(cat:*)` and `Bash(git:*)`. A command like `python3 -c "print(open('<kit>/evals/golden/x/goldeval/check.sh').read())"` reads any file. The same goes for `git -C <kit> show HEAD:evals/behavioral/cases.py`.
   - **Nothing denies these reads:** `lab/engine/run_settings.json` only denies edits to `.approvals` and `.runs`.
   - **The model now knows where to look:** the prompt contains `<kit>/lab/plugin/agents/…` (`:62`, `:69`), so the evals are at the obvious sibling path, `<kit>/evals/`. Before T13 the prompt did not reveal the kit's location.
   - **Not an implementer error:** T13 did exactly what the second note prescribed. The gap is in that prescription, which came from my second-pass recommendation.
   - **Recommendation:** copy the role file into each trial's temp folder in `setup_fixture`, cite it by a relative path, and drop `--add-dir` entirely. The model then never learns the kit path, and nothing outside its folder needs granting.
   - **If you would rather not rework again:** run only `layer=behavioral` and `layer=chain` live (their graders are less useful to the model mid-trial). Then add a note to the dated scorecards that trials could reach `evals/` through Bash.
   - **A full fix is OS-level sandboxing,** which is out of T13's scope. If you want that, record an ADR.
2. **The scorecard layer's prompt is not tested.** The `.format(…, agents=_AGENTS)` call at `eval_models.py:227-229` is only reached by `run_scorecard`. The shim tests run only the behavioral and chain layers (`test_eval_models_argv.py:88-99`, `test_models.py:521`), and with a temp `LAB_ROOT` there is no golden task, so that layer is skipped. The code looks correct to me, but no test runs it.
3. **The rework's commit metadata is still thin.**
   - `ac9aed9` still has the placeholder `Why:` line (title plus `done_when`), with no mention of the second CP-4 rejection. `2f3fe92` says its fix "takes effect at the next orchestrator restart", so the orchestrator was evidently not restarted before this run.
   - Its `Artifacts:` trailer lists `tests/orchestrator/test_models.py`, which the commit did not change. It appears to copy `files_touched` rather than the files actually edited.
4. **The trajectory guard is still red, and it is a criterion of the final checkpoint.** None of these come from the T13 code:
   - ⛔ T15 is recorded as done with no attempt before it. Its entry predates `94f273e`.
   - ⛔ Commit `192203b9` (T7) touched `progress.md` outside its scope. This has been raised before.
   - ⚠️ New: "T13 took 3 attempts — retry-loop smell". Both retries were Owner rejections caused by reviewer recommendations, not the implementer looping. Note this in the record before the merge checkpoint so the warning isn't misread.
5. **Duplicated paths:** `eval_models.py:84-98` still repeats the paths in `orchestrate.py:198-215`. The reject note ruled this out of scope, so it is only a note.
6. **CP-4's own checks are still yours to run:**
   - The live campaign: behavioral first, then chain. Item 1 bears on how far to trust the results.
   - A real `claude -p` asked to write `.approvals/CP-1` should be denied (EX-5).
   - An interactive `claude --plugin-dir lab/plugin` session should show the hard rules (BHV-2b).
   - Check whether `--settings` still applies under `--bare`.

## ❌ Blockers

None in the code. T11 to T13 meet their `done_when` and both reject notes, and the suites and guards I ran are green apart from the known trajectory violations.

VERDICT: WARN