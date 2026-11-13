# Review CP-7 — panel of 3 — aggregated verdict: PASS (PASS, WARN, PASS)

## Panelist 1 — claude-opus-5-5 — lens: correctness: does the code do what the spec says (INV/BHV), values and bounds included
VERDICT: PASS

# CP-7 review: iteration-2 merge, correctness lens (T16–T22)

Both problems that sent CP-7 back are now fixed in the code. The merge checkpoint can no longer approve itself under `--force` (INV-5), and `budget_usd` must now be a finite number (BHV-3d, spec 0.8.0). I found no new deviation in T16–T22. The live `regulated` run in Docker is still not done, and it remains your job before the tag.

## ✅ Conformant

**The rework**
- **INV-5 now holds at run time.** The fix is `lab/engine/orchestrate.py:1013-1017` and `:1043-1047`, wired in at `:1341-1347`.
  - `is_merge_checkpoint` uses the same rule as plan-lint (`lab/engine/planlint.py:322-327`): a checkpoint is a merge checkpoint if no task depends on it, or if its title contains "merge". It looks at every node parsed from `tasks.md` (`orchestrate.py:1178`).
  - A merge checkpoint marked `mode: auto` skips the automatic approval and always waits for a signed human approval. This holds whatever the profile, and even under `--force`, which still skips lint errors at `:1210`.
  - In `regulated`, `--force` is already refused before the run starts (`allow_force=false`).
  - The tests match the plan delta: `tests/fde_kit/test_eval_3_engine.py` runs a final checkpoint in `solo` and in `squad`, plus a checkpoint titled "merge" that other tasks still depend on. In each case the approval honoured is the human one, not one marked "auto-approved".
- **BHV-3d requires a finite budget.** `lab/engine/policy.py:79-80` uses an explicit `math.isfinite` test, because `nan < 0` is false. The error message names the key, the value and the bound ("must be a finite number >= 0"). `nan`, `inf` and `-inf` are all tested.
- **The amendment process was followed.** The spec change is its own commit `88815e0` (0.7.0 → 0.8.0, with an Owner line in `validated_by` and a changelog entry). The coherence pass `0129834` moves the version pointers in `design.md` and `tasks.md` to 0.8.0, and the plan deltas on T16 and T18 are recorded. The rework commits carry `[IDs]`, a `Why:` and `Spec-IDs` (T18 now includes INV-5).

**Unchanged since the first CP-7 pass (re-checked)**
- The profile table in `lab/engine/policy_profiles.toml` matches the spec.
- EX-1 gives the exact message: `policy.py:133-136`.
- A value equal to the floor is accepted for every safety key: `policy.py:86-97`.
- BHV-3b and BHV-3c refusals: `policy.py:114-119` and `:139-148`.
- The integer bounds ≥ 1 for the other free keys: `policy.py:62-80`.
- The run-start checks: `orchestrate.py:336-349`.
- The engine settings read from the policy: `orchestrate.py:355-362`.
- The plan-lint policy rules (T19).
- The kit mounted read-only for an external instance (T20).
- Version 0.2.0 consistent everywhere (T17, T21).

**Gates I ran myself**
- `uv run pytest`: 316 passed, of which `tests/fde_kit` is 159.
- `ruff check` and `ruff format --check`: clean.
- `orchestrate.py work/fde-kit --validate`: no errors (❌).
- `brand_guard`: nothing flagged, but its denylist file is empty.

## ⚠️ For you to decide
None in T16–T22.

## ❌ Blockers
None.

## Not verified here
- **The live `regulated` run in Docker** (`LAB_RUNNER=sandbox lab run … --project <instance>`, with the kit mounted read-only at `/kit`). Docker is not available in this session, so ADR-15 and INV-1 are only tested by checking the arguments passed to Docker. This is your action at this checkpoint.
- **`just gate-ci`, `check-content` and `check-trajectory`:** I didn't run the `just` recipes. I ran their pytest, ruff and plan-lint steps directly.

## Proposed open questions
- **OQ (carried over, still open): types and bounds for the safety keys.** On `regulated`, `min_reviewers = 2.5` is accepted, and `max_tasks_between_checkpoints` = 0 or -4 is accepted as "stricter". Should these keys require whole numbers and have absolute bounds, as BHV-3d gives the free keys?
- **OQ: the `LAB_BUDGET_USD` environment variable.** It overrides the policy (`orchestrate.py:359-360`) but is not bounds-checked, so `LAB_BUDGET_USD=nan` still means no cap. BHV-3d only covers overrides in `lab.toml`, so this is outside the spec as written. Should the variable get the same "finite, ≥ 0" check?

VERDICT: PASS

---

## Panelist 2 — claude-opus-4-8 — lens: spec/design conformance: traceability, scope, ADR compliance, no scope creep
VERDICT: WARN

Review complete. Here is the dossier.

---

# Review CP-7 (re-review after the INV-5/budget rework) — lens: spec/design conformance (traceability · scope · ADR compliance · no scope creep) — tasks T16–T22

This is the second pass on CP-7. The first pass (committed `work/fde-kit/.runs/CP-7-review.md`, panel verdict WARN) raised two issues; the Owner rejected and reopened **T18** (INV-5 run-time hole) and **T16** (NaN budget). I reviewed the two rework commits — `15a0a29` (T16) and `c639094` (T18) — against the spec, the design, and the Owner-approved plan deltas, and re-checked the iteration-2 slice as a whole.

## ✅ Conformant

- **INV-5 hole is closed at run time (T18).** `is_merge_checkpoint()` (`orchestrate.py:1013-1017`) mirrors the plan-lint test exactly — sink of the graph *or* `"merge"` in the title (cf. `planlint.py:322-324`). `wait_checkpoint()` now takes `merge` and, when `mode == "auto" and merge`, only notifies and falls through to `_await_token()` — it never writes an auto-approval token, **regardless of `--force`, mode, or `allow_force`** (`orchestrate.py:1043-1047, 1080-1085`). This is exactly the spec contract (INV-5, `spec.md:91`) and the Owner's plan delta (`tasks.md:750-756`). The call site passes the flag (`:1341-1347`).
- **Tested in `solo` and `squad` as the delta requires (T18).** `test_eval_3_merge_cp_never_auto_approved_under_force` is parametrized over both profiles, runs with `--force` + green evals + reviewer PASS, and asserts the honored token is the pre-placed human approval, not `auto-approved` (`test_eval_3_engine.py:218-235`); a second test covers the merge-*titled* non-sink case (`:238-253`).
- **BHV-3d budget is now finite (T16).** `_check_bounds` adds an explicit `math.isfinite` check with the comment `nan < 0 is False` (`policy.py:80-81`), message wording changed to `a finite number >= 0` — matching spec 0.8.0 (`spec.md:179-181`). Parametrized over `nan`, `inf`, `-inf` (`test_eval_3_policy.py:242-246`).
- **EVAL-3 suites green.** I ran `pytest -m eval` on `policy`, `planlint`, `engine` → **77 passed**.
- **Traceability.** Both rework subjects carry the `[IDs]` tag and a `Spec-IDs:` trailer matching their `implements`; `Why:` bodies record the CP-7 rejection. T17/T19/T20/T21/T22 commits likewise reference valid IDs (`[BHV-3, INV-7]`, `[BHV-3, INV-5, EVAL-3]`, `[BHV-3, INV-1]`, `[INV-7]`, `[BHV-3]`).
- **No scope creep.** Each rework touched only its declared `files_touched` + `tasks.md` run-log (`15a0a29`, `c639094`).
- **Version coherence (INV-7, T21).** `0.2.0` identical in `pyproject.toml`, `plugin.json`, `marketplace.json`, `uv.lock`; `kit_version = "0.2.0"` pinned in the kit's and both examples' `.lab/lab.toml`.
- **Version-pointer coherence pass.** spec `0.8.0`; `design.md:8` and `tasks.md:8-9` both point to spec `0.8.0`; brand guard clean (empty denylist).

## ⚠️ For the Owner to arbitrate

1. **Design lags the code on where INV-5 is enforced.** The run-time guard adds a **second** INV-5 enforcement point (`wait_checkpoint`, `orchestrate.py:1043`), but the design still describes INV-5 as plan-lint-only: I-21 (`design.md:84`) says INV-5 "has no key" and is protected by plan-lint, and ADR-14 (`:331-346`, I-23 `:86`) frames `--force`/`allow_force` as the only door — it does not record that the merge CP is now refused at run time independently of lint. The code is correct and Owner-approved (plan delta `tasks.md:750-756`), so this is **not** a code deviation — but under the "anchored design" rule a new enforcement mechanism should be reflected in the design. Suggest a short design note/ADR touch before tagging `v0.2.0`, so the "why" of the two-point INV-5 enforcement lives in the design, not only in the rejection history.

## Not verified here

- **The live `regulated` Docker run** (CP-7 requires `LAB_RUNNER=sandbox lab run … --project <instance>`, kit mounted read-only). Docker needs approval in this session; ADR-15/INV-1 are only checked at argv level (as in the first pass). This is the Owner's live-run gate.
- **`just gate-ci` / `just check-content` / `just check-trajectory`** — `just` recipes require approval; the engine runs them mechanically at the gate. (Brand guard and the EVAL-3 suites I did run directly.)

## Proposed OQ (carried forward, not a blocker)

- **Safety-key types/bounds** (from the first pass, out of the reopened scope): `min_reviewers = 2.5`, `max_tasks_between_checkpoints = 0`/`-4` (accepted as "stricter"), `goldfish_min_score = -1` are still accepted. The reworks were correctly scoped to the two rejection reasons only. Should safety keys require integers / absolute bounds, as BHV-3d now gives the free keys? For a future spec amendment.

---

Both blocking issues from the first pass are fixed, verified green, in-scope, and traceable. The one open item is a design/code coherence gap on the new INV-5 enforcement point — an Owner arbitration, not a code defect. CP-7 is the final human merge checkpoint (INV-5), so this surfaces for the Owner to decide alongside the `v0.2.0` tag.

VERDICT: WARN

---

## Panelist 3 — claude-sonnet-4-6 — lens: edge cases & robustness: extreme inputs, errors, does the deliverable actually run
VERDICT: PASS

I have reviewed all T16–T22 implementations, test suites, and commit history. Here is the report.

---

## CP-7 Review — T16, T17, T18, T19, T20, T21, T22

**Lens: edge cases & robustness — extreme inputs, errors, does the deliverable actually run**

---

### ✅ Conformant points

**T16 — `policy.py` / `policy_profiles.toml` / `lab policy`**

- `policy_profiles.toml` matches the BHV-3 table exactly: 10 keys, correct `kind`/`strict`/values per profile; `goldfish_min_score` declared with no profile values (undeclared) (`lab/engine/policy_profiles.toml:68-70`).
- `_looser` correctly guards equality: `strict = "true"` → looser only when floor is `true` and value is `false` (`policy.py:89-91`). CP-6's false-positive for equal-to-floor is gone.
- **BHV-3d / spec 0.8.0 (CP-7 delta)**: `_check_bounds` calls `math.isfinite` explicitly before the `< minimum` test (`policy.py:80`), with the comment `# nan < 0 is False: test explicitly`. `nan`, `inf`, `-inf` all raise `PolicyError`. Verified by `test_eval_3_bhv3d_budget_must_be_finite` (3 parametrized cases, all passing).
- Integer-only bounds for `max_task_attempts`, `max_parallel`, `max_cp_rejects` (≥ 1); `budget_usd` ≥ 0 finite number; `0` accepted as "no cap".
- Routes R2–R5 refuse `auto` (INV-3); unknown key refused; R6 `human` accepted.
- `lab policy` CLI correctly shows `value  (origin)` with routes marked `[applied from iteration 3]`.
- 77 `@pytest.mark.eval` tests for EVAL-3 (policy part): all pass.

**T17 — kit `.lab/lab.toml` + fixture writes**

- Kit's `.lab/lab.toml` tracked with `kit_version = "0.2.0"` and `profile = "squad"` consistent with the kit version (`test_kit_lab_toml.py`). All orchestrator test sandboxes write one.

**T19 — plan-lint safety keys**

- `_pv(policy, key)` correctly unwraps the `(value, origin)` tuple (`planlint.py:108-111`).
- `auto_checkpoints_allowed`, `min_reviewers`, `max_tasks_between_checkpoints` all enforced with `policy` parameter; `policy = None` leaves behaviour unchanged.
- **INV-5** existing rule (`planlint.py:324-326`) is separate from `_policy_lint` and applies in every profile including without a policy — verified by `test_eval_3_inv5_holds_without_policy_and_with_solo_override`.
- Longest-path algorithm correctly ignores checkpoints as boundaries and counts only non-done tasks (`planlint.py:139-160`); parallel branches are not summed.

**T18 — engine + pre-flight read the effective policy**

- Policy resolved once at startup, stored in module-global `POLICY` (`orchestrate.py:98`).
- Pre-flight: missing `.lab/lab.toml` → rc 1 naming `lab init … --profile`; `PolicyError` → rc 1 with error message; `sandbox_required=true` without `LAB_RUNNER=sandbox` → rc 1; `allow_force=false` with `--force` → rc 1 (`orchestrate.py:329-350`).
- `--validate` skips pre-flight; `--dry-run` does not.
- Motor constants (`MAX_EVAL_RETRIES`, `MAX_PARALLEL`, `MAX_CP_REJECTS`, `BUDGET_USD`) read from policy; `LAB_BUDGET_USD` env wins when set (`orchestrate.py:355-362`).
- `run_start` journal event carries `profile` and full effective policy with `{value, origin}` per key.
- **INV-5 at run time (CP-7 delta)**: `wait_checkpoint` with `merge=True` notifies "never auto-approved (INV-5)" and falls through to `_await_token`, bypassing the `auto → approve` branch entirely (`orchestrate.py:1043-1047`). `--force` is not passed to `wait_checkpoint`; it only skips plan-lint errors (`orchestrate.py:1210`). `is_merge_checkpoint` uses identical logic (sink or "merge" in title) to plan-lint (`orchestrate.py:1013-1017`). Tests in solo and squad: pre-approved human token is honoured, handled file does not say "auto-approved".

**T20 — external-instance sandbox: kit read-only**

- `build_docker_argv` with `kit` parameter appends `-v <kit>:/kit:ro` after the workspace mount (`sandbox_runner.py:123`).
- Engine passes `/kit/lab/plugin`, `/kit/lab/engine/run_settings.json`, `--add-dir /kit` for sandbox + external (`test_sandbox_external.py:163-166`).
- No host path leaks into the container's claude argv beyond the two bind-mount sources (`test_sandbox_external.py:168-170`).
- Kit mode: single workspace mount, cwd-relative paths unchanged.
- ADR-10 "not supported before iteration 2" refusal removed; test updated.
- `add_dirs` outside the kit root refused (`test_sandbox_external.py:214-218`).

**T21 — version 0.2.0 everywhere**

- `pyproject.toml`, `plugin.json`, marketplace entry, kit and both examples' `.lab/lab.toml` all pin 0.2.0. Verified by `tests/sdlc_rework/test_lockfile.py` + `test_eval_8_examples.py` + `test_kit_lab_toml.py` (13 tests, all pass). Lockfile fresh (`uv lock --check` green).

**T22 — docs**

- `docs/reference/policy-profiles.md` and `docs/how-to/choose-an-organization-profile.md` exist and are linked from `docs/README.md`. Content matches BHV-3 table exactly; enforcement points are correct. Routes note present. Brand guard: empty denylist (nothing to enforce). Doc-pointer test green.

**Gate checks**

- Ruff: 0 errors, 89 files already formatted.
- 125 `@pytest.mark.eval` tests: all pass.
- Traceability: all T16–T22 commits carry `Spec-IDs:` and `Artifacts:` trailers matching their scope; T18 and T16 final commits carry the CP-7 rework note.

---

### Not verified here

- **Live Docker run** with a `regulated` external instance (CP-7's specific review item requiring a real Docker daemon — designated as a human checkpoint action, not an automated test; the argv-only test suite covers it mechanically).
- `just check-content work/fde-kit` and `just check-trajectory work/fde-kit` (`just` not available in this review environment; `content_guard.py` and `brand_guard.py` ran without error directly).

---

### Proposed OQs

- **OQ-candidate**: `goldfish_min_score` accepts any finite non-negative number as an override (e.g., `1.5`). The spec specifies bounds only for the 4 free keys (BHV-3d) and is silent on bounding `goldfish_min_score` to `[0, 1]`. Since it represents a proportion, should a bound of `≤ 1` be enforced? (Not a code deviation — the code made no choice the spec forbids.)

---

VERDICT: PASS