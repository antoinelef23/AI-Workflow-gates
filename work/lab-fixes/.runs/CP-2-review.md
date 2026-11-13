# Review CP-2 — panel of 2 — aggregated verdict: WARN (WARN, WARN)

## Panelist 1 — claude-opus-5-5 — lens: correctness: does the code do what the spec says (INV/BHV), values and bounds included
VERDICT: WARN

# Review CP-2 (merge, final): lab-fixes, T1 to T6. Lens: correctness

I checked the full diff against `origin/main` (27 files) and the commit history. I ran `uv run pytest -q tests/lab_fixes tests/orchestrator tests/test_runner.py tests/fde_kit/test_eval_8_examples.py tests/fde_kit/test_sandbox_external.py`: **176 passed**. `ruff check` and `ruff format --check` on `lab/engine` and `tests/lab_fixes` are both clean.

## ✅ Conformant

- **INV-1 / BHV-1 (interrupt):**
  - The SIGINT/SIGTERM handler sets `STOP` from a helper thread and calls `terminate_all` (`lab/engine/orchestrate.py:198-218`).
  - Workers check `STOP` before each agent turn, after it, after verify and after the eval gate. The last check is right before `scoped_commit` (`:921-1000`).
  - Queued futures are cancelled and `terminate_all` runs again on every 0.2 s poll (`:1466-1484`).
  - `finish_interrupted` writes in-flight tasks back as `pending` (done tasks keep `done`), saves state atomically (I-1), journals exactly one `run_interrupted` event with `signal`, prints how to resume and returns 130 (`:1397-1415`).
  - EX-1 is asserted exactly for both signals (`tests/lab_fixes/test_eval_1_interrupt.py:146-172`).
- **BHV-1a:** a second signal calls `kill_all_now()` then `os._exit(130)` (`orchestrate.py:212-214`). `runner.kill_all_now` is public, as the CP-1 delta asked (`lab/engine/runner.py:108`). Tested under 4 s.
- **BHV-1b:**
  - An interrupted Owner-lane wait returns `interrupted_waiting` (`orchestrate.py:825`), and a never-started task returns `not_started` (`:878`, `:921-925`). Neither is listed in `inflight` (`:1476-1477`).
  - A checkpoint wait returns at once through `STOP.wait(20)` (`:1233`), and the checkpoint stays `pending`.
  - Tested for a checkpoint, an Owner-lane wait and a queued task (`test_eval_1_interrupt_queue.py:42-70`).
- **BHV-1c:** `_await_token` consumes the approval token (renamed to `.handled-*`, `:1222-1224`) before returning. Interrupts are caught by the checks at `:836` and `:840`, so a signature is never reused. The test re-signs and gets exactly one commit (`test_eval_1_interrupt.py:265-303`).
- **CP-2 rejection 2 (review panel):** no reviewer turn starts and no report is written after `STOP` (`orchestrate.py:1055`, `:1066`, `:1130-1137`). This is tested with a 2-reviewer panel (`test_eval_1_interrupt.py:312-339`).
- **INV-2 / BHV-2 (dry run):** `journal()` does nothing in a dry run (`:266-268`). `.runs/` is only created in a real run (`:1358-1361`). The review and checkpoint dry-run branches return before writing anything. Byte-identical and still-absent cases are both tested.
- **INV-3 / BHV-3 (`Artifacts:` trailer):**
  - The trailer is computed after the golden un-staging, using `--no-renames` (CP-2 rejection 1). It is sorted, deduplicated and placed before `Run:` (`:603-628`).
  - `_commit_message` no longer emits `Artifacts:` (`:699-703`).
  - Tested for task, Owner-lane, run-log-only (the EX-2 shape) and rename cases.
  - The `work/lab-fixes/.runs/CP-2-review.md` path in the trailer of commit c9a44e4 is correct under INV-3: `scoped_commit` stages the whole feature directory, which predates this feature (`:561`).
- **BHV-5 (budget message):**
  - With `LAB_BUDGET_USD` set, the source is `LAB_BUDGET_USD`.
  - Otherwise it is `budget_usd, <origin>`, and `override (free key)` is shortened to `override` (`:398-403`). The possible origins are `floor`, `override` and `override (free key)` (`lab/engine/policy.py:25-27`).
  - The EX-3 string is matched exactly.
- **INV-4 / BHV-4 (gate):** `gate: lint-check test evals check-brand check-lock` (`justfile:107`), and `lint` is documented as the explicit fixer (`justfile:52`).
- **INV-5 / BHV-6 (scorecard stamps):** the default stamp is `<YYYY-MM-DD>-<layer>`, with `-2`, `-3`… added while the `.md` exists, and an explicit `--stamp` is used as given (`lab/engine/eval_models.py:334-342`, `:484`). The EX-4 names match exactly.
- **BHV-7 (docs):** the `eval-models` commands are now positional in `README.md:145`, `docs/how-to/evaluate-models.md:60,70`, `lab/models/EVOLUTION.md:35` and the `justfile` comment. EVAL-7 is green.
- **Commit traceability:** every T1 to T6 commit has an `[IDs]` subject tag, a `Why:` body and `Spec-IDs` / `Artifacts` / `Run` trailers. The rework commits record the CP-2 rejection reason they answer.

## ⚠️ To arbitrate

1. **A narrow race can let an agent turn start after the interrupt and escape `terminate_all`, mainly in the review panel** (`lab/engine/runner.py:65-76`, `lab/engine/orchestrate.py:1055-1065`).
   - The handler does not set `STOP` itself; it starts a helper thread that does (`orchestrate.py:217`). This is on purpose, to avoid a deadlock in handler context.
   - So between the last `if STOP.is_set()` and `_TRACKED.add(p)` inside `run_tracked`, a signal can arrive and the agent can still be launched. If `terminate_all` takes its snapshot before `_TRACKED.add`, that process is never signalled.
   - **Wave workers:** the main loop calls `terminate_all()` every 0.2 s while workers drain (`:1471`), so a late process is still killed within about 0.2 s.
   - **Review panel:** it runs on the main thread and nothing re-signals. A reviewer turn launched in that window runs to completion (up to `TASK_TIMEOUT_S`) before the interrupt finishes.
   - **Effect:** no commit is made and nothing survives exit, but INV-1 ("no agent turn starts") and BHV-1 ("terminates the running agent processes") are not met to the letter in that window.
   - **Suggested fix:** a flag in `runner`, set by `terminate_all` / `kill_all_now`. `run_tracked` would check it right after registering and kill the group immediately.
   - I found this by reading the code; I did not reproduce it. The window is microseconds to milliseconds.

## Not verified here

- `just check-content work/lab-fixes` and `just check-trajectory work/lab-fixes`: I was not allowed to run them in this session. Both are CP-2 review items.
- `just gate-ci` as a whole.
- `just gate` on a seeded drift in the real repo. EVAL-4 covers this on a temp project.
- A live interrupt with the Docker sandbox: whether `docker run --rm` removes the container when its client's process group is killed (design §8 risk, scheduled for the iteration-3 run).

## Proposed OQ

- **OQ (in-flight definition, BHV-1c):** if the interrupt hits after the Owner-lane token is consumed but before verify starts (`orchestrate.py:836`), the task is listed in `inflight`. By the glossary it is not in flight yet, because no judging has started. The task still goes back to `pending` and a new signature is required, so BHV-1c holds either way. The question is only whether a signed task that has not been judged belongs in `run_interrupted.inflight`. The spec does not say, and the window is tiny.

VERDICT: WARN

---

## Panelist 2 — claude-opus-4-8 — lens: spec/design conformance: traceability, scope, ADR compliance, no scope creep
VERDICT: WARN

# Reviewer Report — CP-2 (merge, final) · Feature `work/lab-fixes`
**Lens:** spec/design conformance — traceability, scope, ADR compliance, no scope creep.
Tasks covered: T1–T6. Spec 0.3.0 / design 0.1.0 / tasks 0.1.0.

## Traceability
- ✅ Every ADR (ADR-1..7) is implemented and anchored to the file the design named:
  - ADR-1 tracked launcher → `lab/engine/runner.py:52-128` (`run_tracked`, `terminate_all`, public `kill_all_now` per the CP-1 delta); both runners route through it (`runner.py:268`, `sandbox_runner.py:195`).
  - ADR-2 stop-flag + drain → `orchestrate.py:198-219` (`_begin_shutdown`/`_on_signal`/`install_signal_handlers`), worker STOP polls at every seam, `wait(cancel_futures=True)` loop `orchestrate.py:1458-1483`, rc 130 `finish_interrupted`.
  - ADR-3 journal no-op in dry run → `orchestrate.py:266-268` + `DRY_RUN` guard on `.runs/` mkdir `orchestrate.py:1358`.
  - ADR-4 trailers after staging → `_commit_message` drops `Artifacts:` (`:699`), `scoped_commit` computes it from staged paths `orchestrate.py:603-612`.
  - ADR-5 `gate: lint-check …` → `justfile:107`, `lint` re-documented as the explicit fixer.
  - ADR-6 budget source + dated stamps → `BUDGET_SOURCE` `orchestrate.py:100,398-406`; `default_stamp` `eval_models.py:333-339`.
  - ADR-7 positional docs + test → `README.md`, `docs/how-to/evaluate-models.md`, `EVOLUTION.md`, `justfile:39-41`.
- ✅ Final commits carry correct Spec-IDs; CP rejection history (tasks.md Run log) is complete and each rejection has a matching follow-up commit.
- ⚠️ **tasks.md:21** — the Coverage table row still reads `BHV-1, BHV-1a, BHV-1b, INV-1`; **BHV-1c is missing** though T2 implements it (tasks.md:127) and EVAL-1 covers it. Coherence gap left over from the spec 0.3.0 amendment. Cosmetic — does not affect code or evals.

## Scope / no scope creep
- ✅ Engine/test/doc edits all fall within the declared `files_touched`, including the two approved plan deltas: OQ-2 (`tests/test_runner.py`, `tests/fde_kit/test_sandbox_external.py` stub → `run_tracked`) and OQ-1 (`tests/fde_kit/test_eval_8_examples.py` closed-set → brand-name assertion).
- ✅ `--no-renames` fix for INV-3 (CP-2 rejection 19:46) and the review-panel STOP guards for INV-1 (`run_review` `orchestrate.py:1055,1066`; CP-2 rejection 20:47) are both in T3/T2 scope.
- ✅ `progress.md` and `work/lab-fixes/.runs/CP-*-review.md` are session bookkeeping / reviewer dossiers, committed as `docs(lab-fixes)` — outside the 3-artifact deliverable, no engine substance. Not creep.
- ✅ Non-goals respected: no new workflow capability, no policy/profile/checkpoint-semantics change, no history rewrite (NG-1..4).

## ADR / design discipline
- ✅ No invented architecture: stdlib-only (`signal`/`subprocess`/`threading`/`concurrent.futures`), every seam anchored to I-1..I-8 / E-1..E-4 as design §2 prescribes. BHV-1b (`interrupted_waiting`) and BHV-1c (re-sign, consumed token never reused) are implemented as the resolved OQ-3 requires (`orchestrate.py:825,836,841`).

## Gate / eval status (merge conditions)
- ✅ `uv run pytest -m eval tests/lab_fixes`: **24 passed**.
- ✅ Broader suite (`tests/lab_fixes tests/test_runner tests/fde_kit/{sandbox_external,eval_8_examples} tests/orchestrator`): **176 passed**.
- ✅ `ruff check` + `ruff format --check` on changed files: clean (confirms BHV-4/INV-4 — `lint-check` would hold).
- ⚠️ **`lab/engine/brand_denylist.txt` is empty**, so `check-brand` currently enforces nothing. Pre-existing bootstrap state, **not** introduced by this feature, but the merge dossier should not read its green `check-brand` as proof the de-branding is enforced.

## Minor notes (non-blocking)
- ⚠️ `progress.md` TL;DR lists lab-fix item `18` while spec §1 intent lists `5, 16, 21, 22, 28, 29, 31` (no 18). Tracking-doc discrepancy, outside the contract.

## Assessment
Substance conforms fully: all seven ADRs implemented as designed, scope and non-goals respected, both prior CP-2 rejections (renamed-path trailer, review-panel interrupt) genuinely fixed, evals and lint green. The open items are cosmetic documentation/traceability gaps (coverage table missing BHV-1c; inert brand denylist; progress.md item list) — none touch an invariant or behavior. I surface them so the Owner sees them before signing; none blocks the merge.

VERDICT: WARN