# Review CP-4 — panel of 1 — aggregated verdict: WARN (WARN)

## Panelist 1 — claude-opus-5-5 — lens: full review
VERDICT: WARN

# CP-4 review: fde-kit, tasks T11, T12, T13 (full review)

The three tasks meet their plan criteria and the tree is green. One gap in T13 should be settled before you pay for the live campaign: the trials don't receive the role file, so the campaign wouldn't measure what a real run sees.

**Checks I ran:**
- **Tests:** `uv run pytest -q tests/orchestrator tests/sdlc_rework tests/fde_kit` gives 198 passed.
- **Lint:** `ruff check` and `ruff format --check` are clean.
- **Other guards:**
  - The brand guard is green, with an empty denylist.
  - `uv lock --check` is green.
  - The content guard reports spec.md and design.md substance identical, so no version bump was needed.
- **Not run:**
  - `just gate-ci` was refused by this session's permissions, so I ran its parts one by one instead, except `examples-gate`.
  - The CP-4 live campaign and spot checks are billed and human-only; I did not run them.

## ✅ Conformant

**T11 (`50f9c61`)**
- `lab/engine/orchestrate.py:218-221`: the old `.claude/agents` fallback is gone. The agent file is always `lab/plugin/agents/<role>.md` (ADR-3).
- `context_budget.py`, the `ROLE_PROMPT` paths in `eval_models.py`, and the `lab_init.py` docstring all point to `lab/plugin/` now (I-15).
- `tests/fde_kit/test_eval_2_plugin.py:113-124` checks the Stop, SubagentStop and PostToolUse hooks, wired through `${CLAUDE_PLUGIN_ROOT}` (ADR-4).
- `tests/orchestrator/test_hooks.py:63-85` covers an instance that has `.lab/lab.toml` but no `pyproject.toml`: red evals give exit 2 (I-4).
- `tests/fde_kit/test_plugin_cutover.py` checks that `git ls-files .claude` is empty and that no engine file references `.claude/`.
  - It exempts `planlint.py:45` and `plan.py:33`. I checked both: they only *name* the folder (in a docstring and a comment), to detect Owner-lane tasks.
- `tests/fde_kit/test_eval_2_run_preflight.py:249-251` relaxes one assertion. This is justified: the agent path in the prompt is now absolute under `k/lab`, while the `--plugin-dir` and `--settings` values still have to be relative.

**T12 (`a243a5d`)**
- `lab/plugin/rules/hard-rules.md` matches the three sections removed from CLAUDE.md, except for one blank line. Its only commit is T3 (`81cbfee`), so no rule was added or reworded.
- CLAUDE.md shares no line longer than 40 characters with the rules file.
- CLAUDE.md now points to the rules file, states the brand-guard scope (`examples/**` scanned, `**/assets/**` excluded, ADR-9), and says agents load with `--plugin-dir lab/plugin`.
- AGENTS.md is still a pointer to the rules file; `test_agents_md.py` now compares its size against the rules file.
- `context_budget.py:32-38` counts the rules file and counts CLAUDE.md only when it exists; a new test covers both cases.

**T13 (`046b936`)**
- `eval_models.py:94-102` now builds its command with `runner.claude_argv` (I-1).
- `kit_options()` at `eval_models.py:77-89` adds the plugin dir, settings and rules with absolute kit paths, and never `--bare`. It keeps the allowed tools, `--model` and the per-trial temp folder.
- `tests/fde_kit/test_eval_models_argv.py` tests this with the shim only (no billed call), for both the behavioral and chain layers.
- The task cites two blocks of hand-built command code (`:83-99`, `:132-148`), but only one existed. The second range is `run_behavioral`, which already called `call_model`, so one change fixes both layers.

**Traceability:** each commit has its spec IDs in the subject and the `Spec-IDs:` trailer. Every file touched is inside its task's `files_touched`, plus the task's status line in `tasks.md`.

## ⚠️ To arbitrate

1. **T13 does not fully meet ADR-11 ("same options as a run").** This affects what the billed campaign measures.
   - `eval_models.py:62,69`: `ROLE_PROMPT` cites the role file by a relative path, `lab/plugin/agents/<role>.md`. Each trial runs in a temp `labeval-*` folder where that path doesn't exist.
   - `call_model` (`eval_models.py:94-102`) passes no `add_dirs`.
   - A real run in an outside project uses the absolute `agent_file()` path (`orchestrate.py:498,796`) and passes `--add-dir LAB` (`orchestrate.py:292`).
   - So in live trials the model gets the rules but cannot read its role file (implementer.md or reviewer.md). ADR-11's context (`design.md:270-272`) names exactly this gap: "sans règles **ni agents**".
   - **Recommendation:** before running the billed campaign, reject back to T13 (`reject.sh CP-4 work/fde-kit "…" T13`). Use `agent_file()`-style absolute paths in `ROLE_PROMPT`, pass `add_dirs=[kit root]`, and add one shim assertion for both.
2. **Duplicated paths.** `kit_options()` (`eval_models.py:77-89`) repeats the paths from `guardrail_options()` (`orchestrate.py:198-215`) instead of sharing them. There is still only one function that builds the command, but if the rules file moves, the two copies can drift apart.
3. **The trajectory guard is red.** It is not part of `gate`, and neither cause is in T11–T13.
   - `trajectory_guard.py` treats T15 as forged (`journal.jsonl:33`, a `task_done` marked `lane: owner` with no attempt before it). The guard doesn't know about the Owner lane added in `ed61c07`, so the guard needs fixing, not the task.
   - It also flags old scope drift: `progress.md` was touched by T7 (`192203b9`).
   - `journal.jsonl:1` still holds a fake `run_end` from a dry run, already raised at CP-1 and CP-3.
4. **Placeholder commit bodies.** The `Why:` line in each auto commit (`50f9c61`, `a243a5d`, `046b936`) only repeats the task title and `done_when`; it records no reasoning. One example: why `planlint.py` and `plan.py` are exempt is written only in a test comment. This is how the orchestrator writes all its auto commits, not something these tasks did.
5. **CP-4's own checks are still pending and are yours to run:**
   - `just eval-models layer=behavioral live=1` then `layer=chain live=1`, and read the dated scorecards.
   - Ask a real `claude -p` (built with the run's command) to write `.approvals/CP-1`; it should be denied (EX-5).
   - Open `claude --plugin-dir lab/plugin` in a temp instance; it should show the hard rules (BHV-2b).
   - Check whether `--settings` still applies under `--bare`.
   - Item 1 bears directly on the first of these.

## ❌ Blockers

None found in the code. T11–T13 meet their `done_when`, and the suites and guards I ran are green; `examples-gate` was not run.

VERDICT: WARN