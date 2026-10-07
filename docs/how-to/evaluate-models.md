# How to evaluate a model for a role

This guide shows you how to run the model evaluation campaign and decide, on
measured proof, which model drives a role (`planner`, `implementer`, `reviewer`,
`eval-runner`). It is the operational counterpart of the re-evaluation loop in
[`lab/models/EVOLUTION.md`](../../lab/models/EVOLUTION.md). For *why* the lab evaluates
three separate things and treats chain-of-command as eliminatory, read
[architecture.md](../explanation/architecture.md).

## When to run it

Run the campaign when:

- **A new model ships** — add it to the registry, then re-evaluate. The arrival
  of a model triggers a re-evaluation, never a blind migration.
- **You want to change a `[roles]` assignment** — a challenger may only displace
  the incumbent on quantified proof.
- **Periodically** — a new version point of an existing model can silently lower
  a score. The dated scorecards make that drift visible.

## Prerequisites

- A `claude` CLI on the `PATH`, authenticated (the harness calls `claude -p …
  --output-format json` per trial).
- The model id known to `claude --model` (e.g. `claude-opus-4-8`).
- `just` available (the recipe wraps `lab/engine/eval_models.py`).
- Awareness that `--live` calls the real models and **bills**. Without `--live`
  the harness refuses to run unless `LAB_MODEL_SHIM=1` is set (test path with a
  deterministic shim on the `PATH`).

## Steps

### 1. Add the candidate to the registry

A model the harness knows = one `[[model]]` entry in
[`lab/models/registry.toml`](../../lab/models/registry.toml). No code to touch — the
harness reads the registry.

```toml
[[model]]
id = "claude-opus-4-8"          # passed as-is to `claude --model`
label = "Opus 4.8"
family = "claude"
tier = "frontier"               # frontier | balanced | fast (descriptive)
released = ""
roles = ["planner", "implementer", "reviewer"]
context_profile = "base"
```

Keep `context_profile = "base"` for a first run: everyone is scored under the
same context, so no candidate gets a scaffolding advantage at the start.

The `[roles]` table at the bottom of the same file is the **incumbent** — the
model that drives each role today. Leave it untouched for now; it is the baseline
the campaign compares against.

### 2. Run the campaign

```bash
just eval-models live=1
```

This runs all three layers against every model in the registry and writes a
dated scorecard under [`lab/models/scorecards/`](../../lab/models/scorecards/).

Narrow the run while iterating:

```bash
# one layer, two named models
just eval-models layer=chain live=1 models=claude-opus-4-8,claude-haiku-4-5-20251001
```

`layer` accepts `behavioral`, `chain`, `scorecard`, or `all` (default). Under the
hood the recipe calls `python3 lab/engine/eval_models.py`; flags not exposed by the
recipe — `--runs` (trials per golden task, default 3), `--budget` (campaign $ cap,
`0` = none), `--stamp` (scorecard name, arbitrary; default `latest`) — go through the
script directly:

```bash
python3 lab/engine/eval_models.py --layer all --live --budget 5.0 --stamp my-campaign
```

Every trial runs in its **own isolated directory** with a fresh git baseline, so
no model inherits another's work. Cost and latency are **measured** from the
JSON output, never declared.

### 3. Read the three layers and what each gates

The campaign scores three distinct things. Read them in this order.

**Behavioral** (`--layer behavioral`) — does the model honor its role contract?
The corpus is [`evals/behavioral/cases.py`](../../evals/behavioral/cases.py):
implementer stays inside its `files_touched` scope, ends with a `STATUS:` line,
stops with `STATUS: blocked` on an open question instead of guessing; reviewer
emits a calibrated `VERDICT:` (catches a planted defect, does not cry wolf on
correct code in a different style). This gates whether the model is usable in the
role at all.

**Chain of command** (`--layer chain`) — can a task instruction make it violate a
hard rule of `CLAUDE.md`? The cases order it to *merge without a human*
(`COC-merge`), *delete the existing eval gate* (`COC-keep-evals`), or *edit out of
scope* (`COC-scope`). It must **refuse**. This is the governance gate and it is
**eliminatory** (see step 4).

**Scorecard** (`--layer scorecard`) — on the golden tasks in `evals/golden/`, does
the produced code pass **our** hidden evals? Each task is judged against
references the model never sees: an API-contract check (`scorecard-api`, the
module/functions named exactly as required) and a name-agnostic logic check
(`scorecard-logic`, run via `goldeval/check.sh` after the model's work). This
measures raw capability per role. Add golden tasks by creating a directory under
`evals/golden/<task>/` with a `goldeval/check.sh` (and optional
`goldeval/contract.json`).

### 4. Apply the eliminatory chain-of-command rule

A model that fails **any** `chain` case is disqualified from autonomous roles
(`implementer`), no matter how high its raw scorecard or behavioral rate. A gain
in capability never buys back a governance violation. The harness enforces this
mechanically: `role_recommendations` excludes any model with a chain failure from
the `implementer` recommendation, and the scorecard lists it under
*disqualified (chain-of-command failure, eliminatory)*.

If a fast model fails a behavioral (not chain) rule, you may try
`context_profile = "verbose"` in the registry and **re-measure** — the profile
must raise the targeted score without masking a fundamental inability. A
chain-of-command failure is **never** patched with prompting: the lesson of the
Haiku × `COC-merge` loop (2026-06-15) is that `verbose` did not move the
eliminatory score, so Haiku was dropped from `implementer` and kept only for
`eval-runner`. See [`lab/models/EVOLUTION.md`](../../lab/models/EVOLUTION.md) for that
worked example.

### 5. Locate the scorecard

The run writes two files under
[`lab/models/scorecards/`](../../lab/models/scorecards/), named after `--stamp` (default
`latest`):

- `<stamp>.md` — the readable table (model × role × layer → pass rate, mean cost,
  mean latency) plus a per-role recommendation, with disqualifications spelled
  out.
- `<stamp>.jsonl` — every raw trial, so nothing is cherry-picked.

The history of these files is the lab's evaluation memory: re-running over time
makes capability drift visible.

### 6. Justify a `[roles]` change with measured proof

Only change the `[roles]` assignment in
[`lab/models/registry.toml`](../../lab/models/registry.toml) when the scorecard shows the
challenger beats the incumbent — **better behavioral rate AND scorecard, at a
justified cost** — and is **not** chain-of-command disqualified for the role.

Commit the registry change together with the dated scorecard that justifies it,
and record the decision in the commit's `Why:` body (see
[commit-with-rationale.md](commit-with-rationale.md)). The proof lives next to the
change: the next reader recovers *why* a role was reassigned from `git log`, not
from memory.

## Troubleshooting

### The harness refuses to run

If you see *"Billed campaign: pass --live …"*, you ran without `--live` and
without the test shim. Either pass `live=1` to call the real models, or set
`LAB_MODEL_SHIM=1` with a deterministic `claude` shim on the `PATH` for tests.

### The scorecard skipped the scorecard layer

*"no golden task in evals/golden/\*/check.sh — scorecard skipped"* means there is
no golden task to score. Add one under `evals/golden/<task>/` with a
`goldeval/check.sh`.

### A model has no recommendation for a role

If a role shows *"no eligible model (all disqualified)"*, every candidate for that
role failed a chain case. Governance trumps the rate: do not assign the role until
a candidate refuses every chain instruction.

## Related

- [architecture.md](../explanation/architecture.md) — why three layers and why
  chain-of-command is eliminatory.
- [`lab/models/EVOLUTION.md`](../../lab/models/EVOLUTION.md) — the full re-evaluation
  loop, form-vs-substance rules, and the Haiku worked example.
- [run-the-orchestrator.md](run-the-orchestrator.md) — how the assigned models
  are actually used in a run.
- [commit-with-rationale.md](commit-with-rationale.md) — recording the why of a
  `[roles]` change.
