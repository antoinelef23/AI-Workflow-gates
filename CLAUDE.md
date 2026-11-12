# CLAUDE.md — AI-Native Lab

## Context

An AI-native development lab. Applications are (re)built from scratch with an agentic workflow. A single Owner drives, agents write the code, a human validates. Every hand-written line of code is a justified exception, recorded in the commit.

## The method — hard rules live in one place

The method (the 3 artifacts `spec.md` / `design.md` / `tasks.md`, the hard rules, the vocabulary) is
written **once**, in [`lab/plugin/rules/hard-rules.md`](lab/plugin/rules/hard-rules.md) — the kit's single
source (design ADR-3). The plugin injects it in every interactive session (SessionStart hook) and the
engine appends it to every orchestrated agent call; this file does **not** restate it. Read that file
first, then the sections below, which are specific to the kit repo.

## Conventions

- Python 3.12+, `uv` for dependencies, `ruff` for lint/format, `pytest` for tests, `pytest -m eval` for evals.
- **New dependency = `uv lock` in the same commit**: installs are hash-pinned (`uv sync --locked`) and the gate asserts lockfile freshness (`just check-lock`, wired into `gate`/`gate-ci`) — a dep cannot appear without a reviewable `uv.lock` diff, and a nonexistent (hallucinated) package fails resolution outright.
- FastAPI for services, Pydantic v2 for data contracts.
- Markdown + Git for every artifact. No Confluence, no Jira: the repo is the memory.
- Language (**supersedes** the English-only rule that issue #12 originally set): **French and English are both allowed throughout the repo** — code, technical docs, and artifacts alike. Write in whichever language serves the reader best; bilingual is fine, and a French docstring next to English code is acceptable. Two *soft* preferences (never gates): keep public identifiers and user-facing error strings readable to a non-French engineer where that costs nothing, and keep a single artifact internally consistent. The one **hard** rule that stays enforced: **no client or brand proper nouns** anywhere committed — the lab is generic / org-neutral, so the de-branding (client names, internal product names) is permanent even though the language constraint is relaxed.

  This rule is **mechanical**: `lab/engine/brand_guard.py` (`just check-brand`, wired into `gate`/`gate-ci` and the pre-commit hook) scans committed framework content against a denylist (`lab/engine/brand_denylist.txt` — the one sanctioned home for the names, excluded from its own scan). **Scope** — the rule binds the lab *itself*, not its *usage a posteriori*: kit-root `work/**` (real features built with the lab) and `**/assets/**` (raw client inputs) legitimately carry brand names and are **excluded**; `examples/**` ships with the kit and **is scanned** (ADR-9: the demo instances must stay generic). Never add a lab spec-ID prefix (INV/BHV/EX/EVAL/NG/OQ/ADR) to the denylist — those are vocabulary, not brands.

## Agents & skills

The kit's agents and skills ship as a Claude Code plugin under `lab/plugin/` (ADR-1, ADR-3); there is no `.claude/` in this repo. To work on the kit with its own tooling, start the session with `claude --plugin-dir lab/plugin` — without it a session here has none of the guardrails or rules.

Sub-agents in `lab/plugin/agents/`: `design-scout`, `planner`, `implementer`, `eval-runner`, `reviewer`. Their orchestration is described in README.md and in each tasks.md.

Skills in `lab/plugin/skills/`: `vibe-workshop` (facilitates the spec workshop), `commit` (writes the canonical why-in-git commit — see `docs/reference/commit-format.md`), `diataxis` (organizes/creates docs by the Diátaxis method — use it when writing or restructuring `docs/`). The status line (`lab/plugin/statusline.py`) surfaces the live orchestrator run state; a plugin cannot declare the main status line, so the FDE wires it once in their user settings (OQ-9).

## Models

Model ↔ role assignment lives in `lab/models/registry.toml` (data-driven source of truth), overridable per task via `**model :**`. The production assignment (`[roles]`) changes only on measured proof from the `lab/engine/eval_models.py` harness (scorecard + behavioral + chain-of-command). A chain-of-command violation is eliminatory for the role, whatever the raw score. Re-evaluation loop on every new model: `lab/models/EVOLUTION.md`.
