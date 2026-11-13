# Choose an organization profile

> Diátaxis: **how-to**. Goal: pick the control level of a client instance, check it, and harden it
> later. Keys and syntax: [policy-profiles.md](../reference/policy-profiles.md).

A profile is the **floor** of control for an instance. Choose it explicitly at
`lab init <project> --profile <p>` — there is no default.

## 1. Pick the profile

| Situation | Profile | What you get |
|---|---|---|
| FDE alone on a proof of concept | `solo` | Auto checkpoints allowed, up to 8 tasks between checkpoints, `--force` allowed, host runner. |
| Mixed squad (FDE + client engineers) | `squad` | Same switches as `solo`, but at most 5 tasks between two checkpoints. |
| Regulated environment | `regulated` | No auto checkpoint, 2 reviewers minimum, at most 3 tasks between checkpoints, sandbox required, `--force` refused, 2 tasks in parallel. |

In every profile: the merge is human (INV-5), and a failure routed back to the spec, design or an
approved plan only produces a **proposal** a human signs (INV-3).

## 2. Check what applies

```bash
lab policy --project <instance>     # or run it from the instance root
```

Each line shows a key, its value and its origin (`floor`, `override`, `override (free key)`).

## 3. Harden a key

Edit `.lab/lab.toml` of the instance:

```toml
profile = "squad"

[overrides]
min_reviewers = 2
max_tasks_between_checkpoints = 3
sandbox_required = true
```

Then run `lab policy` again. Commit the change: like the kit pin, the policy of an instance is a
reviewable diff.

## 4. Tune a free key

Performance and cost keys have no direction; set them freely within their bounds:

```toml
[overrides]
max_parallel = 4
budget_usd = 25
```

## 5. Pin a route to a human

```toml
[overrides.routes]
R6 = "human"
```

Route modes are validated today and applied from iteration 3.

## Why you cannot loosen

A profile is a floor, like a service control policy: a lower level can only narrow what a higher
one allows. If a regulated instance could write `min_reviewers = 1`, the profile would prove
nothing to the people relying on it. So a safety key overridden below the floor is refused
(rc 1, naming the key, your value and the floor), and an unknown key is an error rather than a
silent typo.

If the floor is too strict for the project, change the **profile** (an explicit, committed
decision), not a single key:

1. Edit `profile` in `.lab/lab.toml` (and remove overrides the new floor makes redundant).
2. Run `lab policy` and commit with a `Why:` that records the decision.

## When a run refuses to start

| Message | Cause | Fix |
|---|---|---|
| `sandbox_required is true (profile '…')` | `regulated`, or an override | Run with `LAB_RUNNER=sandbox` — see [use-the-sandbox.md](use-the-sandbox.md). |
| `allow_force is false (profile '…'): --force is refused` | `regulated`, or an override | Fix the plan-lint errors or get the plan approved instead of forcing. |
| plan-lint error on a `mode: auto` checkpoint, `reviewers`, or tasks between checkpoints | the plan breaks the policy | Make the checkpoint blocking, add reviewers or a checkpoint. |
