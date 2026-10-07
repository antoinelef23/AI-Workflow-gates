# How to run the orchestrator on a feature

This guide shows you how to take a feature whose plan (`tasks.md`) is ready and
drive it to completion with `lab/engine/orchestrate.py`: launch the run in the
background, pick an autonomy level, respond to a blocking checkpoint, and resume
after a stop.

It assumes the three artifacts already exist in `work/<feature>/`
(`spec.md`, `design.md`, `tasks.md`) and that `tasks.md` is the plan you intend
to execute. If you still need to generate the plan, do that first (see the
[getting-started tutorial](../tutorials/getting-started.md)); this guide starts
once a plan exists and ends when the run reaches its final (merge) checkpoint.

## Prerequisites

- The `claude` CLI installed and **authenticated** (the orchestrator calls it headless).
- `uv` installed (used for `pytest`/evals).
- A feature directory `work/<feature>/` containing `tasks.md`.
- `tasks.md` frontmatter set to `status: approved` — the orchestrator refuses an
  unapproved plan (`--dry-run` and `--force` are the only ways past this).
- `LAB_APPROVAL_SECRET` exported **if your plan has any checkpoint**. A plan with
  a checkpoint refuses to start without it (see [Troubleshooting](#troubleshooting)).

Set the approval secret once per shell session:

    export LAB_APPROVAL_SECRET="$(openssl rand -hex 32)"

Keep this secret out of the agents' environment — the orchestrator strips it
before each agent call, so do not echo it into `tasks.md` or any artifact.

## Steps

### 1. Lint the plan

Validate the DAG before anything runs. A plan that does not lint does not run.

    python3 lab/engine/orchestrate.py work/<feature> --validate
    # or: just validate work/<feature>

This checks the acyclic graph, that spec IDs exist, `done_when` is present,
parallel paths touch disjoint files, the final checkpoint is `blocking`, and
every `verify` command is on the allowlist. It also prints the `verify` commands
that will run on the host — read them, because approving the plan means signing
off on those commands. Exit code is non-zero if there are errors. Fix any error
and re-run before proceeding.

### 2. Preview the execution plan (optional)

See the waves and checkpoints without executing or spending anything:

    python3 lab/engine/orchestrate.py work/<feature> --dry-run

This is autonomy level **L0 — plan**: nothing runs, no agent is called.

### 3. Launch the run in the background

On macOS, wrap the run in `caffeinate -i` so the machine does not sleep mid-run,
and redirect output to a log file:

    caffeinate -i python3 lab/engine/orchestrate.py work/<feature> \
      > work/<feature>/.runs/run.log 2>&1 &

This is the default autonomy level **L2 — cruise**: the run pauses only at the
`blocking` checkpoints of the approved plan; `auto` checkpoints self-validate
when evals are green and the reviewer panel returns PASS.

To run in the foreground instead (still `caffeinate`-wrapped), use the justfile:

    just run work/<feature>

### 4. Choose an autonomy level

Pick the flag that matches how closely you want to supervise this run:

- **L0 — plan**: `--dry-run`. Nothing runs. Use it to inspect waves.
- **L1 — supervised**: `--supervised` (or `just run work/<feature> supervised=1`).
  Every checkpoint pauses for you, even ones the plan marked `auto`.
- **L2 — cruise** *(default)*: no flag. Only the `blocking` checkpoints pause.

The **merge** is never automatic at any level: plan-lint rejects a plan whose
final checkpoint is `auto`, so the last decision is always yours.

For the full flag table, see the [CLI reference](../reference/cli.md).

### 5. Respond to a blocking checkpoint

When the run hits a blocking checkpoint it pauses, sends a notification, and
prints a line like:

    ⏸  CP-1 — waiting for work/<feature>/.approvals/CP-1 (or .rejected)

Before you decide, read the reviewer report the orchestrator wrote for that
checkpoint:

    work/<feature>/.runs/CP-1-review.md

It carries the panel's aggregated verdict (PASS / WARN / BLOCK) and each
panelist's findings with `file:line`. Then either approve or reject.

**Approve** — write the signed token the orchestrator is waiting for:

    lab/engine/approve.sh CP-1 work/<feature>

The token is HMAC-signed with `LAB_APPROVAL_SECRET`, verified, then consumed
(it cannot be replayed). The run resumes on the next poll.

**Reject** — reopen the targeted tasks with a reason passed verbatim to the agent:

    lab/engine/reject.sh CP-1 work/<feature> "the quote doesn't show the discount" T2

Omit the task IDs to reopen all tasks the checkpoint covers. The reopened tasks
re-run with your feedback attached, then the checkpoint is presented again. After
more than two rejections of the same checkpoint, the run stops and requires a
manual resume.

### 6. Watch progress

Follow the run as it advances:

    tail -f work/<feature>/.runs/run.log

The live status line (`.claude/statusline.py`, wired in `settings.json`) reflects
the run state from `state.json`. See the [status-line reference](../reference/status-line.md).

### 7. Resume after a stop

If the run stops — budget cap reached, a node blocked or failed, too many
checkpoint rejections, or you killed it — fix the cause, then **re-run the exact
same command**:

    caffeinate -i python3 lab/engine/orchestrate.py work/<feature> \
      > work/<feature>/.runs/run.log 2>&1 &

Resume reads `work/<feature>/.runs/state.json`: `done` nodes are not replayed.
A node that ended `blocked` recorded an open question (OQ) in `spec.md` §8 —
answer it before resuming, and the node retries. A truncated `state.json` (from a
hard kill mid-write) does not crash the resume; the run restarts cleanly instead.

### 8. Finish

The run ends on a summary that lists each node's final status and the total agent
cost. When all tasks are done, the final (merge) checkpoint is the human decision
that closes the feature — it is never auto-validated.

## Where logs and state live

Everything for a run lives under `work/<feature>/.runs/` and
`work/<feature>/.approvals/`:

- `.runs/state.json` — node statuses; the resume source of truth (written atomically).
- `.runs/run.log` — the run's stdout/stderr (if you redirected as above).
- `.runs/journal.jsonl` — one JSON line per event (attempt, duration, per-agent cost, verdict, summary).
- `.runs/CP-n-review.md` — the reviewer panel report for checkpoint `CP-n`.
- `.runs/orchestrator.lock` — the OS lock held for the duration of the run.
- `.approvals/CP-n` — a pending signed approval token; renamed to `.handled-…` once consumed.
- `.approvals/CP-n.rejected` — a pending rejection; renamed to `.handled-…` once read.

These paths are denied to the agents' edit tools by `.claude/settings.json`.

## Troubleshooting

### The run aborts with "orchestrator lock already held"

A second orchestrator was started on the same feature while the first is still
running (an OS `flock` on `.runs/orchestrator.lock` fails the second one fast).
Wait for the active run to finish. If the previous process died without releasing
the lock, the lock is stale — delete the file and re-run:

    rm work/<feature>/.runs/orchestrator.lock

### The run refuses to start: "LAB_APPROVAL_SECRET not set"

Your plan has a checkpoint, and without a signing secret any `.approvals/<CP>`
file an agent could write via Bash would be honored — so the orchestrator
fails closed. Export the secret (recommended):

    export LAB_APPROVAL_SECRET="$(openssl rand -hex 32)"

Only if you knowingly accept unsigned, forgeable approvals, opt out:

    LAB_ALLOW_UNSIGNED_APPROVALS=1 python3 lab/engine/orchestrate.py work/<feature>

### The run refuses to start: status is not "approved"

The orchestrator runs only an approved plan. Set `status: approved` in the
`tasks.md` frontmatter once you (the Owner) have signed off on the lint output.

### An approval is rejected as forged / "approval REJECTED"

The token in `.approvals/CP-n` failed signature verification (wrong or missing
secret, or a hand-edited token). The orchestrator discards it (renamed
`.invalid-…`) and keeps waiting. Re-create a valid token with `lab/engine/approve.sh`
in a shell that has the same `LAB_APPROVAL_SECRET` that started the run.

### The run stopped on budget

`LAB_BUDGET_USD` was reached and the run stopped before the next wave. Review the
cost in `.runs/journal.jsonl`, raise or unset the cap, then resume with the same
command.

## Reference

- Full flag list: [CLI reference](../reference/cli.md).
- Full environment-variable list (`LAB_*`): [environment reference](../reference/environment.md).
- To run agents inside a hardened container: [use the sandbox](use-the-sandbox.md).
- To schedule or automate runs: [automate runs](automate-runs.md).
- Why checkpoints, scoped commits, and the eval gate work this way: [architecture](../explanation/architecture.md).
