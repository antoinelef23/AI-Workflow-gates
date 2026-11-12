# Review CP-1 — panel of 1 — aggregated verdict: WARN (WARN)

## Panelist 1 — claude-opus-5-5 — lens: full review
VERDICT: WARN

# CP-1 review: fde-kit, first vertical slice (T1–T4), full review, second pass

This is a fresh review. Since the first CP-1 report (`7b32145`), spec 0.6.0 and design 0.4.0 were amended (`ee62961`, `17b014f`, `caabeb4`). I checked those amendments for impact and re-ran the slice myself.

## What I ran
- **Gate, run as separate steps** (running `just` as one command needed approval):
  - `ruff check` and `ruff format --check` are clean.
  - `uv lock --check` is green.
  - The full pytest run passes: **1307 tests**, unit tests and evals.
  - `brand_guard --all` passes, but see the note under Reminders.
  - `content_guard --git` reports the substance of `spec.md` and `design.md` as identical.
  - Plan-lint (`--validate`) passes. Its only warnings are the expected "EVAL-n carried by no task" for iterations 2–4, now including EVAL-14.
- **`lab init` on a temp instance** (a plain directory: `git init` in the scratchpad needed approval, and `lab init` never calls git):
  - The first run created the 6 EX-4 files.
  - The second run printed `0 changement`.
  - `--dry-run` on a fresh directory wrote nothing.
  - Leaving out `--profile` gave rc 1 and listed the three profiles.
  - Nothing was created under `.claude/`, and no `CLAUDE.md` or `AGENTS.md`.
- **Pre-flight:**
  - With `kit_version = "0.4.0"`, `lab run work/f --project <tmp> --dry-run` gave rc 1 and `⛔ pre-flight: plugin 0.1.0 ≠ pinned kit 0.4.0`.
  - After restoring the pin, the pre-flight passed.
  - `orchestrate.py work/fde-kit --dry-run` passes the kit-mode pre-flight.
- **Amendment impact:** spec 0.6.0 only adds BHV-12, INV-16, EX-11, EVAL-14 and a clarification of NG-5. Design 0.4.0 only adds ADR-12, still `proposed`. Neither touches BHV-1/2, INV-1/7/8, EX-4/5 or EVAL-1/2, so T1–T4 still conform. The version pointers in `tasks.md:8-9` (0.6.0 / 0.4.0) are coherent.

## ✅ Conformant
- **Traceability:**
  - The 4 commits (`efcc57d`, `318d5c6`, `81cbfee`, `2a04e35`) follow the canonical `[auto]` shape: subject with `[IDs]`, the auto `Why:` (title + `done_when`, allowed by `docs/reference/commit-format.md:35`), and the trailers `Spec-IDs`, `Artifacts` and `Run: auto`.
  - Each task's IDs appear in its diff and in its tests: `test_eval_1_*` ×14 and `test_eval_2_*` ×22.
  - There is no hand-written code: every commit is `Run: auto`.
- **T1 / ADR-5:**
  - There is one root resolver, `lab/engine/kit.py:27-39`, with no walk-up to a `pyproject.toml`.
  - Every lookup listed in I-14 goes through it, including `approve.sh:9` and `reject.sh:11`, which now use `kit.py root` instead of `git rev-parse`.
  - Packaging is `fde-kit`, with `packages=["lab"]` and the `lab` script. `uv.lock` is updated in the same commit.
- **T2 / ADR-7 and ADR-8:**
  - The plan is computed before anything is written, and files are only ever `create`, `identical` or `skip` (`lab_init.py:156-214`).
  - A justfile that doesn't parse stops the run before any write (`:196`). The original bytes are restored if the append fails (`:220-239`).
  - The generic recipes fail closed (BHV-1b).
  - The `.lab/lab.toml` reader is explicit and checks `schema_version` (`:60-87`).
  - The templates are `*.template.md` (OQ-10), and `--profile` is required (OQ-11).
- **T3:**
  - `run_settings.json` holds exactly the 2 denies and no hooks.
  - The hooks go through `${CLAUDE_PLUGIN_ROOT}`.
  - `guard_paths.sh` blocks when it can't read the payload, and it catches relative, absolute, `./` and `../` forms.
  - `hard-rules.md` matches the three CLAUDE.md sections.
  - The marketplace owner name is generic.
  - The version is `0.1.0` in pyproject, `plugin.json` and the marketplace entry.
- **T4:**
  - The argv is unchanged when no option is requested, and `--bare` is never passed (`runner.py:92-97`).
  - The options are added on every call (`orchestrate.py:302`) and resolved from LAB.
  - Kit mode uses relative paths (ADR-10).
  - The pre-flight runs before the lock, runs on `--dry-run`, and is skipped on `--validate` (`:886`).
  - The pin message uses the EX-5 wording (O-1).
  - Sandbox combined with `--project` is refused.
  - The agent file is resolved on each call, with the legacy fallback marked transitional (`:213-220`).
- **First-report deviation #1 is resolved:** the live `claude -p --plugin-dir lab/plugin` sanity call was made and recorded in the `Why:` of `7b32145`. With CLI 2.1.322, an ordinary Edit went through, a Write to `.approvals/CP-1` was denied, and `claude plugin validate` passed.
- **Quality:** ruff is clean, there are no orphan TODOs and no secrets, and `.claude/`, `CLAUDE.md` and `src/` are untouched.

## ⚠️ Deviations for the Owner (none blocking, still not decided)
1. **`lab/plugin/hooks/guard_paths.sh:7` only reads `tool_input.file_path`.** NotebookEdit sends `notebook_path`, so the guard lets a notebook write under `.approvals/` or `.runs/` through. The `Edit(**/…)` denies in `run_settings.json` remain the backstop. The script matches what the T3 prompt asked for. Suggest a one-line fix in T11.
2. **`orchestrate.py:248-251` compares against `kit_version()`, not `plugin.json`.**
   - The message says "plugin X", but the pre-flight never reads `lab/plugin/.claude-plugin/plugin.json`. A drifting manifest is caught only by `test_eval_2_version_coherence` in kit CI.
   - This matches ADR-2's reading "plugin version = kit version", but BHV-2a literally says "plugin version".
   - The Owner should confirm that reading.
3. **`orchestrate.py:205,231` detects kit mode with `PROJECT != LAB`.** PROJECT is resolved; LAB is not when `LAB_ROOT` is relative (`kit.py:31-32`). With a relative `LAB_ROOT` and `--project` on the same directory, the kit is treated as an external instance and refused. This fails closed, is an edge case, and has no test.
4. **INV-1 is only partly met in `--project` runs until T11.** The plugin doesn't carry the `Stop`/`SubagentStop` eval-gate hooks yet: T3 deliberately defers them to T11, as the plan records. Meanwhile, the post-T4 pre-flight already accepts an external instance. The engine's own per-task eval gate still applies, and merge only happens after T11 (CP-5). I recommend not running the kit on a real instance before CP-3.

Minor notes, not deviations:
- `test_eval_2_rules_file_has_the_three_sections` (`tests/fde_kit/test_eval_2_plugin.py:79-83`) checks the headings, not that the copy is verbatim. Any CLAUDE.md amendment before T12 would let the two sources drift silently.
- In a run, the hard rules are injected twice: by `--append-system-prompt` and again by the plugin's SessionStart hook. In kit mode CLAUDE.md adds a third copy. ADR-3 assigns SessionStart to interactive sessions only, so this costs tokens without doing harm.
- If the post-append re-read fails, the justfile is restored but the other files written in the same run are not rolled back (`lab_init.py:242-254`). A justfile that isn't UTF-8 makes `_append_recipes` (`:222`) raise without being caught, after the other files are written.

## ❌ Blockers
None.

## Reminders for the Owner
- **`--dry-run` writes to the real run journal.** `orchestrate.py:1006-1011` appends a `run_end` event whose statuses are all "done", even on `--dry-run`.
  - The CP-1 review steps tell you to run that dry-run on the kit, so it pollutes `work/fde-kit/.runs/journal.jsonl`.
  - This code dates from `09d1e53` (initial commit), so it is outside the slice. The journal is local and not committed.
  - **My own check added one such event (ts 13:42:02)**; there are now 3 `run_end` lines in total.
  - `run_report` and `trajectory_guard` read this file. Fixing it belongs in a separate task.
- **`work/fde-kit/.approvals/CP-1` already exists.** It was signed `approved_by=Claude` at 13:39:34, on the Owner's instruction (`tasks.md:7`). The protocol requires the restarted engine to regenerate the review before that approval is honored. This report is the regenerated review: please confirm the approval still stands in light of it.
- **`lab/engine/brand_denylist.txt` is empty**, so `check-brand` passes without checking anything. This is outside the slice.
- **Not run by me** (each needed approval): `just gate` as a single command, `git init` of the temp repo, `just evals` inside the instance (covered by `test_eval_1_non_python_recipes_fail_closed`), and a new live `claude -p` call (already done and recorded in `7b32145`).
- A restart at CP-1 is recommended; CP-3 is the hard gate.

VERDICT: WARN