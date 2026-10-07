# Agents & Skills Reference

Austere lookup of the lab's sub-agents (`.claude/agents/*.md`), skills
(`.claude/skills/*/SKILL.md`), and the hook + status-line wiring
(`.claude/settings.json`, `.claude/hooks/*`, `.claude/statusline.py`).

For how these pieces orchestrate together, see
[../explanation/architecture.md](../explanation/architecture.md). For usage, see
the how-to guides linked per row.

## Sub-agents

Each file in `.claude/agents/` declares a sub-agent in YAML front matter
(`name`, `description`, optional `tools`, `version`). The `tools` column lists
the front-matter `tools:` field; "(inherited)" means the field is absent and the
agent inherits the caller's tool set.

| Agent | Version | Tools | Role |
| --- | --- | --- | --- |
| `design-scout` | 1.1.0 | `Read, Grep, Glob, Bash, WebFetch, WebSearch` | Collects and analyzes reference repos (internal + OSS Python) to fill §2 of `design.md`. Read-only; decides nothing. Run BEFORE writing `design.md`. |
| `planner` | 1.1.0 | `Read, Grep, Glob, Write, Bash` | Generates `tasks.md` from `spec.md` + `design.md`: sequences (`depends_on`), parallelizes (`parallel_group`), places checkpoints. Never codes, never executes the plan. |
| `implementer` | 1.0.0 | (inherited) | Implements ONE task from `tasks.md`. Tests first, code second. Touches only its task's `files_touched`. Ends with a `STATUS:` verdict line. |
| `eval-runner` | 1.0.0 | `Read, Bash, Grep, Glob` | Runs `spec.md` §7 evals after a task. Binary merge gate (no green eval, no merge). Emits `PASS`/`FAIL`; never fixes code. |
| `reviewer` | 1.1.0 | `Read, Grep, Glob, Bash` | Cross-reviews spec ↔ code before human review: traceability, design conformance, scope, quality. Emits `VERDICT: PASS`/`WARN`/`BLOCK`. Never modifies code. |

### Verdict lines

The orchestrator parses one machine-readable line at the end of an agent's
reply.

| Agent | Line | Values |
| --- | --- | --- |
| `implementer` | `STATUS:` | `done`, `blocked — <reason>` |
| `eval-runner` | (verdict) | `PASS`, `FAIL` |
| `reviewer` | `VERDICT:` | `PASS`, `WARN`, `BLOCK` |

On a `mode: auto` checkpoint, `reviewer` emits `VERDICT: PASS` only with zero
deviation; any doubt falls back to `WARN` (human validation). `eval-runner`
escalates to the Owner on the 3rd consecutive `FAIL` on the same task.

## Skills

Each file in `.claude/skills/<name>/SKILL.md` declares a skill in YAML front
matter (`name`, `description`).

| Skill | Purpose | When |
| --- | --- | --- |
| `vibe-workshop` | Facilitates the 105-min Spec Workshop (6-8 people) that produces `spec.md` v1.0; Claude mediates over screen share and writes the spec live. | The PE kicks off a spec workshop with the business. |
| `commit` | Writes a git commit whose body records WHY the change exists (workshop decision, resolved OQ, trade-off), in the lab's canonical format; honors the `content_guard` fusible (substance change ⇒ `version:` bump). | Committing artifact or code changes in the lab. See [commit-with-rationale.md](../how-to/commit-with-rationale.md) and [commit-format.md](commit-format.md). |
| `diataxis` | Organizes/creates docs by the Diátaxis method: classifies pages into tutorials/how-to/explanation/reference, identifies gaps, applies category templates. | Writing or restructuring `docs/`. |

## Hooks & status line

Wired in `.claude/settings.json`. Hook scripts live in `.claude/hooks/`; the
status-line script is `.claude/statusline.py`. The variable
`$CLAUDE_PROJECT_DIR` resolves to the repo root.

### Hooks

| Event | Matcher | Command | Fires on / behavior |
| --- | --- | --- | --- |
| `PostToolUse` | `Edit\|Write\|MultiEdit` | `bash $CLAUDE_PROJECT_DIR/.claude/hooks/post_edit.sh` | After an edit/write/multi-edit. Runs `uv run ruff check --fix` then `uv run ruff format` on the modified file if it is `*.py` and `uv` + `pyproject.toml` exist. Informative, always exits 0 (never blocks). |
| `SubagentStop` | (none) | `bash $CLAUDE_PROJECT_DIR/.claude/hooks/eval_gate.sh` | When a sub-agent finishes. The automatic merge gate (see below). |
| `Stop` | (none) | `bash $CLAUDE_PROJECT_DIR/.claude/hooks/eval_gate.sh` | When the main agent finishes. The automatic merge gate (see below). |

#### `eval_gate.sh` behavior

The merge gate, fired on `Stop` and `SubagentStop`:

- Exits 0 immediately if `stop_hook_active` is true (avoids re-run loops), if no
  `pyproject.toml` exists, or if `git status --porcelain --untracked-files=all`
  shows no changed `*.py`/`*.toml` file.
- Otherwise runs `just evals`. Non-zero exit → prints `⛔ EVAL GATE RED` plus the
  last 40 lines of output to stderr and **exits 2** (the agent is sent back to
  fix).
- If `just evals` passes but `uv run pytest -m eval --collect-only` collects zero
  evals, prints a non-blocking `⚠️ eval-gate` warning (green by absence, not by
  success). The hard "no eval = no done" rule is enforced per-task by the
  orchestrator, not by this generic hook.

### Status line

```json
"statusLine": {
  "type": "command",
  "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/statusline.py\""
}
```

`statusline.py` reads the session JSON on stdin and prints one line: the model
display name, plus — when an orchestrator run exists — the live state of the
most-recently-modified feature read from `work/<feature>/.runs/state.json`. Pure
stdlib, read-only, never raises. Full output format and glyphs:
[status-line.md](status-line.md).

### Permission denies

`settings.json` also denies all `Write`/`Edit`/`MultiEdit`/`NotebookEdit`
operations matching `**/.approvals/**` and `**/.runs/**` (those directories are
written only by the orchestrator, not by agents).

## See also

- [../explanation/architecture.md](../explanation/architecture.md) — how agents, hooks, and the orchestrator fit together.
- [../how-to/run-the-orchestrator.md](../how-to/run-the-orchestrator.md) — driving a run.
- [../how-to/evaluate-models.md](../how-to/evaluate-models.md) — model ↔ role evaluation.
- [commit-format.md](commit-format.md) — the canonical commit format the `commit` skill and orchestrator emit.
