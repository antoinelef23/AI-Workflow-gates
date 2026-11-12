# Activate the kit on a client project (an instance)

> Diátaxis: **how-to**. Goal: from a machine with the kit to a first orchestrated run on a
> client repo, without putting any agent tooling in that repo.

The kit ships as **one package, one version** (`fde-kit`): the `lab` CLI + engine, and the Claude
Code plugin (agents, skills, hooks, hard rules). The client project (the *instance*) receives
only project data: `.lab/lab.toml`, `work/`, and the `evals` recipes of its justfile. Nothing under
`.claude/`, no `CLAUDE.md`, no `AGENTS.md`.

## Prerequisites

- `uv`, `git`, `just`, and the `claude` CLI (authenticated).
- A git repo for the client project.
- The kit repo URL and the version tag to use (`v<x.y.z>`).

## 1. Install the CLI

```bash
uv tool install git+<kit repo URL>@v<x.y.z>
lab version        # prints x.y.z
```

Pin an exact tag: the instance will pin the same version (step 3), and a run refuses to start if
the two differ.

## 2. Install the plugin (interactive sessions)

The kit repo is its own plugin marketplace (`.claude-plugin/marketplace.json`, source
`./lab/plugin`). In Claude Code:

```
/plugin marketplace add <kit repo URL>
/plugin install fde-kit@fde-kit-marketplace
```

Install the same version as the CLI. With the plugin enabled, a session opened in the instance gets
the hard rules (SessionStart hook), the path guard, the eval gate on `Stop`/`SubagentStop`, and the
agents and skills — with no rules file in the instance.

Optional: wire the status line once in your *user* settings (a plugin cannot declare the main
status line) — see [status-line.md](../reference/status-line.md).

## 3. Activate the instance

```bash
cd <client repo>
lab init . --profile squad --dry-run   # shows the plan, writes nothing
lab init . --profile squad
```

`--profile` is mandatory (`solo`, `squad` or `regulated`); in iteration 1 the value is only
recorded. `lab init` lists every file it creates: `.lab/lab.toml` (with `kit_version` pinned to the
installed version), `work/README.md`, `work/_templates/*.template.md`, and the `evals` /
`evals-collect` justfile recipes if absent (an existing `evals` recipe is kept as is). It never
overwrites, and a second run reports "0 changement". Commit the result: that commit is the pin.

A non-Python project with no evals gets recipes that **fail closed** ("no evals configured"):
define `evals` and `evals-collect` before the first run.

## 4. First orchestrated run

Write the triplet under `work/<feature>/` (see [getting started](../tutorials/getting-started.md)),
get the plan approved, then from any directory:

```bash
lab validate <feature> --project <client repo>       # plan-lint
lab run <feature> --project <client repo> --dry-run  # preview
lab run <feature> --project <client repo>
```

On every agent call the engine passes the plugin (`--plugin-dir`), the run settings (the denies on
`.approvals/` and `.runs/`) and the hard rules (`--append-system-prompt`), so the guardrails apply
even though the instance has none of them. Pre-flight stops with rc 1 if the kit root cannot be
resolved, `lab/plugin/` is missing, the `claude` CLI is too old, or the installed kit version is not
the one pinned in `.lab/lab.toml` (message `plugin X ≠ pinned kit Y`). To upgrade: install the new
tag, bump `kit_version` in `.lab/lab.toml`, and commit.

## Sandbox with an external instance

`LAB_RUNNER=sandbox` together with `--project` is **refused** until iteration 2
(`sandbox + external instance not supported before iteration 2`): the container mounts only the
working directory, so it cannot see the kit. The refusal keeps the guardrails guaranteed. The sandbox
still works in kit mode (no `--project`); see [use-the-sandbox.md](use-the-sandbox.md).

## Developing the kit itself

This repo has no `.claude/`: the kit is developed with its own plugin.

```bash
claude --plugin-dir lab/plugin
```

Without that flag a session here has none of the guardrails or hard rules. The hard rules live once,
in `lab/plugin/rules/hard-rules.md`; `CLAUDE.md` only holds what is specific to the kit repo.

## See also

- [CLI reference](../reference/cli.md) — `lab init|run|validate|version`, `.lab/lab.toml`, `LAB_ROOT`.
- [Agents, skills & hooks](../reference/agents-and-skills.md) — the plugin layout and hook wiring.
- [Run the orchestrator](run-the-orchestrator.md).
