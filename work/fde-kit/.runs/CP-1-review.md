# Review CP-1 — panel of 1 — aggregated verdict: WARN (WARN)

## Panelist 1 — claude-opus-5-5 — lens: full review
VERDICT: WARN

# CP-1 review: fde-kit, first vertical slice (T1–T4)

**Verdict: WARN.** I found no blockers. There are four deviations for the Owner to decide on. The required live `claude -p` sanity check was not done: running `claude` needs approval in this session.

## What I checked myself
- **Tests and gate parts:** the full pytest run passes, 1307 tests (unit tests and evals). Ruff check and ruff format are clean. `uv lock --check` is green, brand_guard is clean, and plan-lint (`--validate`) is green, with only the expected warnings about evals not carried by any task.
- **`lab init` on a temp instance:** I couldn't create a git repo in the scratchpad without approval, so I used a plain directory (`lab init` never calls git). The first run created 6 files, matching EX-4. The second run printed `0 changement`. `--dry-run` wrote nothing. Leaving out `--profile` gave rc 1 and listed the three profiles.
- **Pre-flight:** with `kit_version = "0.4.0"`, `lab run work/f --project <tmp> --dry-run` stopped with rc 1 and `plugin 0.1.0 ≠ pinned kit 0.4.0`. After restoring the pin, the pre-flight passed. `orchestrate.py work/fde-kit --dry-run` passes the kit-mode pre-flight.
- **Untouched files:** `.claude/`, `CLAUDE.md`, `src/`, `spec.md` and `design.md` show an empty diff from `39cd052` to `2a04e35`.

## ✅ Conformant
- **Traceability:** all 4 commits follow the canonical format: subject with `[IDs]`, an auto `Why:` (title + `done_when`, as `docs/reference/commit-format.md` allows for `[auto]` commits), and the trailers `Spec-IDs`, `Artifacts` and `Run: auto`. Each task's IDs appear in its diff. Version pointers line up (spec 0.5.0, design 0.3.0).
- **T1 / ADR-5:** one root resolver, `lab/engine/kit.py:27-39`, with no walk-up to a `pyproject.toml`. Every lookup listed in I-14 goes through it (`orchestrate.py:73`, `eval_models.py:47-55`, `context_budget.py:61`, `run_report.py:150`, `trajectory_guard.py:116`, `approve.sh:9`, `reject.sh:11`). Packaging is `fde-kit`, `packages=["lab"]`, with the `lab` script, and `uv.lock` is updated in the same commit (O-3).
- **T2 / ADR-7 and ADR-8:**
  - The plan is computed first, and files are only ever `create`, `identical` or `skip` (`lab_init.py:156-214`).
  - The templates are named `*.template.md` (OQ-10), and `--profile` is required (OQ-11).
  - Only data is written (INV-8).
  - A justfile that doesn't parse stops the run before any write (`:196`), and the original bytes are restored if appending a recipe fails (`:220-239`).
  - The generic recipes fail closed (BHV-1b).
  - The `.lab/lab.toml` reader is explicit and checks `schema_version` (`:60-87`).
- **T3:** additive only.
  - `run_settings.json` holds exactly the 2 denies and no hooks.
  - The hook commands go through `${CLAUDE_PLUGIN_ROOT}`.
  - `guard_paths.sh` blocks if it can't read the payload.
  - `hard-rules.md` is a verbatim copy of the three CLAUDE.md sections.
  - The marketplace owner name is generic.
  - The versions match across pyproject, `plugin.json` and the marketplace entry (I-19).
- **T4:**
  - The argv is unchanged when the new options aren't requested, and `--bare` is never passed (`runner.py:92-97`).
  - The options are added on every call (`orchestrate.py:302`).
  - They are resolved from LAB, never from PROJECT (I-2).
  - Kit mode uses relative paths, and `cwd=PROJECT=LAB`.
  - The pre-flight runs before the lock, runs on `--dry-run`, and is skipped on `--validate` (`:885-890`).
  - The pin message uses the spec EX-5 wording (O-1).
  - Sandbox combined with `--project` is refused.
  - The agent file is resolved on each call, with the legacy fallback marked transitional (`:213-220`).
- **Quality:** no orphan TODO and no secrets.

## ⚠️ Deviations for the Owner
1. **The live sanity call in the CP-1 reviews was not run.** That call is `claude -p --plugin-dir lab/plugin`, checking that an ordinary edit is not blocked while `onFailure: block` is set. The `claude` CLI version is also unchecked. This is the one point the tests can't cover: a faulty guard would freeze every later agent. The Owner must run it before approving.
2. **`lab/plugin/hooks/guard_paths.sh:7` reads only `tool_input.file_path`.** NotebookEdit sends `notebook_path`, so the hook lets a notebook write under `.approvals/` or `.runs/` through. The `Edit(**/.approvals/**)` deny in `run_settings.json` should still catch it (my understanding is that Edit rules cover NotebookEdit in Claude Code, but I didn't check). The guard itself matches what the T3 prompt asked for. Suggest a one-line fix in T11.
3. **`orchestrate.py:244-249`:** the message says "plugin X", but X is `kit_version()` (from pyproject or package metadata). The pre-flight never reads `lab/plugin/.claude-plugin/plugin.json`. A drifting manifest is caught only by the I-19 test in kit CI, never at run time. This matches the ADR-2 reading "plugin version = kit version", but BHV-2a literally says "plugin version".
4. **`orchestrate.py:207,230`:** kit mode is detected with `PROJECT != LAB`. PROJECT is always resolved, but LAB is not when `LAB_ROOT` is set (`kit.py:31-32`). With a relative `LAB_ROOT` and a `--project` pointing at the same directory, the kit is treated as an external instance and refused because it has no `.lab/lab.toml`. This fails closed, it's an edge case, and it's not covered by tests.

Minor notes, not deviations:
- The pre-flight also checks that `hard-rules.md` and `run_settings.json` exist (`:236-238`), which the prompt didn't ask for. It fails closed and serves BHV-2a.
- If the post-append re-read fails, the justfile is restored but the other files written in the same run are not rolled back (`lab_init.py:242-254`). The only "nothing written" promise, for a justfile that doesn't parse, is kept.

## ❌ Blockers
None.

## Reminders for the Owner
- A restart at CP-1 is recommended (self-hosting protocol); CP-3 is the hard gate.
- `just gate` as a single command needed approval. I ran its parts directly: lint (ruff check + format --check), test + evals (the full pytest run), check-brand and the lock check, all green.

VERDICT: WARN