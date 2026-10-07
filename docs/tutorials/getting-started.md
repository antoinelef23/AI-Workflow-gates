# Getting started — your first merged feature

In this tutorial, we will take the smallest possible real feature from nothing to a merged
result: we set the approval secret, look at the three artifacts that drive the work, run the
plan-lint, watch the plan without running it, run it for real, approve a checkpoint, and end
with the feature merged and the *why* recorded in git.

We mirror a feature that already exists in the repo — `work/devis-pose/`, a pure
"installation quote" calculator with no I/O — so every command below is real and reproducible.

This is a lesson, not a reference. We minimise explanation and link out instead. By the end you
will recognise the shape of every run you do afterwards.

## Before we begin

We need, from the repo root (`lab-ia-natif/`):

- The `claude` CLI, installed and authenticated.
- `uv` installed (Python 3.12+).
- `just` installed (our task runner).
- `openssl` (already on macOS/Linux) to generate a secret.

That is all. Let's go.

## Step 1: Set the approval secret

Any plan that contains a human checkpoint refuses to start without a signing secret — that is
the lab's fail-closed default. We export one for this shell session:

```bash
export LAB_APPROVAL_SECRET="$(openssl rand -hex 32)"
```

Confirm it is set:

```bash
echo "${LAB_APPROVAL_SECRET:+secret is set}"
```

The output should be exactly:

```
secret is set
```

Notice that we never print the secret itself. It signs the approval tokens we'll create in
Step 6, and the orchestrator strips it from every agent's environment so an agent can't forge
an approval. (Why this matters: [explanation/architecture.md](../explanation/architecture.md).)

## Step 2: Look at the three artifacts

Every unit of work is three versioned markdown files in `work/<feature>/`. Let's read the ones
for our tiny feature:

```bash
ls work/devis-pose
```

The output should look something like:

```
design.md	spec.md		tasks.md
```

These three are the whole contract — they replace user stories, functional specs, and tickets:

- **`spec.md`** — the WHAT. The business contract: invariants (`INV-1`…), behaviors (`BHV-1`…),
  worked examples (`EX-1`…), and the evals that gate the merge (`EVAL-1`…). Open it and notice
  section 7, "Evals — merge gate": no green eval, no merge.
- **`design.md`** — the HOW. The stack and the architecture decisions, each anchored to a
  reference pattern (here `compute_quote` / `format_quote`, pure functions, no network).
- **`tasks.md`** — the DO. The execution plan: tasks `T1…T4`, two checkpoints `CP-1` (auto) and
  `CP-2` (merge, blocking), with `depends_on` for sequencing and `parallel_group` for parallelism.

Open `work/devis-pose/tasks.md` and find the line `status: approved` in its frontmatter. That
is the Owner's signature: the orchestrator refuses to *run* a plan that isn't `approved`. The
plan is already approved here, so we can drive it.

To start your own feature later, you copy the templates — but for this tutorial we reuse the
existing, validated `devis-pose`:

```bash
# (for later — not now)
# cp lab/templates/spec.md   work/<feature>/spec.md
# cp lab/templates/design.md work/<feature>/design.md
# cp lab/templates/tasks.md  work/<feature>/tasks.md
```

## Step 3: Plan-lint the feature

Before anything runs, we lint the plan. Plan-lint checks the DAG is acyclic, that every spec ID
referenced exists, that `done_when` is present, that parallel tasks touch disjoint files, that
the final checkpoint is blocking, and that every `verify` command is on the allowlist.

```bash
just validate work/devis-pose
```

The output should look something like:

```
Plan-lint — 6 nodes, frontmatter status: approved
  ✅ no problem

  Verify commands (run without a shell, to validate):
    T1: uv run pytest -q -m "not eval"
    T2: uv run pytest -q tests/devis_calc
    T3: uv run pytest -q tests/devis_format
    T4: uv run pytest -q tests/devis_cli
```

Notice that plan-lint surfaces every `verify` command. By approving the plan, the Owner is
signing off on exactly these commands — they will run on the host after each agent, parsed to an
argv list and executed **without a shell**. A plan that lints is a plan the Owner can approve
once and walk away from. If it doesn't lint, it doesn't run.

## Step 4: Dry-run — see the plan, run nothing

Now we ask the orchestrator to show us the execution plan without touching anything:

```bash
python3 lab/engine/orchestrate.py work/devis-pose --dry-run
```

The output should look something like:

```
Plan: 6 nodes — T1, T2, T3, CP-1, T4, CP-2
Models (registry): implementer=claude-sonnet-4-6, reviewer=claude-opus-4-8

=== Parallel wave: T1 ===
  [dry-run] claude-cli run: T1 (acceptEdits, max_turns=100, 7 allowed tools)

=== Parallel wave: T2, T3 ===
  [dry-run] claude-cli run: T2 (acceptEdits, max_turns=100, 7 allowed tools)
  [dry-run] claude-cli run: T3 (acceptEdits, max_turns=100, 7 allowed tools)
  [dry-run] CHECKPOINT CP-1 (mode auto) — waits for work/devis-pose/.approvals/CP-1
```

Notice the second wave runs `T2` and `T3` **together**: they have no file dependency on each
other (`calc.py` vs `format.py`), so they parallelize. `T1` runs first because both depend on
it. Nothing was executed — `--dry-run` writes no state and runs no agents. This is the plan you
are about to authorise for real.

## Step 5: Run it for real

We launch the run in the foreground via `just`. (On macOS, the recipe wraps the call in
`caffeinate -i` so your machine won't sleep mid-run.)

```bash
just run work/devis-pose
```

The orchestrator walks the waves, runs an agent per task, and passes the eval gate after each
one. The output is a live narrative:

```
Plan: 6 nodes — T1, T2, T3, CP-1, T4, CP-2

=== Parallel wave: T1 ===
▶ T1 (attempt 1/3)

=== Parallel wave: T2, T3 ===
▶ T2 (attempt 1/3)
▶ T3 (attempt 1/3)
```

When the agents finish `T2` and `T3`, the run reaches the first checkpoint and pauses:

```
🔔 CHECKPOINT CP-1 — Owner validation required → lab/engine/approve.sh CP-1 work/devis-pose (reviewer report: work/devis-pose/.runs/CP-1-review.md)
⏸  CP-1 — waiting for .../work/devis-pose/.approvals/CP-1
```

Notice the run did **not** abort — it is *waiting* for us. `CP-1` was declared `mode: auto`, but
auto-validation only happens when the evals are green AND the reviewer votes PASS; on any doubt
it falls back to asking a human. That fallback is exactly what we want to experience, so leave
this terminal paused and open a second one for the next step.

## Step 6: Approve the checkpoint

In the second terminal (with `LAB_APPROVAL_SECRET` still exported in the same shell session),
first read what the reviewer found:

```bash
cat work/devis-pose/.runs/CP-1-review.md
```

This report is written before every checkpoint so the Owner decides on evidence, not vibes.
Satisfied, we sign the approval:

```bash
lab/engine/approve.sh CP-1 work/devis-pose
```

The output should be:

```
✅ CP-1 approved for work/devis-pose
```

Back in the first terminal, the paused run picks the approval up and continues:

```
🔔 CP-1 validated — resuming execution

=== Parallel wave: T4 ===
▶ T4 (attempt 1/3)
```

Notice what just happened: `approve.sh` created an HMAC-signed token (signed with our secret);
the orchestrator verified it, then **consumed** it so it can't be replayed. If we'd disagreed
instead, we would have rejected it with a reason that gets passed straight to the agent:

```bash
# (alternative — not now)
# lab/engine/reject.sh CP-1 work/devis-pose "the quote doesn't show the discount" T2
```

## Step 7: Approve the merge and see it land

`T4` (the CLI) finishes and the run reaches the final checkpoint, `CP-2`. This one is
`mode: blocking` — the merge is **never** automatic:

```
🔔 CHECKPOINT CP-2 — Owner validation required → lab/engine/approve.sh CP-2 work/devis-pose (reviewer report: work/devis-pose/.runs/CP-2-review.md)
⏸  CP-2 — waiting for .../work/devis-pose/.approvals/CP-2
```

We read `work/devis-pose/.runs/CP-2-review.md`, then approve:

```bash
lab/engine/approve.sh CP-2 work/devis-pose
```

The run resumes and ends on a summary — never on a mid-course abort:

```
=== Summary ===
  ✅ T1 — done
  ✅ T2 — done
  ✅ T3 — done
  ✅ CP-1 — done
  ✅ T4 — done
  ✅ CP-2 — done
  Σ agent cost: $0.42 (detail: .runs/journal.jsonl)
🎉 devis-pose: all tasks are done. Merge = human decision (final CP).
```

(Your cost figure will differ — it is measured per agent, not estimated.)

## Step 8: Read the *why* in git

Each task committed only its own files, under a lock, with the reasoning in the commit body —
not just the diff. Let's see it:

```bash
git log --oneline -6
```

The output should look something like:

```
a1b2c3d feat(devis-pose): quote CLI [BHV-1, BHV-3]
e4f5g6h feat(devis-pose): format module: format_quote [BHV-3]
...
```

Now read one commit in full:

```bash
git show --stat HEAD
```

Notice the `Why:` body and the trailers (`Spec-IDs`, `Version-Bump`, `Checkpoint`, `Run`). The
diff says *what* changed; the `Why:` says *why* it changed and what triggered it. That is the
lab's memory: the next agent (reviewer, planner, scout) recovers the reasoning via
`git log`/`git blame` instead of re-litigating a decision. The commit shape is the same whether
a human or the orchestrator wrote it — see
[reference/commit-format.md](../reference/commit-format.md).

## What we built

We took a feature from nothing to merged through the full agentic loop:

- set a signing secret and learned why checkpoints fail-closed without it;
- read the three artifacts (`spec.md` / `design.md` / `tasks.md`) that *are* the work;
- plan-linted and saw the `verify` commands the Owner authorises;
- dry-ran to see the parallel waves before committing;
- ran for real and watched parallel tasks, the eval gate, and the checkpoint pause;
- approved a checkpoint with a signed, single-use token;
- approved the final merge — the one decision that is never automatic;
- found the reasoning preserved in git, where the next agent will read it.

You now recognise the rhythm of every run: **plan-lint → dry-run → run → approve → merge.**

## Next steps

- Drive your own feature end to end, with all the run options:
  [how-to/run-the-orchestrator.md](../how-to/run-the-orchestrator.md)
- Understand why the system is built this way (autonomy, checkpoints, parallelization, the
  trust model): [explanation/architecture.md](../explanation/architecture.md)
- See why the reasoning lives in commits, not a wiki:
  [explanation/git-as-memory.md](../explanation/git-as-memory.md)
