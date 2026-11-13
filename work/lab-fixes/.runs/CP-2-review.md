# Review CP-2 — panel of 2 — aggregated verdict: WARN (WARN, PASS)

## Panelist 1 — claude-opus-5-5 — lens: correctness: does the code do what the spec says (INV/BHV), values and bounds included
VERDICT: WARN

## CP-2 review: `lab-fixes` (correctness lens, T1–T6)

I read the code diff from `54fecfc` to `HEAD` against spec 0.3.0 and design 0.1.0. `uv run pytest -q tests/lab_fixes`: **29 passed**. No commit's recorded `Why:` contradicts the findings below.

### ✅ Matches the spec

- **BHV-1 / INV-1 (interrupt), T1 and T2**
  - The SIGINT/SIGTERM handler raises `STOP` and kills the agent process groups from a helper thread (`lab/engine/orchestrate.py:198-218`).
  - `STOP` is checked before each agent turn, after it, after settling, after verify, after the gate, and immediately before `scoped_commit` (`orchestrate.py:921-999`).
  - Queued futures are cancelled, `terminate_all` runs again every 0.2 s, and the shutdown waits for the workers (`orchestrate.py:1454-1480`).
  - On exit, in-flight tasks are set back to `pending` and the state write is atomic. Exactly one `run_interrupted` event is journaled with `inflight` and `signal`, the resume command is printed, and the exit code is 130 (`orchestrate.py:1393-1410`).
  - Every group is killed with SIGTERM, then SIGKILL after the grace period, children included, and the code waits on the whole group, not just the leader (`lab/engine/runner.py:89-126`). The timeout keeps its old message (`runner.py:267-272`, `sandbox_runner.py:195-211`).
- **BHV-1a:** a second signal calls `kill_all_now()` and then `os._exit(130)` (`orchestrate.py:212-215`). State is only ever written atomically.
- **BHV-1b:** a checkpoint or Owner-lane wait returns `interrupted` / `interrupted_waiting` (`orchestrate.py:825-826`, `:1126-1133`, `:1188-1189`). The node stays `pending` and is not added to `inflight` (`:1471-1473`, `:1489-1490`). A task that never started returns `not_started` and is not added to `inflight` either (`:878-879`, `:921-925`).
- **BHV-1c:** if the run is interrupted after the Owner signs, the task returns `interrupted` (`orchestrate.py:836-841`). The token was already renamed to `.handled-*` (`:1221-1223`), so a restart waits for a new signature.
- **BHV-2 / INV-2 (dry run):** `journal()` does nothing in a dry run (`orchestrate.py:265-268`). `mkdir .runs`, the lock and `save()` only run on a real run (`:1354-1361`). The dry-run review path writes nothing (`:1045-1047`).
- **BHV-3 / EX-2 (commit trailers):** `Artifacts:` is built from the staged paths after the golden-file un-staging, sorted, and placed before `Run:` (`orchestrate.py:603-627`). `_commit_message` no longer adds it (`:699-703`). The run-log `tasks.md` is included because the feature directory is staged.
- **BHV-4 / INV-4:** `gate: lint-check …` (`justfile:107`), and `lint` is documented as the explicit fixer (`justfile:52`).
- **BHV-5 / EX-3:** the cap's source is `LAB_BUDGET_USD` when set, otherwise `budget_usd, <origin>`, with "override (free key)" shortened to "override" (`orchestrate.py:396-403`, `:1420`). The message is exact up to "…next wave." and the pre-existing resume sentence follows it.
- **BHV-6 / INV-5:** the default stamp is `<date>-<layer>`, suffixed `-2`, `-3`… while the `.md` exists. An explicit `--stamp` is used as given (`lab/engine/eval_models.py:329-342`, `:484`).
- **BHV-7:** no `key=value` invocation is left in README, `docs/**`, `EVOLUTION.md` or the `justfile` comments. `docs/reference/cli.md:178` shows the recipe's signature, not a call, and also gives the positional form.

### ⚠️ Deviations for the Owner to decide

- **INV-3 / BHV-3: a renamed file leaves a path out of `Artifacts:`** (`lab/engine/orchestrate.py:605-611`)
  - The trailer comes from `git diff --cached --name-only`, which has rename detection on by default. A staged rename only lists the new path.
  - I checked this in a throwaway repo: after `a.txt → b.txt` was staged, `--name-only` gave `b.txt` and `--no-renames` gave `a.txt, b.txt`.
  - So a task that renames or moves a file inside its `files_touched` produces a commit that deletes `a.txt` with a trailer that doesn't list it. INV-3 says "no more, no fewer".
  - EVAL-3 doesn't test this case.
  - Fix: add `--no-renames` to that call, plus an EVAL-3 case for a rename.

### Not verified here

- I ran `tests/lab_fixes` only, not `tests/orchestrator`, `just gate-ci`, `just check-content work/lab-fixes` or `just check-trajectory work/lab-fixes`.
- I didn't do a live Docker or `claude` interrupt. Design §8 leaves that check to the iteration-3 run.

### Notes (not deviations)

- There is a tiny race: a worker can pass its last `STOP` check just before the signal and then launch an agent that the handler's snapshot misses. The main loop's repeated `terminate_all()` (`orchestrate.py:1461-1464`) and the one in `finish_interrupted` (`:1396`) kill it within about 0.2 s, and it can never commit.
- A commit already under way when the signal arrives is allowed to finish, as the design accepts in §8.

VERDICT: WARN

---

## Panelist 2 — claude-opus-4-8 — lens: spec/design conformance: traceability, scope, ADR compliance, no scope creep
VERDICT: PASS

I have a complete picture. All artifacts read, full diff reviewed against the ADRs, traceability verified, scope swept, and the merge gate exercised live. Here is the dossier.

---

# CP-2 Merge Review — `work/lab-fixes` (T1–T6)
**Lens:** spec/design conformance — traceability, scope, ADR compliance, no scope creep.
**Base:** `54fecfc` (PR #2 merge, pre-feature) → `HEAD ee844aa`. 25 files, +1849/−53.

## ✅ Conformant

**Traceability** — every task commit uses the canonical subject `type(feature): title [IDs]`, a `Why:` body, and `Spec-IDs:`/`Run:` trailers; IDs match each task's `implements`:
- T1 `52015e8` [BHV-1, INV-1] · T4 `4052e13` [BHV-4, INV-4, BHV-7, EVAL-4] · T5 `211b04a` [BHV-6, INV-5, EVAL-6] · T2 `787be0e` [BHV-1,1a,1b,1c, INV-1, EVAL-1] · T6 `009939b` [BHV-7, EVAL-7] · T3 `ee844aa` [BHV-2, INV-2, BHV-3, INV-3, BHV-5, EVAL-1/2/3/5].
- Spec amendments are separate commits with `Version-Bump:` trailers (`55ca955` 0.2.0→0.3.0; `fd13a0d` 0.1.0→0.2.0) and coherence passes (`ac26b3a`, `d637605`); `version :` pointers in design/tasks read 0.3.0/0.1.0. OQ-1/OQ-2/OQ-3 resolved by the Owner and recorded.

**ADR compliance** — each technical choice traces to its ADR:
- **ADR-1** `runner.py:42-131` — `run_tracked` (`Popen(start_new_session=True)`, locked registry, group-kill on timeout re-raising), `terminate_all` (SIGTERM→grace→SIGKILL, waits on the group not the leader), public `kill_all_now` (plan delta c). Both runners route through it; sandbox keeps `docker run --rm` (`sandbox_runner.py:195`).
- **ADR-2** `orchestrate.py:198-219, 1393-1409, 1454-1480` — handler on main thread only appends + spawns a drain thread (E-1), `STOP` polled before turn/after turn/before commit, `cancel_futures` (E-3), atomic `save` (I-1), one `run_interrupted{inflight,signal}`, resume print, rc 130, `os._exit(130)` on 2nd signal (BHV-1a). BHV-1b `interrupted_waiting` (`:825`, `:1489`) keeps waiting nodes out of `inflight`; BHV-1c re-sign (`:836, :841`); never-started tasks `not_started` (`:878, :925`).
- **ADR-3** `orchestrate.py:266-268` journal no-op in dry run; `.runs/` mkdir guarded `:1354` (INV-2).
- **ADR-4** `orchestrate.py:603-630` trailers computed from `git diff --cached --name-only`, sorted; `_commit_message` no longer emits `Artifacts:` (INV-3/BHV-3).
- **ADR-5** `justfile:107` `gate: lint-check …`; `lint` documented as the explicit fixer (`:52`).
- **ADR-6** `orchestrate.py:100, 392-402` budget source; `eval_models.py:329-344, 484` dated stamp + `-2/-3` collision suffix.
- **ADR-7** README/`docs/how-to/evaluate-models.md`/EVOLUTION.md + justfile comment all positional (`just eval-models all 1`); EVOLUTION.md touched only on the command line (scaffolding preserved).

**Scope — no creep.** Every changed file is in the union of T1–T6 `files_touched`, plus the three artifacts and `work/lab-fixes/.runs/CP-1-review.md` (the CP-1 review dossier — a feature review record, not spec code). No NG item touched (NG-1/2/3 untouched; NG-4 honored). The OQ-1/OQ-2 deltas (`test_eval_8_examples.py`, `test_sandbox_external.py`, `test_runner.py`) are inside the Owner-approved scope extensions.

**Merge gate (run live):**
- `pytest -m eval tests/lab_fixes` → **22 passed**. Full suites `tests/lab_fixes tests/orchestrator tests/test_runner.py` + touched fde_kit tests → **174 passed**.
- `ruff check` + `ruff format --check` (engine + lab_fixes) → clean. Brand guard → clean (empty denylist).
- Feature journal (untracked) shows real-run events only — no dry-run noise.

## ⚠️ For the Owner (conformance note — not a code deviation)

- **Transitional trailers on the feature's own post-CP-1 commits.** T3 `ee844aa` staged `work/lab-fixes/tasks.md` but its `Artifacts:` trailer omits it and is not sorted (`…test_eval_1_interrupt_queue.py` last = `node.files` order); T6 `009939b` staged `CP-1-review.md` + `tasks.md`, trailer lists neither. **Cause:** the engine executing the plan was restarted once at CP-1 on T2's code — *before* T3's ADR-4 trailer fix existed — so the commits that introduce the fix cannot themselves use it (bootstrap). This is **documented** (`f5c11d9` Why: "the T1–T5 Artifacts trailers miss tasks.md: the INV-3 defect T3 fixes, produced by the pre-T3 engine"), **protected by NG-4** ("old commits keep their trailers; history is never rewritten"), and the **delivered code is correct** — EVAL-3 verifies exact sorted staged-path trailers on commits made by the new engine, and design §7 scopes the fix to iteration 3 forward ("must be exact *first*"). Per the git-archaeology rule, a choice justified in a prior `Why:` is conformant, not a finding. Flagged only so the Owner merges with eyes open.

## Not verified here
- Live hardware interrupt / stray-process check and `just gate`/`gate-ci` end-to-end were exercised at CP-1 (validated `16:08`); I ran the eval suites and lint directly rather than the `just` wrappers (recipe multi-op approval), with equivalent coverage.

No established deviation of the reviewed code: every ADR is implemented, every INV/BHV is covered and eval-locked, scope is clean, gates are green. The one trailer observation is a documented, NG-4-protected bootstrap property, not a defect. CP-2 is `mode: blocking` — the merge remains a human action.

VERDICT: PASS