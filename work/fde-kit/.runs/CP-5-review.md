# Review CP-5 — panel of 3 — aggregated verdict: WARN (WARN, WARN, WARN)

## Panelist 1 — claude-opus-5-5 — lens: correctness: does the code do what the spec says (INV/BHV), values and bounds included
VERDICT: WARN

## CP-5 review (correctness lens): fde-kit iteration 1, T1–T15

**Scope checked:** iteration 1 only (BHV-1/1b–1e, BHV-2/2a/2b, INV-1, INV-7, INV-8, INV-9; EVAL-1/2/8), reading code against spec 0.6.0 and design 0.4.0.

**What I ran:**
- `uv run pytest -q`: 222 passed.
- `uv run pytest -m eval tests/fde_kit`: 48 passed.
- `ruff check` and `ruff format --check`: both clean. The ruff-format failure that caused the first CP-5 BLOCK is fixed (e72d97e).
- `uv lock --check`: green.
- Both examples, `uv sync --locked` then `pytest -m eval`: devis 1063 passed, booking 8 passed.
- `just gate-ci` itself was refused by the sandbox permissions. I ran each of its recipes' commands by hand instead, and all were green.

### ✅ Conformant
- **BHV-1 / EX-4 (`lab init`).** The plan is computed first. Each file is classified create, identical or skip, never overwritten, with one line per file (`lab/engine/lab_init.py:163-250`). Only `.lab/lab.toml`, `work/README.md`, `work/_templates/*.template.md` and the justfile recipes are written, which satisfies INV-8.
  - The second run prints "0 changement" (`lab_init.py:268`), which covers BHV-1c.
  - `--dry-run` returns before applying anything (`:255-261`), which covers BHV-1d.
  - An unparsable justfile is detected before any write (`:181`), and an existing `evals` recipe is kept (`:183-187`), which covers BHV-1e.
  - A missing `--profile` gives rc 1 listing the three profiles (`:241-246`; I confirmed this live).
- **BHV-1b.** The generic recipes fail closed with exit 1 and the message "no evals configured" (`lab/templates/instance/evals.generic.just`). The Python recipe maps pytest's rc 5 to 0 (`evals.python.just`), as ADR-8 says. Tested at `tests/fde_kit/test_eval_1_init.py:182`.
- **INV-7.** The pin is exact. `read_lab_toml` raises an explicit error on a missing or invalid file instead of returning silently empty (`lab_init.py:59-86`). Both examples are pinned to `0.1.0` with profile `squad`, matching `pyproject.toml:3`.
- **BHV-2 / EX-5, first block.** `guardrail_options()` (`lab/engine/orchestrate.py:203-215`) resolves plugin dir, settings and rules from the kit (LAB), never from PROJECT. It uses absolute paths for an external instance and cwd-relative paths in kit mode, as ADR-10 requires. The engine never passes `--bare`. `run_settings.json` holds exactly the two denies and no hook.
- **BHV-2a / EX-5, second block.** `orchestrate.py:250-254` emits the spec literal `plugin <X> ≠ pinned kit <Y>` with rc 1.
  - The pre-flight runs before the lock, runs on `--dry-run`, and is skipped on `--validate` (`:1015-1063`).
  - It refuses a CLI older than 2.1.295, and refuses sandbox combined with `--project` (`:255-270`).
- **INV-1, interactive side.**
  - `guard_paths.sh:13-18` denies both relative and absolute paths under `.approvals/` and `.runs/`. It also reads `notebook_path`, and fails closed (exit 2) when the payload can't be parsed.
  - `hooks.json` wires PreToolUse with `onFailure: block`, plus SessionStart, Stop, SubagentStop and PostToolUse, all through `${CLAUDE_PLUGIN_ROOT}`.
  - BHV-2b: `session_start.sh` prints the rules file.
- **ADR-5.** `kit.py:28-40` resolves the root from `LAB_ROOT`, else from the location of the kit's code if it holds the `lab/models/registry.toml` marker, else rc 1. `approve.sh:9` goes through the same function.
- **ADR-11.** `eval_models.py:86-98` uses the same options as a run, with absolute paths. It grants `--add-dir` on the agents directory only, as the CP-4 second pass required.
- **INV-9 / EVAL-8.** The wheel ships only `lab/`. The demo code is tracked under `examples/` only, and the transitional bits are gone (`tests/fde_kit/test_eval_8_examples.py`).

### ⚠️ To arbitrate
1. **Non-Python instances are still not gated at session end (ADR-4 / INV-1).** `lab/plugin/hooks/eval_gate.sh` now enters the gate whenever `.lab/lab.toml` exists (`:16`). But the changed-files filter at `:22` still only matches `.py|.toml|.ts|.tsx|.js|…`.
   - **Failure case:** in a BHV-1b instance (Go, Java, …), editing `main.go` makes the Stop hook exit 0 without running `just evals`. That is the same silent pass ADR-4 set out to remove.
   - The test `tests/orchestrator/test_hooks.py:79` only uses `app.py`, so it can't catch this.
   - The run gate is not affected: per ADR-2 it belongs to the engine. The weakness is only in the interactive guardrail. Owner decision: accept it as-is for 0.x, or file a follow-up to gate on any tracked change when `.lab/lab.toml` exists.
2. **`lab init` is not atomic (minor).** `apply_plan` (`lab_init.py:220-231`) writes `.lab/lab.toml` and `work/` before appending to the justfile. If the re-read after the append fails, only the justfile is restored (`:211-217`), so a rc 1 can leave some files written. ADR-8 only requires the justfile bytes to be restored, so this conforms to the letter. It is a surprising state for the user, though. Possible fix: do the append first, or roll back the files just created.
3. **Outside my lens, for information only:**
   - `lab/engine/brand_denylist.txt` is empty, so `check-brand` passes without enforcing anything. A "green" brand gate is therefore vacuous.
   - The trailers of commit e72d97e carry a duplicated, indented `Run: auto`.

### ❌ Blockers
None. The previous CP-5 blocker (ruff format on `tests/fde_kit/test_doc_pointers.py`) is resolved.

VERDICT: WARN

---

## Panelist 2 — claude-opus-4-8 — lens: spec/design conformance: traceability, scope, ADR compliance, no scope creep
VERDICT: WARN

Right — `.runs/` is a denied path (that's INV-1 working as intended); the engine writes the review, not me. My report is my output. Here it is.

---

# Review CP-5 — merge (human, final)
**Lens:** spec/design conformance — traceability, scope, ADR compliance, no scope creep. Tasks T1–T15. Read-only; the Owner decides, I illuminate.

CP-5 is `mode: blocking` (merge is always human). The mechanical merge gate (`just gate-ci`) is **green**; the deviations below are audit-trail / scope items the Owner arbitrates at merge.

## ✅ Conformant

**Traceability**
- Every fde-kit task commit (T1–T15) carries its subject `[IDs]` tag + `Spec-IDs:` trailer and maps to its task (T1 `[INV-7]` … T14 `[BHV-1, BHV-2]`).
- Human exceptions carry a full `Why:` — the hand commit `192203b9` (T7) explains the account-switch; CP rejections are recorded in `.approvals/`.

**Scope boundary — no iteration 2-4 creep**
- Only `EVAL-1/2/8` modules under `tests/fde_kit/` (+ `test_eval_models_argv.py`, T13's ADR-11 harness — not a spec EVAL). No `test_eval_3..7/9..14`.
- No iteration 2-4 engine modules (`policy`, `goldfish`, `retro`, `adapter`, `improver`). `lab init` records `profile` without applying it — exactly ADR-7.
- Deliberate, documented staging: design.md 0.4.0 scopes iteration 1; spec.md 0.6.0 stages iterations 2-4 by amendment; `tasks.md` warns plan-lint flags later EVALs as carried by no task — **expected**.

**ADR compliance (structural)**
- ADR-3 / T11 cutover: **0 tracked files under `.claude/`**; plugin fully populated (`plugin.json`, `agents/*.md`, `hooks/hooks.json`, `rules/hard-rules.md`, `statusline.py`). Only `.claude/` hit in engine is a comment (`lab/engine/planlint.py:45`).
- ADR-1 / I-19: `pyproject.toml` = `plugin.json` = `marketplace.json` = `0.1.0`.
- ADR-2/INV-1, INV-8, ADR-9/INV-9: carried by green `EVAL-1/2/8` + the prior correctness panel.
- Version pointers coherent (design→spec 0.6.0; tasks→spec 0.6.0 + design 0.4.0).

**Mechanical gate (merge condition) — green**: `ruff format --check` + `ruff check` clean; `uv lock --check` green; `161 passed` + `61 eval passed`; examples (prior panel: devis 1063, booking 8); `content_guard` spec/design = new files, nothing to compare.

## ⚠️ Deviations to arbitrate (Owner)

1. **`just check-trajectory work/fde-kit` → 2 violations, rc≠0** (CP-5 lists this check):
   - **T15 — `task_done` with no prior `owner_signed`** (`trajectory_guard.py:7-8,50-54`; `journal.jsonl:33` has `"lane":"owner"` but **0** `owner_signed` events). T15 is the legitimate Owner-lane task; its signature exists (`.approvals/T15.handled-20261112154253`). The owner-lane branch added in `94f273e` keys on an `owner_signed` event that was never emitted → a real signed task mis-read as "forged." Audit-trail gap, **not** a substance defect (T15's moves are real, evals green).
   - **T7 commit `192203b9` touched `progress.md`** outside `files_touched ∪ work/fde-kit/` (`trajectory_guard.py:74,105`). Documented hand-made human commit during an account switch (`Why:` body); `progress.md` is a session-handoff doc. Recorded decision, but a genuine scope-drift the guard flags.

2. **~6 lab-engine commits bundled, outside the fde-kit triplet** — `deffc82`, `876a54d`, `94f273e`, `f4f151c`, `ed61c07`, `2f3fe92` touch `lab/engine/orchestrate.py`, `planlint.py`, `plan.py`, `trajectory_guard.py` + tests. Orchestrator fixes from dogfooding this plan ("lab-fix batch"), each tested + `Why:`, but none traces to an fde-kit spec ID. Merge-here vs separate lab-maintenance PR is the Owner's call.

3. **Minor:** `46ab6dc fix(fde-kit): … [BHV-7]` tags `BHV-7` (iteration-4 scope) on a revert/housekeeping commit — spurious ID.

## ℹ️ Observation (pre-existing, not introduced here)
- `brand_guard` denylist is **empty** (`lab/engine/brand_denylist.txt`, set at initial commit `09d1e53`, untouched here), so `check-brand` passes vacuously. ADR-9 leans on brand_guard scanning `examples/**`; worth confirming the empty denylist is intended.

## ❌ Blockers
None for the spec/design-conformance lens. The mechanical merge gate is green; all deviations are documented and feed the human merge decision.

VERDICT: WARN

---

## Panelist 3 — claude-sonnet-4-6 — lens: edge cases & robustness: extreme inputs, errors, does the deliverable actually run
VERDICT: WARN

---

# CP-5 Reviewer Report — Edge Cases & Robustness Lens

**Scope:** Tasks T1–T14, T15 | **Checkpoint:** CP-5 merge (human, final)
**Lens:** edge cases & robustness: extreme inputs, errors, does the deliverable actually run

---

## Git archaeology performed

Checked `94f273e` (trajectory guard / owner lane fix), `5a70c84` (guard_paths notebook_path fix), `192203b9` (T7 hand-commit), `2be6b62` (T15 Owner lane) for recorded Why: before flagging any item.

---

## ✅ Conformant

**Kit root resolution (ADR-5, `lab/engine/kit.py:27-39`)**
- Priority order honored: `LAB_ROOT` env → marker at `parents[2]` → `SystemExit(1)`. Empty `LAB_ROOT=""` is falsy → falls through to marker check, no silent bad-path.
- Version fallback (`kit.py:42-57`): `importlib.metadata` → `pyproject.toml` → explicit rc 1. No silent "unknown".

**`lab init` edge cases (BHV-1b/c/d/e, INV-8, `lab/engine/lab_init.py`)**
- Plan-first, classify-then-apply: no file is ever overwritten (`_file_item:156-166`, action ∈ {create, identical, skip}).
- Idempotent second run: "0 changement" (`run:283`). `--dry-run` returns before `apply_plan` (`run:272-278`).
- Non-Python instance: both recipes fail closed with rc 1 and an explicit message (`lab/templates/instance/*.generic.just`).
- Unparseable justfile: `just_recipes` raises `InitError` before any file is written; `run()` catches it and returns 1 (`lab_init.py:196`, `run:280-283`).
- Append failure rollback: original bytes restored when the re-read of the justfile fails after append (`_append_recipes:237-238`). Monkeypatch test confirms (`test_eval_1_justfile_restored_when_reread_fails`).
- `--profile` absent or unknown: rc 1 listing the three profiles, no partial write (`run:260-264`).

**Pre-flight fail-closed (BHV-2a, INV-1, ADR-6, `orchestrate.py:229-271`)**
- Plugin dir missing → rc 1. Pin mismatch → rc 1 with both versions named (spec EX-5 literal). CLI < 2.1.295 → rc 1. Sandbox + `--project` → rc 1. All verified by shim tests.
- `--validate` skips the pre-flight entirely (`orchestrate.py:1012`): gate-ci and pre-commit never need a live claude CLI.
- `--dry-run` does run the pre-flight (verified by `test_eval_2_pin_mismatch_also_refuses_dry_run`).

**`guard_paths.sh` (INV-1, `lab/plugin/hooks/guard_paths.sh`)**
- Fails closed on unreadable JSON payload (exit 2 with message, `guard_paths.sh:8-11`).
- Covers both `file_path` (Edit/Write/MultiEdit) and `notebook_path` (NotebookEdit) after fix `5a70c84`. Test confirms both keys and both protected dirs.
- Bash `case *` matches across `/`, so path traversal like `src/../.approvals/CP-1` is caught.
- `eval_gate.sh` loop-protection via `stop_hook_active` (line 11); `.lab/lab.toml` trigger added (line 16, I-4 fix).

**Plugin structure and version coherence (ADR-1, INV-7, I-19)**
- pyproject `0.1.0` = `lab/plugin/.claude-plugin/plugin.json:"version"` = marketplace entry. Verified by `test_eval_2_version_coherence`.
- `run_settings.json` holds exactly 2 `Edit(…)` denies, no `hooks` key.

**`lab/engine/eval_models.py` harness argv (ADR-11, T13)**
- Builds argv via `claude_argv` with `--plugin-dir`, `--settings`, `--append-system-prompt`, never `--bare`.
- Role file copied into trial's `.agent/` directory (no kit path in the prompt, no `--add-dir` that would reach `evals/`). Verified by `test_eval_models_argv.py:89-93`.

**Full test suite**: 222 passed, 0 failed. All 61 `@pytest.mark.eval` evals green. `ruff check` and `ruff format --check` clean (HEAD `e72d97e`).

---

## ⚠️ Deviations to arbitrate by Owner

**1. `just check-trajectory work/fde-kit` exits 1 — two known violations (`lab/engine/trajectory_guard.py`)**

Both violations were raised at prior checkpoints and have documented Why: in git; they are pre-existing run-execution anomalies, not code correctness defects.

- **⚠️ BHV-2a T15 — `owner_signed` missing from journal** (`work/fde-kit/.runs/journal.jsonl:33`): T15's journal has `task_done` with `lane: owner` but no preceding `owner_signed` event. The fix (`orchestrate.py:624` emits `owner_signed` when the approval token is verified) was added in `94f273e`, which explicitly records: *"T15's entry in the current journal predates this (still flagged until the next Owner-lane task; recorded in progress.md)."* The guard implementation is now correct; the missing event in the existing journal is a run-history artifact. Owner must add a PR note waiving it, or add the missing event to the journal.
  - File: `work/fde-kit/.runs/journal.jsonl:33`

- **⚠️ BHV-2b T7 — `progress.md` outside `files_touched` (`trajectory_guard.py:88-107`)**: Commit `192203b9` (`Run: human`) touched `progress.md` alongside the T7 deliverable files. The guard's docstring says it checks only `[auto]` commits, but the implementation matches ALL commits with the `feat(fde-kit): T<n>` subject pattern, including `Run: human` entries. The commit's Why: explains the touch explicitly. Mitigation options: filter on `Run: auto` in the subject, or Owner waives in PR.
  - File: `lab/engine/trajectory_guard.py:88`

**2. `eval_gate.sh:23` extension filter — partial I-4 fix**
The eval gate fires only when a changed file ends in `.py|.toml|.ts|.tsx|.js|.jsx|.mjs|.cjs`. A non-Python kit instance (`.lab/lab.toml` present) that changes `.go`, `.java`, or `.rb` files exits 0 without running evals. The I-4 fix added the `.lab/lab.toml` trigger but left the extension filter. Within iteration-1 scope (only Python instances supported), this is low risk; it becomes relevant in iteration 2 when non-Python projects may appear.
- File: `lab/plugin/hooks/eval_gate.sh:23`

**3. `brand_denylist.txt` is empty — brand guard enforces nothing**
`python3 lab/engine/brand_guard.py` reports: *"empty denylist — nothing to enforce."* The CP-5 checklist item `just check-brand` passes trivially. The denylist is populated per-mission by design; the enforcement mechanism is correct but inert for the kit repo itself until names are added.
- File: `lab/engine/brand_denylist.txt:1`

---

## ❌ Blockers

None found in the deliverable code. All 222 tests pass. The trajectory guard violations above require Owner acknowledgment before merge but are run-history artifacts, not code defects.

---

VERDICT: WARN