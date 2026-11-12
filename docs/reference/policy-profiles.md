# Policy profiles reference

> Diátaxis: **reference**. Facts only. To pick a profile, see
> [choose-an-organization-profile.md](../how-to/choose-an-organization-profile.md).

An instance picks a **profile** (its *floor*) in `.lab/lab.toml`. It may **tighten** a safety key
and **tune** a free key through `[overrides]`; it can never loosen a safety key below the floor
(INV-2). The result is the **effective policy**, computed key by key and shown by
[`lab policy`](cli.md#lab-policy).

The profiles are data: `lab/engine/policy_profiles.toml` (`schema_version = 1`). Resolution lives
in `lab/engine/policy.py`.

## Keys

*Strict* is the direction in which a safety key is stricter. A free key has no direction.

| Key | Type · strict direction | `solo` | `squad` | `regulated` | Enforced by |
|---|---|---|---|---|---|
| `auto_checkpoints_allowed` | safety · `false` | true | true | false | plan-lint: error on a checkpoint with `mode: auto` |
| `min_reviewers` | safety · up | 1 | 1 | 2 | plan-lint: error when a checkpoint's `reviewers` is below the minimum |
| `max_tasks_between_checkpoints` | safety · down | 8 | 5 | 3 | plan-lint: error when a path of the graph has more tasks than this between two checkpoints |
| `sandbox_required` | safety · `true` | false | false | true | run start (pre-flight, rc 1): `LAB_RUNNER=sandbox` is required |
| `allow_force` | safety · `false` | true | true | false | run start (pre-flight, rc 1): `--force` is refused |
| `max_task_attempts` | free | 3 | 3 | 3 | engine (route R1: attempts per task) |
| `max_parallel` | free | 3 | 3 | 2 | engine (concurrent tasks per wave) |
| `max_cp_rejects` | free | 2 | 2 | 2 | engine (route R7: rejections of one checkpoint) |
| `budget_usd` | free · 0 = no cap | 0 | 0 | 0 | engine (campaign cost cap) |
| `goldfish_min_score` | safety · up | undeclared | undeclared | undeclared | spec exit gate (BHV-8c), on the implementer reader's score; measure only while undeclared |

Each key has **one** enforcement point; none is applied twice (ADR-14). The policy is resolved once
at start, after `--project`. plan-lint receives it as a parameter; outside an instance
(`lab validate` with no project, tests) the documented `squad` profile stands in, never for a real
run.

No key touches the merge: it stays human in every profile (INV-5) and the rule stays in plan-lint.

`LAB_BUDGET_USD`, when set, takes precedence over `budget_usd` (operator setting, see
[environment.md](environment.md)).

### Free-key bounds (BHV-3d)

| Key | Bound |
|---|---|
| `max_task_attempts`, `max_parallel`, `max_cp_rejects` | integer ≥ 1 |
| `budget_usd` | number ≥ 0 (0 = no cap) |

A value outside its bound is refused, rc 1, naming the key, the value and the bound.

## `.lab/lab.toml` syntax

```toml
schema_version = 1
kit_version = "0.2.0"
profile = "regulated"          # solo | squad | regulated — the floor

[overrides]                    # optional: tighten a safety key, tune a free key
min_reviewers = 3
max_parallel = 4

[overrides.routes]             # optional: R1..R7 = auto | proposal | human
R6 = "human"
```

- `[overrides]` keys are the ten keys above. An **unknown key is an error**, never ignored (BHV-3b).
- A safety-key override is accepted if it is **at least as strict** as the floor; a value equal to
  the floor is accepted. Looser ⇒ refused (BHV-3a).
- `[overrides.routes]` accepts `R1`..`R7` with `auto`, `proposal` or `human`. An unknown route is
  an error. `auto` on **R2, R3, R4 or R5** is refused, rc 1, in every profile (BHV-3c, INV-3).
- Route modes are validated and displayed today, but **applied from iteration 3** (BHV-5);
  `lab policy` says so next to each route.

## Origins

| Origin | Meaning |
|---|---|
| `floor` | Value comes from the profile. |
| `override` | Safety key (or route) set by the instance, at least as strict as the floor. |
| `override (free key)` | Free key set by the instance. |

## Errors

All are rc 1 and name what is wrong.

| Case | Message shape |
|---|---|
| Safety key looser than the floor | `<key>=<value> is looser than floor '<profile>' (<floor value>)` |
| Unknown key / unknown route | `unknown policy key '<key>'` / `unknown route '<route>' in [overrides.routes]` |
| Free key out of bounds | `<key>=<value> is out of bounds (must be … >= <bound>)` |
| `auto` on R2–R5 | `route <Rn>=auto is refused: <Rn> is never automatic (INV-3)` |
| Route mode not in `auto`, `proposal`, `human` | `route <Rn>=…: mode must be one of auto, proposal, human` |
| Profile not in the three names | `profile '<p>' not in solo, squad, regulated` |

## Example (EX-1)

Floor `regulated` (`min_reviewers = 2`, `sandbox_required = true`).

Loosening is refused:

```toml
profile = "regulated"
[overrides]
min_reviewers = 1
```

```
$ lab policy
lab policy: min_reviewers=1 is looser than floor 'regulated' (2)      # rc 1
```

Tightening a safety key and tuning a free key is accepted:

```toml
profile = "regulated"
[overrides]
min_reviewers = 3
max_parallel = 4
```

```
$ lab policy
…
min_reviewers = 3  (override)
max_parallel = 4  (override (free key))
…
```

Output is one line per key: `<key> = <value>  (<origin>)`, then one line per overridden route.
`goldfish_min_score` prints `undeclared` until declared.
