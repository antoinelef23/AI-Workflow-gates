# Review CP-6 — panel of 1 — aggregated verdict: BLOCK (BLOCK)

## Panelist 1 — claude-opus-5-5 — lens: full review
VERDICT: BLOCK

# CP-6 review: policy vertical slice (T16, T17, T18, T19)

I reviewed `90b19d7..9216282`: 4 commits, 14 files, +1008/−6, against spec 0.6.0 (BHV-3/3a/3b/3c, INV-2/3/5/7, EX-1, EVAL-3), design 0.5.0 (ADR-13/14/16) and the T16–T19 prompts in `tasks.md`.

## ✅ Conformant
- **Traceability:** each commit's subject `[IDs]` tag matches its `Spec-IDs:` trailer, and each matches the task's `implements`. Each commit changes only its own `files_touched` plus its own status line in `tasks.md`. Each has a `Why:` body.
- **T16, the profile data:** the per-key tables in `lab/engine/policy_profiles.toml:6-69` match the BHV-3 table exactly. `goldfish_min_score` is declared with no value, as asked. `test_eval_3_profile_table_equals_bhv3` checks this.
- **T16, the policy rules:** both EX-1 inputs give the exact message and origins (`policy.py:111-113`, `test_eval_3_policy.py:48,54`).
  - An unknown key, including one under `[overrides.routes]`, is refused (`policy.py:93-98`), per BHV-3b.
  - Setting R2–R5 to `auto` is refused (`policy.py:122-125`), per BHV-3c and INV-3. Routes are flagged "applied from iteration 3".
  - No key concerns the merge (INV-5).
- **T16, `lab policy`** (`cli.py:51-66`): prints one line per key with value and origin, and returns rc 1 on `PolicyError` or `LabTomlError`. I ran it on the kit, `examples/booking` and `examples/devis`: all three show squad, origin `floor`.
- **T17:** `.lab/lab.toml` is tracked with `kit_version = "0.1.0"` and `profile = "squad"`. All three test sandboxes write one.
- **T19, plan-lint** (`planlint.py:114-161`):
  - each of the three plan-time keys is enforced;
  - the longest-chain check stops at checkpoints and names the offending path;
  - done tasks are skipped;
  - with `policy=None` nothing changes.
  - The rule that a final/merge checkpoint is never `auto` (INV-5) still sits outside the policy code (`planlint.py:324-327`), so no key can relax it. Tests cover it in all three profiles.
- **T18, the engine:**
  - The policy is resolved once, after `--project`, before pre-flight and before the lock (`orchestrate.py:1047-1056`). `--validate` ignores the refusals.
  - It refuses to start when `.lab/lab.toml` is missing, on a `PolicyError`, when `sandbox_required` is true without `LAB_RUNNER=sandbox`, and when `--force` is used with `allow_force` false.
  - The three engine constants are now read from the policy, and `LAB_BUDGET_USD` still wins when set (`orchestrate.py:262-271`). This follows ADR-14.
  - The plan-lint call receives the policy, and `run_start` records the profile and the effective policy.
- **Quality:**
  - `ruff check` is clean and `ruff format --check` passes.
  - No secrets and no orphan TODOs.
  - `uv run pytest tests/orchestrator tests/fde_kit tests/sdlc_rework` gives **261 passed**; the three EVAL-3 modules give **46 passed**.
  - `orchestrate.py work/fde-kit --validate` reports no errors under the kit's own squad policy.

## ❌ Blocker
- **`lab/engine/policy.py:65-68` (`_looser`, `strict = "true"` / `"false"`):** a yes/no safety key is refused when the override **equals** the floor. The test is "is the value the strict one", not "is it looser than the floor". This breaks the T16 rule ("stricter or equal is accepted") and INV-2 (the effective value is the stricter of floor and override, so equal is fine). Confirmed by running it:
  - `solo` + `sandbox_required = false` → `PolicyError: sandbox_required=false is looser than floor 'solo' (false)`
  - `solo` + `allow_force = true` → `allow_force=true is looser than floor 'solo' (true)`
  - `squad` + `auto_checkpoints_allowed = true` → same kind of refusal.

  **Effect:** a solo or squad instance that writes its floor value explicitly gets rc 1 from `lab policy` and is refused at engine start, with an error message that contradicts itself. It fails closed, so no safety hole, but a valid config is rejected.

  **Why the tests missed it:** `test_eval_3_equal_to_floor_accepted` (`test_eval_3_policy.py:63`) only tries a numeric key on `regulated`.

  **Fix:** for `"true"`, flag looser only when `floor is True and value is False`; mirror that for `"false"`. Add an equal-to-floor test for each yes/no key on `solo`. This goes back to T16 only; T17–T19 don't need rework.

## ⚠️ To arbitrate (non-blocking)
- **`orchestrate.py:1179`:** the "Budget reached" message still blames `(LAB_BUDGET_USD)`, even when the cap now comes from the policy's `budget_usd`. The message is misleading, though the behaviour is correct.

## Not verified here
- `just gate-ci`, `just check-content`, `just check-trajectory`: I didn't run them; the engine runs those gates.
- The manual CP-6 checks are Owner actions: EX-1 on a temp instance, `--dry-run` on a `regulated` instance, and the mandatory engine restart before T20.

## Proposed OQs
- **OQ (free-key ranges):** BHV-3 gives no valid range for free keys, and the code accepts anything numeric.
  - `max_parallel = 0` passes the policy check, then `ThreadPoolExecutor(max_workers=0)` raises `ValueError` (`orchestrate.py:1207`).
  - `max_task_attempts = 0` means no task is ever attempted.
  - A negative `budget_usd` is accepted.

  Proposal: require ≥ 1 for `max_parallel`, `max_task_attempts` and `max_cp_rejects`, and ≥ 0 for `budget_usd`, rejected as a `PolicyError`.

VERDICT: BLOCK