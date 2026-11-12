# Review CP-1 — panel of 1 — aggregated verdict: WARN (WARN)

## Panelist 1 — claude-opus-5-5 — lens: full review
VERDICT: WARN

# CP-1 review: fde-kit, T1–T4 (full review, third pass)

The T1–T4 code is conformant, and every check I could run is green, but CP-1 must not be approved on the live run as it stands. The orchestrator (pid 899, started 14:04) lost its state and re-ran T1–T4. Once CP-1 is approved, it will replay work that is already committed.

## How this pass differs from the earlier ones
- The four T1–T4 commits currently at the top of the branch (`15f628c`, `92fb92e`, `6536375`, `2bad205`) each change one line of `work/fde-kit/tasks.md` (the run log) and nothing else.
- The real implementation is in `efcc57d`, `318d5c6`, `81cbfee` and `2a04e35`. It was already reviewed at CP-1 (`7b32145`) and is the subject of this report.
- Since then, the only change in the slice's paths is `pyproject.toml` (+1 line, T5) and `tests/fde_kit/test_doc_pointers.py` (T10). The T1–T4 code itself is unchanged.

## What I ran
- **Gate, as separate steps** (`just` needs approval here):
  - `ruff check` and `ruff format --check` are clean.
  - `uv lock --check` is green.
  - All of pytest passes: **182 tests**, 50 of them evals. The slice suites alone are 179/179.
  - Plan-lint passes. Its only warnings are the expected "EVAL-n carried by no task".
  - `content_guard --git` reports the substance of `spec.md` and `design.md` as identical.
  - `brand_guard --all` passes, but its denylist is empty.
- **`lab init` on a temp instance** (a plain directory, because `git init` needs approval):
  - The first run created the 6 EX-4 files.
  - The second run printed `0 changement`.
  - `--dry-run` on a fresh directory wrote nothing.
  - Leaving out `--profile` gave rc 1 and listed the three profiles.
  - Nothing was created under `.claude/`, and no `CLAUDE.md` or `AGENTS.md`.
  - The generic justfile recipes fail closed.
- **Pre-flight:**
  - With `kit_version = "0.4.0"`, `lab run work/f --project <tmp> --dry-run` gave rc 1: `plugin 0.1.0 ≠ pinned kit 0.4.0`.
  - After restoring the pin, it gave rc 0.
- **Rules file:** `lab/plugin/rules/hard-rules.md` is a verbatim copy of the three `CLAUDE.md` sections, checked section by section.
- **Untouched files:** `.claude/` and `CLAUDE.md` show no diff since before T1.
- **Not run:**
  - The kit-mode `orchestrate.py work/fde-kit --dry-run`. The live run shares that `.runs/`, and a dry-run appends a false `run_end` to its journal.
  - A new live `claude -p` call. One was already made and recorded in the `Why:` of `7b32145`.

## ✅ Conformant
- **T1 (ADR-5):**
  - There is one root resolver, `lab/engine/kit.py:27-39`, with no walk-up.
  - The version comes from installed metadata, with a fallback to `pyproject.toml` (`kit.py:42-57`).
  - The CLI is a thin wrapper that keeps the engine's flat imports (`lab/engine/cli.py:16`).
  - Packaging is `fde-kit` with `packages=["lab"]`, and the lockfile is fresh.
- **T2 (ADR-7, ADR-8):**
  - The plan is computed first, and files are only `create`, `identical` or `skip`.
  - The templates are `*.template.md` (OQ-10), and `--profile` is required (OQ-11).
  - EVAL-1 is green.
- **T3 (ADR-1 to ADR-4):**
  - `lab/engine/run_settings.json` holds exactly the 2 denies and no hooks.
  - The hooks go through `${CLAUDE_PLUGIN_ROOT}` (`lab/plugin/hooks/hooks.json:9`), and the guard has `onFailure: block`.
  - The guard blocks if it can't read the payload (`guard_paths.sh:7-10`).
  - The version is `0.1.0` in pyproject, `plugin.json` and the marketplace entry, and the owner name is generic.
- **T4 (ADR-2, ADR-6, ADR-10):**
  - The argv is unchanged when no option is requested, and `--bare` is never passed (`runner.py:92-97`).
  - The options are added to every call through `run_claude` (`orchestrate.py:302`), reviewer included (`:674`).
  - They are resolved from LAB, and kit mode uses relative paths.
  - The pre-flight runs before the lock, on real runs and on `--dry-run`, and never on `--validate`.
  - The pin message uses the EX-5 wording (O-1).
  - Sandbox combined with `--project` is refused.
  - The agent file is resolved on each call (`:213-220`). This review was itself started with the legacy `.claude/agents/reviewer.md`, as expected before T11.
- **Self-hosting:** the live engine was started from a tree that contains T4, so it is already a post-T4 engine. The recommended restart is effectively done.

## ⚠️ Deviations for the Owner
1. **The run state was lost, and approving CP-1 now would replay T5–T10.**
   - `state.json` and `journal.jsonl` are gitignored (`.gitignore:25-26`) and didn't survive the session change. The journal now starts at 14:04.
   - The engine re-ran T1–T4: 4 agent calls, about $1.62, no code change.
   - `state.json` lists T5, CP-2, T6, T7, T8 and T10 as `pending`, even though they are already committed (`89d2532`, `90fb9f9`/`c2aebe2`, `192203b`, `6f3948d`, `a44e003`).
   - If CP-1 is approved, the engine will ask for CP-2 again and re-run T6, a "pure move" whose sources no longer exist. It will also re-run T7, which earlier blocked on tool rights that haven't been fixed in the agent's tools (`progress.md` §5, item 13).
   - This contradicts the handoff, which says the run resumes at T7 (`progress.md` §6.3).
   - **Recommendation:** stop pid 899. Then either rebuild `state.json` with those nodes marked done (it's an engine file, so that's a human decision), or approve CP-1 knowing the replay will happen and supervise it. Don't sign CP-1 on the live run as it stands.
2. **Duplicate commits that carry no code.**
   - `15f628c` through `2bad205` have the same subjects, `Spec-IDs` and `Artifacts` as the real T1–T4 commits, but their diff is a single log line.
   - `git log --grep 'T4 Engine'` now returns two candidates, and the `Artifacts:` trailer of the second one is false.
   - Rewriting history isn't required. I suggest a note commit or a `git notes` entry pointing to `efcc57d`…`2a04e35`. This is a gap in the "why lives in git" rule: the commits should say they replay already-done work.
3. **The journal is polluted again.** Line 1 of `work/fde-kit/.runs/journal.jsonl` is a `run_end` at 14:04:09 with cost 0 and every status, including CP-5, set to "done". It comes from a `--dry-run` (`orchestrate.py:1008`), a known issue (`progress.md` §7.5). `run_report` and `trajectory_guard` read this file.
4. **Deviations from the earlier CP-1 pass, still not decided (the code hasn't changed):**
   - `lab/plugin/hooks/guard_paths.sh:7` ignores `notebook_path`. The `Edit(**/…)` denies remain the backstop.
   - `orchestrate.py:248-249` compares against `kit_version()`, not `plugin.json`. ADR-2 reads it that way, while BHV-2a literally says "plugin version". The Owner should confirm.
   - `orchestrate.py:205,231` compare `PROJECT != LAB` while LAB isn't resolved when `LAB_ROOT` is relative (`kit.py:31-32`). This fails closed and has no test.
   - INV-1 is only partly met in `--project` runs until T11, because the plugin doesn't carry the Stop/SubagentStop hooks yet. The kit shouldn't run on a real instance before CP-3.

Minor notes:
- `lab run` on a feature without a `tasks.md` crashes with a raw `FileNotFoundError` (`orchestrate.py:835`) instead of a clean rc 1. This predates the slice.
- `test_eval_2_rules_file_has_the_three_sections` checks the headings, not that the copy is verbatim. The copy is verbatim today, as I checked by hand.
- `lab_init` doesn't roll back the other files if the justfile append fails (from the earlier pass).

## ❌ Blockers
None in T1–T4: the code meets BHV-1, BHV-2, BHV-2a, BHV-2b, INV-1 (partly, see 4), INV-7, INV-8, EVAL-1 and EVAL-2. Deviation 1 is an operational hazard to settle before signing. Sending T1–T4 back wouldn't fix it.

## Reminders
- `work/fde-kit/.approvals/` doesn't exist: the signatures from the earlier CP-1 and CP-2 were lost with the old environment. A new `LAB_APPROVAL_SECRET` is needed.
- `lab/engine/brand_denylist.txt` is empty, so `check-brand` passes without checking anything.

VERDICT: WARN