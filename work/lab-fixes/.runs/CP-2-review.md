# Review CP-2 — panel of 2 — aggregated verdict: BLOCK (BLOCK, PASS)

## Panelist 1 — claude-opus-5-5 — lens: correctness: does the code do what the spec says (INV/BHV), values and bounds included
VERDICT: BLOCK

# CP-2 review (merge): correctness lens, T1–T6

I found one ❌ blocker. The interrupt does not cover the checkpoint review panel, so INV-1 can be broken at a checkpoint with 2 reviewers, and CP-2 is one. Everything else matches the spec. The 30 `tests/lab_fixes` tests pass, and ruff check and format are clean on `lab/engine` and `tests/lab_fixes`.

## ❌ Blocker

**INV-1 / BHV-1: a reviewer agent turn can start after the interrupt** (`lab/engine/orchestrate.py:1063`, the loop in `run_review` at 1052–1079)
- `run_review` starts one reviewer agent per panelist in a loop. It never checks `STOP` inside that loop, and `run_claude` (`orchestrate.py:449`) has no check either.
- `wait_checkpoint` only checks `STOP` before and after the whole panel (`orchestrate.py:1126-1130`).
- The signal handler's helper calls `terminate_all()` once (`orchestrate.py:198-202`). The 0.2 s loop that keeps killing late launches only runs during a task wave (`orchestrate.py:1462-1465`), and the main thread is inside `run_review` here.
- **Scenario:** a checkpoint with `reviewers: 2` (CP-2 of this plan), SIGINT while panelist 1 is running.
  1. Panelist 1 is killed.
  2. Its empty result becomes a `WARN` and a `review` event is journaled.
  3. The loop then starts panelist 2. That is a new, billed agent turn after the interrupt, which INV-1 forbids ("MUST NOT … start any agent turn").
  4. Nothing kills that turn, so it runs to the end.
  5. `.runs/CP-x-review.md` is then overwritten with the partial panel.
  6. Only after that does the run exit with rc 130.
- **Why EVAL-1 misses it:** it tests an interrupt while waiting for the checkpoint's approval token (`tests/lab_fixes/test_eval_1_interrupt.py:203-227`), not during the review panel.
- **Fix:** add `if STOP.is_set(): break` (or return `"interrupted"`) at the top of the panelist loop, plus one EVAL-1 case: interrupt during a 2-reviewer panel ⇒ one reviewer turn only, rc 130, the checkpoint stays `pending`.
- **Not a recorded decision:** I found no `Why:` in the branch's commits or the CP-1/CP-2 reviews that scopes the review panel out of INV-1.

## ✅ Matches the spec

- **BHV-1 / BHV-1a / INV-1, task path:**
  - Every agent process starts in its own process group and is tracked while it runs (`runner.py:59-87`).
  - On interrupt: SIGTERM to every group, then SIGKILL after the grace period (`runner.py:89-104`), and `kill_all_now` plus `os._exit(130)` on a second signal (`orchestrate.py:205-213`).
  - `STOP` is checked before each agent turn, after it, after verify and the eval gate, and right before `scoped_commit` (`orchestrate.py:918-999`).
  - Queued tasks are cancelled and late launches are killed (`orchestrate.py:1461-1465`).
  - `finish_interrupted` writes state atomically, journals `run_interrupted` with the in-flight list and the signal, prints how to resume, and returns 130 (`orchestrate.py:1393-1410`).
- **BHV-1b:** a task waiting for its Owner signature returns `interrupted_waiting` and is left out of `inflight` (`orchestrate.py:825-826`, `1472-1473`). A waiting checkpoint makes the run exit through `finish_interrupted([])` (`orchestrate.py:1489-1490`).
- **BHV-1c:** the approval token is consumed when honoured (`orchestrate.py:1218-1221`). An interrupt after the signature returns `interrupted` and the task stays `pending` (`orchestrate.py:836-841`); EVAL-1 checks that a new signature is required on restart.
- **Plan delta (task never started):** a task stopped before its first turn returns `not_started`, never `interrupted` (`orchestrate.py:878-879`, `921-924`), and `test_eval_1_interrupt_queue.py` covers it.
- **BHV-2 / INV-2 (dry run):** `journal()` does nothing in a dry run (`orchestrate.py:267-268`). `.runs/` is only created by a real run (`orchestrate.py:1354-1357`). In a dry run, `run_review` returns before writing its report (`orchestrate.py:1045-1047`).
- **BHV-3 / INV-3 (commit trailers):**
  - `Artifacts:` is now computed from the paths actually staged, after golden files outside the task's scope are un-staged (`orchestrate.py:603-612`).
  - Renamed files list both the old and the new path (`--no-renames`), which was the cause of the earlier CP-2 rejection.
  - The line is inserted before `Run:` (`orchestrate.py:618-628`), and `_commit_message` no longer emits `Artifacts:`.
  - EVAL-3 covers task commits, Owner-lane commits, the run-log-only case (EX-2) and renames.
- **BHV-5 (budget message):** the source of the cap is resolved when the policy is applied, and `override (free key)` is shortened to `override` (`orchestrate.py:396-403`). EX-3 is asserted exactly (`test_eval_5_budget.py:48-50`).
- **BHV-6 / INV-5 (scorecard stamps):** the default stamp is `<date>-<layer>`, with `-2`, `-3`… added while the `.md` already exists (`eval_models.py:334-342`). An explicit `--stamp` is used as given (`eval_models.py:484`).
- **BHV-4 / INV-4 (gate):** `gate` now depends on `lint-check` (`justfile:107`), and `lint` is documented as the explicit fixer (`justfile:52`).
- **BHV-7 (docs):** the recipe comment is positional (`justfile:39-41`), README, `docs/how-to/evaluate-models.md` and EVOLUTION.md were fixed, and EVAL-7 guards them.

## Not verified here

- I did not run `just gate-ci`, `just check-content work/lab-fixes` or `just check-trajectory work/lab-fixes`.
- I did not run a live Docker interrupt. The `docker run --rm` container being removed together with its process group is design risk 1, to be checked at the iteration-3 Docker run.
- Commits T3 (`ee844aa`, `3c5eb4e`) and T6 (`009939b`) were written by an engine started before T3's trailer fix, so their own `Artifacts:` lines still follow `files_touched`. This was noted earlier (`d10f294`) and NG-4 keeps old trailers as they are.

## Proposed OQ

- **OQ-4:** if the interrupt lands after an Owner signature but before its verify starts (`orchestrate.py:836`), the task is listed in `inflight`. The glossary says a task is in-flight once its judging has started, so a strict reading would leave it out. Should a signed-but-not-yet-checked Owner-lane task count as in-flight? The current behaviour (listed) is defensible, so this is for the Owner to decide, not a code deviation.

VERDICT: BLOCK

---

## Panelist 2 — claude-opus-4-8 — lens: spec/design conformance: traceability, scope, ADR compliance, no scope creep
VERDICT: PASS

All delta-scoped test changes match the documented OQ-1/OQ-2 plan deltas exactly. I have everything I need for the conformance report.

---

# CP-2 Reviewer Report — merge checkpoint (lab-fixes)

**Lens:** spec/design conformance — traceability, scope, ADR compliance, no scope creep.
**Base:** `origin/main` (`54fecfc`) → `HEAD` (`3c5eb4e`). 27 files, +2217/−136.

## Traceability ✅

- Every spec ID is mapped to a task and an eval in the coverage table (`work/lab-fixes/tasks.md:19-29`); BHV-1..7, INV-1..5, EVAL-1..7 all accounted for.
- Engine commits carry the canonical shape — subject `type(feature): title [IDs]`, mandatory `Why:`, `Spec-IDs:`, `Artifacts:`, `Run:` (e.g. T1 `52015e8`, T3 `3c5eb4e`).
- The `Artifacts:` trailer on the T3 rework commit (`3c5eb4e`) lists exactly its three staged paths — the feature proving its own INV-3 on itself.
- The two spec amendments (0.2.0 OQ-1/OQ-2, 0.3.0 BHV-1c/OQ-3) are separate `docs` commits with version bumps and coherence passes, and the `# version :` pointers in design.md/tasks.md agree (spec 0.3.0, design 0.1.0). `content_guard` confirms substance is unchanged since the last bump for both spec and design ✅.

## ADR compliance ✅

- **ADR-1** tracked launcher — `run_tracked` / `terminate_all` / `kill_all_now` in `lab/engine/runner.py:54-131`; both runners route through it (`runner.py:268`, `sandbox_runner.py:195`).
- **ADR-2** interrupt = stop flag + drain, never a commit — `STOP` event + `_on_signal` + `_begin_shutdown` (`orchestrate.py:114-219`); `STOP` checked before/after each turn and before every commit (`orchestrate.py:920-998`); wave loop cancels queued futures and drains (`orchestrate.py:1454-1480`).
- **ADR-3** journal no-op in dry run — `orchestrate.py:266-268`; `.runs/` mkdir moved under `not args.dry_run` (`orchestrate.py:1354`) → INV-2.
- **ADR-4** trailers computed after staging — `_commit_message` no longer emits `Artifacts:` (`orchestrate.py:699`); `scoped_commit` reads staged paths and appends the trailer (`orchestrate.py:603-612`).
- **ADR-5** gate uses non-mutating lint — `justfile:107` `gate: lint-check …`.
- **ADR-6** budget source + dated stamps — `BUDGET_SOURCE` (`orchestrate.py:100`, `398-404`, message `:1420`); `default_stamp` (`eval_models.py:329-339`, `:484`).
- **ADR-7** positional `eval-models` everywhere — README, docs, EVOLUTION.md, justfile comment all converted.

## Scope — no creep ✅ (two notes ⚠️)

- All `files_touched` fall inside declared task scopes. The three edits to pre-existing tests (`tests/test_runner.py`, `tests/fde_kit/test_sandbox_external.py`, `tests/fde_kit/test_eval_8_examples.py`) match the OQ-2 and OQ-1 plan deltas verbatim (stub moved to `run_tracked`; closed `work/` set replaced by a no-demo-feature assertion).
- NG-3 (no policy/profile/checkpoint semantics), NG-4 (no history rewrite) respected. No new workflow capability (NG-1).

⚠️ **`progress.md` (+334, `156b493`/`3ef38a1`)** is not in any task's `files_touched`. It is the session-handoff / lab-fix batch tracker that spec §1 references, updated in `docs` commits — legitimate bookkeeping, not a feature deliverable, but it rides along into the merge. No conformance issue.

⚠️ **Budget message** (`orchestrate.py:1420`) appends `Restart after review …` beyond EX-3's literal `expected_output` (which ends at "stopping before the next wave."). That trailing sentence pre-dates this feature; EX-3 is illustrative of the *source-naming* requirement (BHV-5), and EVAL-5 is green. Non-blocking.

## Prior CP-2 rejection — resolved ✅

Rejection (2026-11-13 19:46): *Artifacts trailer misses renamed source paths — add `--no-renames` and an EVAL-3 rename case.* Fix in `3c5eb4e`: `--no-renames` added to both `git diff --cached` reads (`orchestrate.py:567`, `:605`) and `test_eval_3_rename_lists_both_source_and_destination` added (`tests/lab_fixes/test_eval_3_trailers.py:104`).

## Gate evidence ✅

- `tests/lab_fixes` evals: **23 passed**, 7 deselected.
- Affected suites (lab_fixes + orchestrator + runner + sandbox + eval_8): **175 passed**.
- `ruff check` + `ruff format --check`: clean (non-mutating). `content_guard` spec+design: substance identical. `trajectory_guard work/lab-fixes`: OK, 0 warnings (no dry-run noise). `brand_guard --all`: clean. `check-lock`: n/a (no new dep).

## Verdict

The diff conforms to spec 0.3.0 and design 0.1.0: traceability intact, every technical choice anchored to an ADR, no scope creep, the prior rejection closed, all evals and guards green. The merge itself remains the Owner's human action (CP-2 is `mode: blocking`, final human checkpoint).

VERDICT: PASS