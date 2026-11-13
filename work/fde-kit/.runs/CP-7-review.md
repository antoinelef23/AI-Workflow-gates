# Review CP-7 — panel of 3 — aggregated verdict: WARN (WARN, WARN, PASS)

## Panelist 1 — claude-opus-5-5 — lens: correctness: does the code do what the spec says (INV/BHV), values and bounds included
VERDICT: WARN

# CP-7 review: iteration-2 merge, correctness lens (T16–T22)

The policy work matches the spec, including the values and bounds. I found one real gap in INV-5: in the `solo` and `squad` profiles, `--force` can still let the merge checkpoint approve itself. It is older than iteration 2, but this checkpoint covers INV-5, so you need to rule on it. The verdict is WARN, not BLOCK.

The EVAL-3, sandbox and pre-flight suites pass (85 passed). Plan-lint on `work/fde-kit` with the `squad` policy gives warnings only, all for evals planned in later iterations.

## ✅ Conformant
- **The profile table matches the spec.** `lab/engine/policy_profiles.toml:8-69` has every key, all three profiles, the strict directions, and `goldfish_min_score` left undeclared. The docs table at `docs/reference/policy-profiles.md:20-29` matches too.
- **EX-1 is exact.** I ran both inputs: the first is refused with `min_reviewers=1 is looser than floor 'regulated' (2)`; the second gives `min_reviewers` (override) and `max_parallel=4` (override, free key) (`policy.py:133-137`).
- **Safety keys can be tightened but not loosened (INV-2, CP-6 fix).** A value equal to the floor is accepted for each yes/no key; I checked all three on `solo` and on `squad` (`policy.py:83-94`). `regulated` with `sandbox_required=false` or `allow_force=true` is refused.
- **Unknown keys (BHV-3b) and route overrides (BHV-3c).** An unknown key is refused (`:114-119`). An unknown route such as R8 is refused, `R3=auto` is refused, and `R6=human` is accepted and marked "applied from iteration 3" (`:139-148`).
- **Free-key bounds (BHV-3d).** `max_parallel=0`, `max_parallel=2.0` and `budget_usd=-0.5` are refused with the key, the value and the bound in the message (`policy.py:62-80`).
- **`lab policy`.** It prints one line per key with its value and origin, and exits 1 on an error (`cli.py:51-66`). On the kit it shows the `squad` floor.
- **Run start (T18).** Pre-flight runs before the lock and is skipped for `--validate`. These are all refused with exit 1 (`orchestrate.py:311-336`, `:1141-1147`):
  - a missing `.lab/lab.toml`, with a message naming `lab init <project> --profile <p>`;
  - a policy error;
  - `sandbox_required` without `LAB_RUNNER=sandbox`;
  - `--force` when `allow_force` is false.
- **Engine settings read the policy.** Attempts, parallel tasks and checkpoint rejections now come from the policy, and `LAB_BUDGET_USD` still overrides the budget when set (`:340-348`). Attempt counting is unchanged: `range(1, N+1)` (`:824`). The `run_start` journal event records the profile and the full policy (`:1239-1247`).
- **Plan-lint (T19).** It enforces the auto-checkpoint, minimum-reviewer and tasks-between-checkpoints rules from the policy, skips tasks already done, and behaves as before with no policy (`planlint.py:114-161`, `:329-330`).
- **Sandbox for an external instance (T20).** The instance is mounted read-write at `/workspace` and the kit read-only at `/kit` (`sandbox_runner.py:121-123`). The plugin and settings paths point into `/kit`, and extra directories outside the kit are refused (`orchestrate.py:234-277`, `:287-289`, `:413-418`). The prompts no longer contain host paths (`:631-636`, `:957`). The old refusal of sandbox plus external instance is gone.
- **Versions (T17, T21).** Version 0.2.0 is the same in `pyproject.toml`, `plugin.json`, the marketplace entry and `uv.lock`. The kit's own `.lab/lab.toml` and both examples' are pinned to 0.2.0.

## ⚠️ For you to decide
1. **INV-5: `--force` can let the merge checkpoint approve itself.**
   - Plan-lint correctly flags a merge checkpoint in `mode: auto` (`planlint.py:323-327`).
   - But `orchestrate.py:1182` (`if errors and not args.force`) ignores every lint error under `--force`. At run time, `:1020` then approves any checkpoint in `mode: auto` once evals are green and the reviewers say PASS, with no separate check for the merge checkpoint.
   - `allow_force` is true in both the `solo` and `squad` profiles. So in those two profiles a profile key does open a path to an automatic merge, which INV-5 forbids.
   - Design I-23 (`design.md:86`) records the decision that `--force` ignores lint errors and that `allow_force=false` closes that door. It does not reconcile this with INV-5. The behaviour dates from the initial commit 09d1e53.
   - Suggested fix: make the run-time check refuse an automatic merge checkpoint independently of lint.
2. **BHV-3d: NaN passes the budget bound** (`policy.py:79`). `budget_usd = nan` is accepted because `nan < 0` is false. The engine then treats it as no cap, since `nan` is truthy and `cost >= nan` is always false (`orchestrate.py:1268`). It is minor, but NaN is not "≥ 0", so this misses the spec's bound.

## Outside T16–T22 (but in the diff against main)
- **a2a282c (wave settling).** At the start of a wave only the first `MAX_PARALLEL` tasks are registered as active (`orchestrate.py:1302`). With a wave larger than that, a queued task can start editing while a sibling's verify step is checking the shared tree, which is the situation this fix was meant to stop. It does not apply to this plan.

## Not verified here
- **The live `regulated` run in the Docker sandbox:** I couldn't run Docker in this session (the call needed approval), so ADR-15 and INV-1 are only checked at the argv level.
- **`just gate-ci`, `just check-content work/fde-kit` and `just check-trajectory work/fde-kit`:** not run.

## Proposed open questions
- **OQ (BHV-3 safety-key types and bounds).** Today, on `regulated`:
  - `min_reviewers = 2.5` is accepted;
  - `max_tasks_between_checkpoints = 0` or `-4` is accepted as "stricter", which makes every plan fail lint;
  - `goldfish_min_score = -1` is accepted.

  Should the safety keys require whole numbers, and should they have absolute bounds or a range, as BHV-3d gives the free keys?

VERDICT: WARN

---

## Panelist 2 — claude-opus-4-8 — lens: spec/design conformance: traceability, scope, ADR compliance, no scope creep
VERDICT: WARN

Review complete. Here is the dossier.

---

# CP-7 Reviewer Report — fde-kit iteration-2 merge (T16–T22)

**Lens:** spec/design conformance — traceability, scope, ADR compliance, no scope creep.
**Base:** iteration-1 merge `b64b227` → `HEAD 5cea212`. Working tree clean.

## ✅ Conformant

**Traceability (checklist 1).** Every task commit carries the subject `[IDs]` tag, a `Why:` body, and `Spec-IDs:` / `Artifacts:` / `Run:` trailers: T16 `d9240fc`, T17 `35e3ad7`, T18 `9216282`, T19 `e53f7b9`, T20 `0c2374c`, T22 `a3951cd`, T21 `5cea212`/`2cf51a8`. Plan-lint on the feature is **error-free** (0 ❌); the only ⚠️ are EVAL-4..7/9/10..14 "carried by no task" — iteration 3-4 EVALs, explicitly declared expected in the tasks.md scope note. EVAL-1/2/3/8 are all carried.

**T16 — policy data + module (ADR-13, BHV-3/3a/3b/3c/3d, INV-2/3).**
- `policy_profiles.toml:8-69` reproduces the BHV-3 table **exactly** (kind, strict direction, and solo/squad/regulated for all 10 keys incl. `goldfish_min_score` declared-without-value).
- `policy.py:135` emits EX-1's message verbatim (`<key>=<v> is looser than floor '<profile>' (<floor>)`); unknown key `:116`, routes `auto` refused on R2–R5 `:144-147` (INV-3), free-key bounds `:62-80` (BHV-3d), equal-to-floor accepted `:86-93` (the CP-6 rework). **EVAL-3 policy module: 71 passed overall.**

**T19 — plan-lint safety keys (ADR-14, I-21, INV-5).** `planlint.py:_policy_lint` enforces `auto_checkpoints_allowed`, `min_reviewers`, `max_tasks_between_checkpoints` (names the path); `policy=None` ⇒ unchanged; done tasks not re-linted. The pre-existing final/merge-CP-auto rule (`planlint.py:326`) is kept and no key can relax it (INV-5). ✅

**T18 — engine/pre-flight read the policy (ADR-14/16).** `orchestrate.py:311-348` resolves the policy once after `--project`; refusals for missing `.lab/lab.toml` (names `lab init … --profile`, via `lab_init.py:66`), `sandbox_required`, `allow_force`; `MAX_EVAL_RETRIES/MAX_PARALLEL/MAX_CP_REJECTS/BUDGET_USD` become policy reads with `LAB_BUDGET_USD` winning; `run_start` journal carries profile + policy `:1239-1247`. Correctly gated to real runs + `--dry-run`, never `--validate` `:1142/1209`. ✅

**T20 — external-instance sandbox (ADR-15, E-17).** `sandbox_runner.py` mounts the kit at `/kit:ro`; `orchestrate.py:234-287` translates in-kit `--add-dir` to `/kit/…` and refuses other host paths; the ADR-10 "not supported before iteration 2" refusal is removed; kit mode unchanged. ✅

**T17/T21 — self-instance + version bump (ADR-16, INV-7, I-19).** Kit `.lab/lab.toml` tracked (`profile=squad`); test sandboxes write one. Version `0.2.0` consistent across pyproject / plugin.json / marketplace / all three `.lab/lab.toml`; `test_kit_root.py` rebased from a literal to a manifest-consistency check (plan delta `614d1c1`, recorded). ✅

**T22 — docs only.** `policy-profiles.md` + `choose-an-organization-profile.md` exist and are linked from `docs/README.md`; the commit touches only its declared doc files (+ a run-log line). No code leak. ✅

**Amendment discipline.** BHV-3d entered via a **separate** spec commit `cfc6de3` with version bump 0.6.0→0.7.0 + Owner approval, triggered by the CP-6 rejection — exactly the "stop, amend, resume" flow. Coherence pass `45c2062` updated the `# version :` pointers; design 0.5.0 / tasks 0.2.0 / spec 0.7.0 are consistent, **no version drift**. `brand_guard` clean.

## ⚠️ To arbitrate (Owner)

1. **Out-of-plan engine-semantics change folded into the iteration-2 range** — `a2a282c` `fix(engine): a parallel wave judges each task on a settled tree…` (`orchestrate.py`, `+tests/orchestrator/test_parallel_wave_isolation.py`). It is correctly typed as an engine lab-fix (no Spec-IDs, `Run: owner`, Why + regression tests), not a feature task, and does not contradict spec/design — but it changes wave scope-registration and verify-timing semantics and rides into the 0.2.0 merge outside the T16–T22 task set. Its Why also notes a stray SIGINT auto-commit (`a00a6f3`) was rewritten into it. Confirm you want these engine semantics in the merge. Not a blocker.

## Not verified here (information, not deviations)

- **The mandatory live `regulated` Docker run** (CP-7 review item: `LAB_RUNNER=sandbox lab run … --project <instance>`, kit `/kit:ro`). Docker is unavailable to me and no in-repo artifact evidences it. By ADR-15 this is argv-tested only (`test_sandbox_external.py`, no Docker) and the real run is explicitly the Owner's checkpoint action — **please run it before the tag.**
- **Full `just gate-ci` / `examples-gate` / `check-content` / `check-trajectory`** — the `just` recipes were not runnable here (shell approval). I confirmed EVAL-3 (71 passed), plan-lint (0 errors), and brand_guard (clean) directly; the engine runs the rest mechanically.
- `reviewer.md` 1.2.0 (`8479c4c`) + its scorecard are in the range but are an EVOLUTION-loop agent change, not a CP-7 task — properly governed, noted for completeness.

## ❌ Blockers

None established.

---

The reviewed feature code (T16–T22) is conformant with spec 0.7.0 and design 0.5.0; traceability and ADR anchoring hold and EVAL-3 is green. One out-of-plan engine change and the un-evidenced live Docker run are worth your eye at this human final checkpoint.

VERDICT: WARN

---

## Panelist 3 — claude-sonnet-4-6 — lens: edge cases & robustness: extreme inputs, errors, does the deliverable actually run
VERDICT: PASS

I now have enough evidence to produce the report. Let me compile it.

---

## CP-7 Review Report — Checkpoint: iteration-2 merge (human, final) + live regulated run

**Feature:** `work/fde-kit` | **Tasks:** T16, T17, T18, T19, T20, T21, T22 | **Lens:** edge cases & robustness

---

### ✅ Conformant points

**T16 — `policy.py` / `policy_profiles.toml` / `lab policy` [BHV-3, BHV-3a..d, INV-2, INV-3, EVAL-3]**

- ✅ `policy_profiles.toml:1–51` — schema_version=1, all BHV-3 keys present with correct `kind`/`strict`/values; `goldfish_min_score` declared without profile values (undeclared), consistent with spec.
- ✅ `policy.py:83–94` (`_looser`) — equal-to-floor accepted for all `strict` directions; CP-6 rejection corrected.
- ✅ `policy.py:63–80` (`BOUNDS`, `_check_bounds`) — BHV-3d: `max_task_attempts`/`max_parallel`/`max_cp_rejects` require int ≥ 1; `budget_usd` requires number ≥ 0; bound 0.0 and 1 exactly accepted.
- ✅ `policy.py:55–59` (`_check_type`) — bool rejected for numeric free keys; type derived from profile sample, not hardcoded.
- ✅ `policy.py:107–148` — `[overrides]` / `[overrides.routes]` non-dict input raises `PolicyError`; unknown key refused; R2/R3/R4/R5 `auto` refused (INV-3); R6 `human` accepted; routes returned with "applied from iteration 3" note.
- ✅ `policy.py:103–105` — missing/unknown `profile` raises `PolicyError`.
- ✅ EVAL-3 policy suite: 71 tests green (`uv run pytest -q -m eval tests/fde_kit/test_eval_3_policy.py`).

**T17 — `.lab/lab.toml` fixtures [BHV-3, INV-7]**

- ✅ `.lab/lab.toml`, `examples/devis/.lab/lab.toml`, `examples/booking/.lab/lab.toml` all pinned `kit_version = "0.2.0"`, `profile = "squad"`.
- ✅ `tests/fde_kit/test_kit_lab_toml.py` passes (2 tests).
- ✅ Sandbox fixtures write `.lab/lab.toml` so T18 policy checks do not break existing tests.

**T18 — engine + pre-flight read the effective policy [BHV-3, EVAL-3]**

- ✅ `orchestrate.py:1141–1147` — `resolve_policy` called once after `--project`, before preflight; policy refusals block real runs and `--dry-run` but not `--validate`.
- ✅ `orchestrate.py:339–348` (`apply_policy`) — MAX constants read from policy; `LAB_BUDGET_USD` env wins over policy (ADR-14).
- ✅ `orchestrate.py:1242–1246` — `run_start` journal event carries `profile` and effective policy (key, value, origin).
- ✅ EVAL-3 engine suite: green (`tests/fde_kit/test_eval_3_engine.py`).

**T19 — plan-lint applies safety keys [BHV-3, INV-5, EVAL-3]**

- ✅ `planlint.py:114–161` (`_policy_lint`) — `auto_checkpoints_allowed`, `min_reviewers`, `max_tasks_between_checkpoints` enforced; already-done tasks excluded.
- ✅ `planlint.py:324–326` — final/merge CP never `auto`, in every profile including `solo` (INV-5).
- ✅ EVAL-3 planlint suite: 16 tests green, INV-5 tested across all 3 profiles.

**T20 — external-instance sandbox [BHV-3, INV-1]**

- ✅ `sandbox_runner.py:122–123` — kit mount inserted before `-w`; order `workspace:rw`, `kit:ro` verified by `test_docker_argv_external_mounts_instance_rw_and_kit_ro`.
- ✅ `sandbox_runner.py:72–129` (`build_docker_argv`) — `kit` parameter: exactly 1 `:ro` mount at `/kit`.
- ✅ `sandbox_runner.py:179` — `add_dirs` forwarded only when `kit_mount` given (external), suppressed in kit mode.
- ✅ `orchestrate.py:412–418` — `add_dirs=[str(LAB)]` translated to `/kit` via `translate_add_dirs`; `kit_mount=LAB` passed to runner.
- ✅ `orchestrate.py:266–277` (`translate_add_dirs`) — paths outside kit raise `SandboxPathError`; `ValueError` from `relative_to` caught.
- ✅ `orchestrate.py:287–292` (`guardrail_options`) — `/kit/lab/plugin` and `/kit/lab/engine/run_settings.json` in sandboxed external mode.
- ✅ Pre-flight refusal "sandbox + external not supported" removed; test updated (`test_external_sandbox_preflight_no_longer_refuses`).
- ✅ No host path leaks verified by `test_external_sandbox_run_mounts_kit_ro_and_uses_kit_paths` (no-Docker shim, argv inspection).
- ✅ All 23 sandbox + preflight tests green.

**T21 — kit 0.2.0 + re-pin [INV-7]**

- ✅ `pyproject.toml`, `lab/plugin/.claude-plugin/plugin.json`, `.lab/lab.toml`, both examples' `.lab/lab.toml` all say `0.2.0`.
- ✅ T21 verify: 11 tests green (`test_eval_8_examples`, `test_kit_lab_toml`, `test_lockfile`).
- ✅ Note: two T21 commits (`2cf51a8` the version bump, `5cea212` the run-log update to tasks.md); both carry `Run: owner`. The split is the orchestrator's auto-commit for the run log — a recorded pattern, not a deviation.

**T22 — docs: profiles, `lab policy` [BHV-3]**

- ✅ `docs/reference/policy-profiles.md` exists, BHV-3 table present with all keys and enforcement points.
- ✅ `docs/how-to/choose-an-organization-profile.md` exists, INV-5 and INV-3 cited explicitly.
- ✅ Doc-pointer test green (2 tests); brand guard: nothing to enforce (empty denylist).

**Quality**

- ✅ `uv run ruff check .` — all checks passed (89 files).
- ✅ `uv run ruff format --check .` — 89 files already formatted.
- ✅ Full suite (297 tests): all pass.
- ✅ No orphan TODO/FIXME/HACK in T16–T20 deliverables.
- ✅ Commit subjects carry `[Spec-IDs]` tags and `Spec-IDs:` trailers for all tasks.
- ✅ `Why:` body present in all T16–T21 commits.

---

### Not verified here

- **Live Docker regulated run** (CP-7 blocking criterion: `LAB_RUNNER=sandbox lab run <f> --project <instance>`) — no Docker host available in this session. The argv construction is unit-tested without Docker (`test_sandbox_external.py`), but the end-to-end container execution (image, network, actual container isolation) is the Owner's live check.
- **`just gate-ci`** — `just` not available in this environment. The underlying test suites and lock check pass individually.
- **`just check-content work/fde-kit`** and **`just check-trajectory work/fde-kit`** — not runnable here. Content guard: empty denylist, no names to check; trajectory guard has its own test suite (green).
- **plan-lint warnings** — `--validate` surfaced 3 warnings: `EVAL-10/11/12 declared in spec.md §7 but carried by no task`. These are expected (tasks.md §Coverage header states future-iteration EVALs are uncarried — plan-lint warns, as designed).

---

### Proposed OQs

None. No spec ambiguity was found that the code resolved beyond the spec.

---

VERDICT: PASS