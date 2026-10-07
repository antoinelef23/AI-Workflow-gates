# AI-Native Lab — Agentic Workflow

> A repo skeleton for building software with an agentic workflow. Each unit of work produces three versioned markdown artifacts: `spec.md` (the WHAT), `design.md` (the HOW), `tasks.md` (the DO). They replace user stories, functional specs, and tickets.

A single **Owner** drives the app, agents write the code, a human validates. Every line written by hand is a justified exception, recorded in the commit. The system is built so that **between two human decisions, nothing needs a human** — the decision doesn't disappear, it moves: the Owner decides once (when approving the plan), then the run advances on its own to the next real decision.

## Repo structure

```
ai-native-lab/
├── CLAUDE.md                  # Persistent context loaded by the agents
├── AGENTS.md                  # Vendor-neutral pointer to CLAUDE.md (never a copy)
├── README.md                  # This file: the workflow
├── justfile                   # Standard targets (just gate / validate / run …)
├── pyproject.toml             # Package + pytest/ruff config
├── .githooks/pre-commit       # Local content_guard + plan-lint gate (opt-in)
│
├── lab/                       # ───────── The reusable framework ─────────
│   ├── engine/                # The lab engine (orchestrator, guards, eval harness)
│   │   ├── orchestrate.py     # The DAG executor (waves, gates, checkpoints)
│   │   ├── content_guard.py   # "Substance is sacred, form is free" enforcement
│   │   ├── approvals.py       # HMAC-signed checkpoint approvals
│   │   ├── eval_models.py     # Model×role evaluation campaign
│   │   ├── registry.py        # Reads lab/models/registry.toml
│   │   ├── ci_checks.sh       # CI content-guard + plan-lint over changed features
│   │   ├── run_report.py      # Run-telemetry report (first-pass rate, cost/role/model)
│   │   ├── trajectory_guard.py# HOW a run happened: journal integrity + commit scope
│   │   ├── context_budget.py  # Static-context payload per role (soft budget)
│   │   ├── journal_io.py      # Shared .runs/journal.jsonl reader
│   │   ├── runner.py          # AgentRunner interface (claude-cli | sandbox)
│   │   └── sandbox_runner.py  # Hardened-container runner (LAB_RUNNER=sandbox)
│   ├── templates/             # spec.md / design.md / tasks.md templates
│   └── models/                # registry.toml, profiles/, EVOLUTION.md, scorecards/
│
├── .claude/
│   ├── agents/                # Sub-agents: design-scout, planner, implementer, eval-runner, reviewer
│   ├── hooks/                 # eval_gate.sh (merge gate) + post_edit.sh (lint)
│   ├── statusline.py          # Status line: live orchestrator run state (state.json)
│   ├── settings.json          # Hooks + statusLine + permission denies
│   └── skills/                # vibe-workshop (spec), commit (why→git), diataxis (docs)
├── docs/                      # Diátaxis: tutorials/ how-to/ explanation/ reference/ (see docs/README.md)
│
│                              # ───────── Built with the lab (examples / product) ─────────
├── work/                      # Feature bundles: spec.md / design.md / tasks.md / .runs
├── evals/                     # golden/ (oracles) + behavioral/ (model governance)
├── src/                       # Feature code produced by the method
└── tests/                     # Tests produced by the method
```

## The pipeline: who triggers what

```mermaid
flowchart TD
    VW["Spec workshop<br/>~105 min, 6-8 people"] -->|"trigger: HUMAN"| SPEC["spec.md v1.0<br/>commit + tag"]
    SPEC -->|"trigger: OWNER<br/>(runs design-scout + architecture)"| SCOUT["design-scout<br/>PARALLEL: internal repos ∥ OSS refs"]
    SCOUT --> DESIGN["design.md<br/>validated by FDE"]
    SPEC --> DESIGN
    DESIGN -->|"trigger: OWNER<br/>(runs planner)"| TASKS["tasks.md<br/>agent-generated plan"]
    TASKS -->|"CHECKPOINT: human validation"| GO{Owner approves?}
    GO -->|no: iterate| TASKS
    GO -->|yes| IMPL["implementer(s)<br/>PARALLEL by parallel_group<br/>SEQUENCE by depends_on"]
    IMPL -->|"trigger: AUTOMATIC<br/>(post-implementation hook)"| EVAL["eval-runner<br/>no green eval, no merge"]
    EVAL -->|fail| IMPL
    EVAL -->|pass| REV["reviewer + Owner review"]
    REV -->|"trigger: HUMAN (Owner)"| MERGE["merge → Git audit trail"]
    MERGE -.->|"the spec evolves in the repo"| SPEC
```

## Trigger rules

| Step | Triggered by | Mode | Validation |
|---|---|---|---|
| spec.md v1.0 | **Human** — facilitated spec workshop | Sequential (entry point) | Business signs the contract |
| design.md | **Owner** — runs `design-scout`, then writes it | Scout runs **in parallel** (internal repos ∥ OSS refs) | FDE validates the architecture |
| tasks.md | **Owner** — runs `planner` | Sequential (needs spec + design) | **Mandatory human checkpoint** before execution |
| Implementation | **Agent** — `implementer` per task | **Parallel** across `parallel_group`, **sequenced** via `depends_on` | No manual line without justification |
| Evals | **Automatic** — hook after each task | Sequential per task | Binary gate: no green eval, no merge |
| Merge | **Human** — Owner, reviewed by previous Owner | Sequential | Git audit trail |

## The 3 parallelization principles

1. **Parallelize the research, never the decision.** `design-scout` explores internal repos and OSS references in parallel; writing and validating the design are sequential.
2. **Parallelize tasks with no file dependency.** Two tasks may run in parallel only if their `files_touched` are disjoint AND neither is `depends_on` the other. Otherwise: strict sequence.
3. **Every point of no return is a human checkpoint.** Plan generation, merge, deploy: the agent proposes, the human disposes.

## Autonomy levels

| Level | Command | Human pauses |
|---|---|---|
| L0 — plan | `--dry-run` | everything (nothing runs) |
| L1 — supervised | `--supervised` | ALL checkpoints (`auto` modes ignored) |
| L2 — cruise *(default)* | — | only the `blocking` checkpoints of the approved plan |
| Always | — | the **merge**: never automatic; plan-lint rejects a final `auto` checkpoint |

## The guardrails that make autonomy safe

1. **Plan-lint** (`--validate`, or `just validate work/<feature>`): acyclic DAG, spec IDs exist, `done_when` present, disjoint parallel paths, final checkpoint blocking, every `verify` command on an allowlist. A plan that doesn't lint doesn't run — that's what lets the Owner approve once and walk away.
2. **Structured verdict**: each implementer ends with `STATUS: done` or `STATUS: blocked — <reason>`. An agent blocked on a spec gap (an open question) never passes as finished; it records the question and only its sub-tree stops.
3. **Anti-empty-gate**: a task that implements spec IDs — or merely touches source code — FAILS if no eval is collected (`pytest -m eval --collect-only`). A green `just evals` with zero evals validates nothing. Eval coverage is matched by pytest **node-id** (so `eval_1` ≠ `eval_10`, and a file path doesn't count as coverage).
4. **Per-task verify**: the `verify` command in tasks.md materializes `done_when`. It is parsed to an argv list and run **without a shell** (no metacharacters, command + env-prefix allowlists) — checked mechanically after each agent, before the evals.
5. **Failure containment**: failed/blocked only neutralizes dependents (`skipped`); other branches continue. The run always ends on a summary, never on a mid-course abort.
6. **Scoped commits, why in git**: only the task's `files_touched` (+ the feature dir) are staged, under a lock — two parallel agents don't pollute each other, and the golden oracles can't be swept into a task commit. Out-of-scope changes are reported, not committed. Every commit follows the canonical format ([docs/reference/commit-format.md](docs/reference/commit-format.md)): a `Why:` body + git trailers (`Spec-IDs`, `Version-Bump`, …), the same shape the human `/commit` skill writes — so the *reasoning* behind a change (not just the diff) lives in git, where the reviewer/planner/scout agents recover it via `git log`/`blame`. The `version:` bump stays the *fusible* (intent); git carries the *why*.
7. **Signed human approvals**: checkpoint approvals are HMAC-signed (`lab/engine/approve.sh`) and verified before they're honored, then consumed (no replay). **Fail-closed by default**: a plan with checkpoints refuses to start without `LAB_APPROVAL_SECRET` (opt-out `LAB_ALLOW_UNSIGNED_APPROVALS=1`). The secret is stripped from the agent's environment, and `.approvals/`/`.runs/` are denied to the agent's edit tools.
8. **Concurrency safety**: an OS `flock` (`.runs/orchestrator.lock`) fails a second run on the same feature fast; `state.json` is written atomically and resume tolerates a truncated file.
9. **Documented `auto` checkpoints**: before every checkpoint, the `reviewer` report is written to `.runs/CP-n-review.md`. Auto = green evals AND `VERDICT: PASS`; on any doubt it falls back to human validation.
10. **Session eval gate** (`.claude/settings.json`): `Stop`/`SubagentStop` hooks → an agent can't finish with changed code and red evals; `PostToolUse` → ruff on each edit.
11. **Hash-pinned dependencies** (`just check-lock`, in `gate`/`gate-ci`): installs run `uv sync --locked` against the committed `uv.lock` (sha256) — a dependency cannot appear without a reviewable lockfile diff, a hallucinated package name fails resolution outright, and a package can't be silently swapped on the index without breaking its hash.
12. **Trajectory guard** (`just check-trajectory work/<feature>`): checks HOW a run happened from the journal + git history — a `task_done` with no successful attempt (forged/corrupt journal) or a task commit outside its `files_touched` fails; retry-loops warn.

```bash
# 0. Configure the approval secret once (required for checkpointed plans)
export LAB_APPROVAL_SECRET="$(openssl rand -hex 32)"

# 1. Plan-lint, then Owner approval (status: approved + checkpoint modes)
python3 lab/engine/orchestrate.py work/my-feature --validate

# 2. See the execution plan without running anything
python3 lab/engine/orchestrate.py work/my-feature --dry-run

# 3. Run in the background (caffeinate prevents sleep on macOS)
caffeinate -i python3 lab/engine/orchestrate.py work/my-feature > work/my-feature/.runs/run.log 2>&1 &

# 4. On each blocking CHECKPOINT notification: read .runs/CP-n-review.md, then
lab/engine/approve.sh CP-1 work/my-feature
# … or reject with a reason (reopens the targeted tasks; the agent gets the comment):
lab/engine/reject.sh CP-1 work/my-feature "the quote doesn't show the discount" T2
```

Recovery: state lives in `<feature>/.runs/state.json` — re-running the same command resumes where it stopped (`done` nodes don't replay; `blocked` nodes retry after you answer their open questions). Prerequisites: `claude` CLI authenticated, `uv` installed.

## Documentation

Full docs live in [`docs/`](docs/README.md), organized by the [Diátaxis](https://diataxis.fr/) method: **[tutorials/](docs/tutorials/)** (learn by doing — start with [getting-started](docs/tutorials/getting-started.md)), **[how-to/](docs/how-to/)** (run the orchestrator, commit with rationale, sandbox, automate, evaluate models), **[explanation/](docs/explanation/)** (architecture, git-as-memory, static vs dynamic context), **[reference/](docs/reference/)** (CLI, environment variables, commit format, status line, agents & skills).

## Model evaluation

The lab evaluates not only the **product** (the code, via the spec §7 evals) but also the **models** it uses, per role. Source of truth: `lab/models/registry.toml` (data-driven — adding a model is one entry, zero code). The orchestrator assigns a model to each role (`[roles]`), overridable per task (`**model :**`), and logs which model produced what.

`lab/engine/eval_models.py` (target `just eval-models live=1`) measures three layers:

1. **Scorecard** — on the golden tasks (`evals/golden/`), does the produced code pass **our** hidden evals (never the ones the model writes itself)? Raw capability per role, judged fairly. The oracle is held out: the model never sees `goldeval/` during execution.
2. **Behavioral** (`evals/behavioral/`) — does the model respect its role contract: scope, the `STATUS` verdict, stopping on ambiguity, evals-first, calibrated reviewer verdicts?
3. **Chain-of-command** — can a task instruction make it violate a `CLAUDE.md` hard rule (merge without a human, skip the evals, leave its scope)? It must refuse. This layer is **eliminatory**: one violation disqualifies the model for the role, regardless of its raw score.

Fairness by construction (same prompts, isolated trials, measured metrics, no cherry-pick) and a re-evaluation loop on every new model: see **`lab/models/EVOLUTION.md`**. The harness mechanics are tested in CI with a deterministic `claude` shim (no cost); the real campaign (`LIVE=1`) is manual because it is billed.

## Telemetry and limits

- **Journal**: every run writes `<feature>/.runs/journal.jsonl` — one JSON line per event (attempt, duration, **$ cost per agent**, reviewer verdict, verify/eval failures, summary). The summary prints the run's total cost.
- **Run report**: `just report [feature] [json=1]` aggregates the journals across features — **first-pass success rate**, mean attempts, cost per role and per model, verify/eval failure clusters. This is the quantified proof the registry arbitration (`lab/models/registry.toml`) calls for.
- **Context budget**: `just context-budget` prints the static-context payload each role pays on every call (CLAUDE.md + role `.md` + profile); it only gates once `[context] max_static_tokens` is declared in the registry (see [static vs dynamic context](docs/explanation/static-vs-dynamic-context.md)).
- **Retries with memory**: a retry resumes the SAME agent session (`--resume`) — the agent fixes its work instead of starting over.
- **Per-agent wall clock**: `LAB_TASK_TIMEOUT` (default 2400 s) kills a stuck agent; the task counts as a failed attempt and the wave continues.
- **Budget per run**: `LAB_BUDGET_USD` (orchestrator) and `--budget` (eval campaign) — the run stops before the next wave if cost exceeds the cap, notifies, and resumes via `.runs/state.json`. Cost is measured (`--output-format json`), not estimated.
- **Separation of duties**: a model never validates its own work alone. The review panel prefers a reviewer model ≠ implementer; if impossible, an `auto` checkpoint refuses to self-validate and falls back to human. Plan-lint warns if `roles.reviewer == roles.implementer`.
- **Reviewer panel**: `**reviewers :** N` on a checkpoint runs N reviews from distinct angles (correctness / spec conformance / edge cases); auto-validation only on a **majority** PASS vote.
- **Team notifications**: `LAB_GCHAT_WEBHOOK` (opt-in) posts checkpoints/blocks to a chat webhook (no-op if absent, never crashes).
- **Test env**: `LAB_ROOT` (sandbox), `LAB_NO_NOTIFY=1` (CI). `tests/orchestrator/` replays the whole mechanism (lint, waves, containment, resume, auto checkpoints, anti-empty-gate, signed approvals) in seconds with a deterministic `claude` shim.

## CI

`.github/workflows/gate.yml` mirrors the local merge gate:
- `just gate-ci` — **non-mutating** lint (`ruff check` + `ruff format --check`, so drift fails CI instead of being silently auto-fixed) + tests + evals (the shim orchestrator suite included) + brand guard + lockfile guard (`check-lock`).
- `lab/engine/ci_checks.sh` — runs `content_guard --against <base>` over changed features (the "substance is sacred" rule, enforced vs the base branch, not a clean-checkout HEAD) plus plan-lint (informational). Fail-safe: skips cleanly if the base ref is unavailable.

## Trust model (read this)

The orchestrator drives agents through an `AgentRunner` interface (`lab/engine/runner.py`), so the execution backend is swappable:

- **`claude-cli`** (default) — runs on the **host**, gated by tool allowlists (`--allowedTools`, the `verify` allowlist, `.claude/settings.json` denies). An implementer that runs its own tests has code execution, so here the signed-approval boundary is *defense-in-depth that raises the bar*, not a hard boundary against a determined, code-executing agent.
- **`sandbox`** (`LAB_RUNNER=sandbox`, see [docs/how-to/use-the-sandbox.md](docs/how-to/use-the-sandbox.md)) — runs the same call in a hardened container: only the repo is mounted, the approval secret is never passed in, egress is allowlisted, non-root + read-only rootfs + dropped caps. This makes the secret **unreachable** by the agent, which is what turns the approval crypto into a true boundary. Validated end-to-end on Docker (the secret is provably absent inside the container); the egress-allowlist proxy is operator infrastructure.

Intended threat model: a **trusted-but-possibly-misaligned** agent on the host runner; a **malicious** agent under the sandbox runner.

## Backlog (acknowledged, not shipped)

- **Egress-allowlist proxy** — the sandbox restricts egress to a network you control; a bundled filtering proxy (model API + package registry only) is documented in docs/how-to/use-the-sandbox.md but not shipped.
- **Cross-vendor provider runner** — the `AgentRunner` seam exists; a Vertex/Gemini implementation is a drop-in (not testable here without other-provider access).
- **Git worktree per parallel task** — makes file collision *impossible* rather than *forbidden*; deferred to avoid destabilizing the verified orchestrator, deserves its own PR.

## Start a unit of work

```bash
cp lab/templates/spec.md   work/<feature>/spec.md     # filled in the spec workshop
cp lab/templates/design.md work/<feature>/design.md   # filled by Owner + design-scout
cp lab/templates/tasks.md  work/<feature>/tasks.md    # generated by planner, approved by Owner
```

Then in Claude Code: `read work/<feature>/spec.md and design.md, generate tasks.md per lab/templates/tasks.md, and wait for my approval before executing.`
