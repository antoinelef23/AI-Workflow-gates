# Review CP-6 — panel of 1 — aggregated verdict: WARN (WARN)

## Panelist 1 — claude-opus-5-5 — lens: full review
VERDICT: WARN

# CP-6 review, second pass: policy vertical slice (T16, T17, T18, T19)

This pass covers `90b19d7..d9240fc` against spec 0.7.0 (BHV-3/3a/3b/3c/3d, INV-2/3/5/7, EX-1, EVAL-3), design 0.5.0 and tasks 0.2.0. Since the first pass (`bcab2e5`, BLOCK), three commits landed: spec 0.7.0 (`cfc6de3`), the coherence pass and plan delta (`45c2062`), and the T16 rework (`d9240fc`). Since `9216282`, only `lab/engine/policy.py` and `tests/fde_kit/test_eval_3_policy.py` changed in `lab/` and `tests/`. The first pass's ✅ findings for T17, T18 and T19 still hold.

## ✅ Conformant
- **The previous blocker is fixed** (`lab/engine/policy.py:86-89`). A yes/no safety key is now refused only when the floor is the strict value and the override is the opposite one. I re-ran the three cases that failed before:
  - `solo` + `sandbox_required=false` is accepted, with origin `override`.
  - `solo` + `allow_force=true` is accepted, with origin `override`.
  - `squad` + `auto_checkpoints_allowed=true` is accepted, with origin `override`.
- **Real loosening is still refused (INV-2, BHV-3a).** `regulated` + `sandbox_required=false`, `allow_force=true` or `auto_checkpoints_allowed=true` each give rc 1 with a correct message. EX-1 (`min_reviewers=1` on `regulated`) still gives the exact expected message. A value equal to the floor is accepted on `min_reviewers` and `max_tasks_between_checkpoints`.
- **BHV-3d bounds are in place** (`policy.py:62-80`, called at `:130`). Each refusal names the key, the value and the bound. I checked:
  - `max_parallel=0` and `max_task_attempts=-3` are refused.
  - `max_parallel=2.0` is refused, as the spec asks for integers.
  - A value of `true` is caught earlier by `_check_type` (`:51-59`). Without that, `bool` would pass the integer check.
  - `budget_usd=-0.01` is refused, `0` is accepted, and `1` is accepted for each integer key.
- **The tests match the plan delta** (`test_eval_3_policy.py:179-239`). They cover equal-to-floor for each yes/no key on `solo` and `squad` (and on `regulated` too), and each BHV-3d bound, both refused and accepted.
- **The plan delta followed the amendment process** (`45c2062`). The `# version :` pointers in `design.md` and `tasks.md` moved to 0.7.0, and BHV-3d is added to T16 and to the coverage matrix. The spec amendment is its own commit, with a version bump and an entry in the history table.
- **Traceability.** The subject of `d9240fc` matches its `Spec-IDs:` trailer and T16's updated `implements`. The commit touches only T16's `files_touched` plus its status line in `tasks.md`, and its `Why:` body records why T16 was reworked.
- **Quality.**
  - `ruff check` and `ruff format --check` are clean.
  - `pytest tests/orchestrator tests/fde_kit tests/sdlc_rework` gives **286 passed**.
  - T16's own verify command gives **43 passed**.
  - `orchestrate.py work/fde-kit --validate` reports 0 errors.
  - No secrets and no orphan TODOs.

## ⚠️ To arbitrate
1. **`lab/engine/policy.py:79`: `budget_usd = nan` passes the BHV-3d check.** `nan < 0` is False, so the value is accepted. The engine then never caps spending: `BUDGET_USD` is truthy, and `COST >= nan` is always False (`orchestrate.py:271`, `:1177`). NaN does not satisfy "≥ 0", so this goes against the letter of BHV-3d. It needs a deliberate `nan` written in the TOML, and the key is a free key, not a safety key, so the risk is low. A one-line fix would be `math.isfinite(value)` or `not value >= minimum`.
2. **`lab/engine/orchestrate.py:1179`: still open from the first pass, and not decided in the CP-6 rejection.** The "Budget reached" message still blames `(LAB_BUDGET_USD)`, even when the cap comes from the policy's `budget_usd`. The behaviour is correct; only the message misleads.

## Not verified here
- I did not run `just gate-ci`, `just check-content`, `just check-trajectory` or `just check-brand`; running them needed approval. The engine runs these gates.
- The manual CP-6 checks are Owner actions:
  - EX-1 on a temporary instance;
  - `--dry-run` on a `regulated` instance;
  - **the mandatory engine restart before T20.** The running engine still holds the plan as it was before the delta.

## Proposed OQs
- **OQ (budget_usd upper end):** BHV-3d gives only a lower bound, so `budget_usd = inf` is accepted and means "no cap", the same as `0`. Should the spec require a finite number?

VERDICT: WARN