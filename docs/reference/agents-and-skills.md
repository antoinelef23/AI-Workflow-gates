# Agents & Skills Reference

Austere lookup of the kit's plugin `fde-kit` (`lab/plugin/`): sub-agents
(`lab/plugin/agents/*.md`), skills (`lab/plugin/skills/*/SKILL.md`), hard rules
(`lab/plugin/rules/hard-rules.md`), and the hook + status-line wiring
(`lab/plugin/hooks/hooks.json`, `lab/plugin/hooks/*.sh`, `lab/plugin/statusline.py`).
The repo has no `.claude/` directory.

## Plugin layout

```
lab/plugin/
├── .claude-plugin/plugin.json   # name = fde-kit, version = package version
├── agents/                      # the 5 sub-agents
├── skills/                      # vibe-workshop, commit, diataxis
├── hooks/                       # hooks.json + the scripts it calls
├── rules/hard-rules.md          # single source of the hard rules (method, vocabulary)
└── statusline.py
```

The repo root holds `.claude-plugin/marketplace.json` (one entry, source `./lab/plugin`), so the
repo is its own marketplace. Package version = `plugin.json` version = marketplace entry. Interactive
use: install the plugin, or `claude --plugin-dir lab/plugin` when developing the kit. Orchestrated
runs: the engine passes `--plugin-dir`, `--settings lab/engine/run_settings.json` and
`--append-system-prompt <hard-rules.md>` on every agent call (never `--bare`).

For how these pieces orchestrate together, see
[../explanation/architecture.md](../explanation/architecture.md). For usage, see
the how-to guides linked per row.

## Sub-agents

Each file in `lab/plugin/agents/` declares a sub-agent in YAML front matter
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

Each file in `lab/plugin/skills/<name>/SKILL.md` declares a skill in YAML front
matter (`name`, `description`).

| Skill | Purpose | When |
| --- | --- | --- |
| `vibe-workshop` | Facilitates the 105-min Spec Workshop (6-8 people) that produces `spec.md` v1.0; Claude mediates over screen share and writes the spec live. | The PE kicks off a spec workshop with the business. |
| `commit` | Writes a git commit whose body records WHY the change exists (workshop decision, resolved OQ, trade-off), in the lab's canonical format; honors the `content_guard` fusible (substance change ⇒ `version:` bump). | Committing artifact or code changes in the lab. See [commit-with-rationale.md](../how-to/commit-with-rationale.md) and [commit-format.md](commit-format.md). |
| `diataxis` | Organizes/creates docs by the Diátaxis method: classifies pages into tutorials/how-to/explanation/reference, identifies gaps, applies category templates. | Writing or restructuring `docs/`. |

## Hooks & status line

Declared in `lab/plugin/hooks/hooks.json`; every command is referenced through
`${CLAUDE_PLUGIN_ROOT}` (e.g. `bash "${CLAUDE_PLUGIN_ROOT}"/hooks/eval_gate.sh`), so it resolves
wherever the plugin is installed. The status-line script is `lab/plugin/statusline.py`.

### Hooks

| Event | Matcher | Script | Fires on / behavior |
| --- | --- | --- | --- |
| `PreToolUse` | `Edit\|Write\|MultiEdit\|NotebookEdit` | `hooks/guard_paths.sh` | Before an edit tool runs. Exits 2 when `tool_input.file_path` is under `.approvals/` or `.runs/`; `"onFailure": "block"` makes a failure of the hook itself blocking (fail-closed). |
| `SessionStart` | (none) | `hooks/session_start.sh` | At session start. Injects `rules/hard-rules.md` into the context (no rules file needed in the instance). |
| `PostToolUse` | `Edit\|Write\|MultiEdit` | `hooks/post_edit.sh` | After an edit/write/multi-edit. Runs `uv run ruff check --fix` then `uv run ruff format` on the modified file if it is `*.py` and `uv` + `pyproject.toml` exist. Informative, always exits 0 (never blocks). |
| `SubagentStop` | (none) | `hooks/eval_gate.sh` | When a sub-agent finishes. The automatic merge gate (see below). |
| `Stop` | (none) | `hooks/eval_gate.sh` | When the main agent finishes. The automatic merge gate (see below). |

Known limit: a write made by a subprocess (a script launched through Bash) is not blocked by
`guard_paths.sh`. The sandbox is the hard boundary (see [../how-to/use-the-sandbox.md](../how-to/use-the-sandbox.md)).

#### `eval_gate.sh` behavior

The merge gate, fired on `Stop` and `SubagentStop`:

- Exits 0 immediately if `stop_hook_active` is true (avoids re-run loops), if neither
  `pyproject.toml` nor `.lab/lab.toml` exists, or if `git status --porcelain --untracked-files=all`
  shows no changed `*.py`/`*.toml` file.
- Otherwise runs `just evals`. Non-zero exit → prints `⛔ EVAL GATE RED` plus the
  last 40 lines of output to stderr and **exits 2** (the agent is sent back to
  fix).
- If `just evals` passes but `uv run pytest -m eval --collect-only` collects zero
  evals, prints a non-blocking `⚠️ eval-gate` warning (green by absence, not by
  success). The hard "no eval = no done" rule is enforced per-task by the
  orchestrator, not by this generic hook.

### Status line

A plugin cannot declare the main status line: wire it once in your **user** settings
(`~/.claude/settings.json`), pointing at the script of the kit checkout or installed plugin:

```json
"statusLine": {
  "type": "command",
  "command": "python3 /path/to/fde-kit/lab/plugin/statusline.py"
}
```

`statusline.py` reads the session JSON on stdin and prints one line: the model
display name, plus — when an orchestrator run exists — the live state of the
most-recently-modified feature read from `work/<feature>/.runs/state.json`. Pure
stdlib, read-only, never raises. Full output format and glyphs:
[status-line.md](status-line.md).

### Permission denies

A plugin cannot carry permission denies. Orchestrated runs get them from
`lab/engine/run_settings.json`, passed with `--settings` on every call:
`Edit(**/.approvals/**)` and `Edit(**/.runs/**)` (no hook in that file). Those directories are
written only by the orchestrator, not by agents. Interactively, `guard_paths.sh` plays that role.

## See also

- [../explanation/architecture.md](../explanation/architecture.md) — how agents, hooks, and the orchestrator fit together.
- [../how-to/run-the-orchestrator.md](../how-to/run-the-orchestrator.md) — driving a run.
- [../how-to/evaluate-models.md](../how-to/evaluate-models.md) — model ↔ role evaluation.
- [commit-format.md](commit-format.md) — the canonical commit format the `commit` skill and orchestrator emit.
