# Review CP-4 — panel of 1 — aggregated verdict: WARN (WARN)

## Panelist 1 — claude-opus-5-5 — lens: full review
VERDICT: WARN

# CP-4 review, second pass: fde-kit, T11 to T13 (full review)

The fix for my first-pass finding is in place, but it opens too much. T13 now lets trials read their role file, which closes the ADR-11 gap. To do that it gives every trial read access to the whole kit, and that includes the hidden scoring checks. This should be settled before you pay for the campaign.

**Checks I ran:**
- **Tests:** `uv run pytest -q tests/orchestrator tests/sdlc_rework tests/fde_kit` gives **200 passed** (198 at the first pass; the 2 new ones come from `94f273e`).
- **Lint:** `ruff check` and `ruff format --check` are clean.
- **Lockfile:** `uv lock --check` is green.
- **Brand guard:** green, but the denylist is empty, so it checks nothing.
- **Content guard:** spec.md and design.md substance is identical to before T15 (`2be6b62`), so no version bump was needed.
- **Not run:** `just gate-ci` with `examples-gate`, and the billed live campaign (human-only).

## ✅ Conformant

**T11 (`50f9c61`) and T12 (`a243a5d`):** no change since the first pass, and those findings still hold. The `.claude/` fallback is gone, the plugin hooks are tested, the hard rules live in one file, and CLAUDE.md now holds only the kit-specific parts.

**T13 rework (`bc58ecd`), checked against the reject note (`tasks.md:669`):**
- `lab/engine/eval_models.py:76-80`: `ROLE_PROMPT` now gives the role file's absolute path, built from `kit_root(honor_env=False)`. The old relative path is gone.
- `lab/engine/eval_models.py:90`: `kit_options()` adds `add_dirs=[kit root]`. This matches a real run's `--add-dir LAB` (`orchestrate.py:292`), and it reaches the behavioral layer (`:175`), the chain layer and the scorecard layer (`:228`), all through `call_model` (`:108`).
- `tests/fde_kit/test_eval_models_argv.py:75-82`: one shared assertion, used by both the behavioral and chain tests. It checks `--add-dir` equals the repo root, that the prompt holds the absolute agent path, and that the relative form is gone. This is what the reject note asked for.
- **Scope:** only `eval_models.py`, the test file and the `tasks.md` journal changed, all inside `files_touched`. `orchestrate.py` was not touched, as instructed.
- **Traceability:** the subject is tagged `[BHV-2]` and the `Spec-IDs: BHV-2` trailer is present.
- **Quality:** no TODO or FIXME, and no secrets.

**`94f273e`** (an Owner engine fix, outside T11 to T13): the trajectory guard now accepts an `owner_signed` event as proof of an Owner-lane attempt. The commit body explains why, and it comes with tests.

## ⚠️ To arbitrate

1. **`--add-dir <kit root>` lets trials read the hidden evals. Settle this before the billed campaign.**
   - **Where:** `lab/engine/eval_models.py:90` applies to every layer.
   - **Scorecard layer:** the harness deliberately leaves `goldeval/` out of the trial's folder (`eval_models.py:221`) and copies it in only after the model has finished (`:231`). With the whole kit readable, the model can still open `evals/golden/*/goldeval/check.sh` directly.
   - **Behavioral and chain layers:** the model can also read `evals/behavioral/cases.py`, which holds the `check()` logic that grades it.
   - **Nothing denies these reads:** `lab/engine/run_settings.json` only denies edits to `.approvals` and `.runs`.
   - **Why it matters:** this breaks the fairness rule in `lab/models/EVOLUTION.md:10-12` ("judged against references that the model does not write itself"). The prompt now hands the model an absolute path inside the kit, which makes it more likely to wander there.
   - **How this happened:** the kit-root grant was what the Owner's reject note prescribed (`tasks.md:669`), and it came from my first-pass recommendation. The implementer followed it faithfully, so this is a decision to revisit, not an implementer error.
   - **Recommendation:** narrow the grant to `lab/plugin` (or `lab/plugin/agents`), which is all the trials need to read. A real run's `--add-dir LAB` is fine because an orchestrated run doesn't sit next to the answer key. Add a shim assertion that `--add-dir` does not cover `evals/`. If you choose to keep the kit-root grant, run only `layer=behavioral` and `layer=chain`, never `live=1` on every layer, and record that the reviewed scorecards could have seen the hidden checks.
2. **The role-path text can break on unusual folder names** (`eval_models.py:80` with `:172` and `:225`). The absolute path is put into the template before `.format()` runs, so a kit folder whose path contains `{` or `}` would crash every trial with a KeyError. It is unlikely. A fix is to escape the path, or pass `agents=` to `.format()`.
3. **Duplicated paths** (`eval_models.py:84-96` and `orchestrate.py:198-215`) are unchanged. The reject note ruled this out of scope, so I list it only as a note.
4. **The trajectory guard is still red, with 2 violations, neither caused by T11 to T13:**
   - T15 has no prior attempt in the journal. Its entry was written before `94f273e`, which records this.
   - `192203b` (T7) touched `progress.md`; this was already raised.
   - `just check-trajectory` is a criterion of the final checkpoint, so it has to be dealt with before then, not at CP-4.
5. **The `Why:` line is a placeholder** in `bc58ecd`. It repeats the task title and does not mention the CP-4 rejection that triggered the rework, so the reason is only in the `tasks.md` journal. This is how the orchestrator writes all its automatic commits.
6. **CP-4's own checks are still yours to run:**
   - The live campaign: behavioral first, then chain.
   - A real `claude -p` asked to write `.approvals/CP-1` should be denied (EX-5).
   - An interactive `claude --plugin-dir lab/plugin` session should show the hard rules (BHV-2b).
   - Check whether `--settings` still applies under `--bare`.
   - Item 1 bears directly on the first of these.

## ❌ Blockers

None in the code. T11 to T13 meet their `done_when` and the suites I ran are green. I did not run `examples-gate`.

VERDICT: WARN