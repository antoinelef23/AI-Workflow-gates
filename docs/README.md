# Documentation

Organized by the [Diátaxis](https://diataxis.fr/) method — four kinds of doc, each
serving a different reader need. Pick by what you're trying to do:

| I want to… | Go to |
| --- | --- |
| **learn** the lab by doing | [Tutorials](#tutorials) |
| **accomplish a task** I already understand | [How-to guides](#how-to-guides) |
| **understand** why things are the way they are | [Explanation](#explanation) |
| **look up** a flag, env var, or format | [Reference](#reference) |

## Tutorials

*Learning-oriented — follow end to end.*

- [Getting started](tutorials/getting-started.md) — from the three artifacts to one merged feature, the smallest complete run.

## How-to guides

*Task-oriented — you know what you want.*

- [Run the orchestrator on a feature](how-to/run-the-orchestrator.md)
- [Organize features by domain](how-to/organize-features-by-domain.md)
- [Ingest raw client inputs into the artifacts](how-to/ingest-client-assets.md)
- [Commit a change with its rationale](how-to/commit-with-rationale.md)
- [Run agents in the sandbox](how-to/use-the-sandbox.md)
- [Automate runs](how-to/automate-runs.md)
- [Evaluate a model for a role](how-to/evaluate-models.md)

## Explanation

*Understanding-oriented — the why and the trade-offs.*

- [Architecture](explanation/architecture.md) — the orchestrator, the DAG/waves/checkpoints, the 3-artifact contract.
- [Git as the project memory](explanation/git-as-memory.md) — why the "why" lives in commits, the fusible vs the rationale.
- [Static vs dynamic context](explanation/static-vs-dynamic-context.md) — the versioned boundary between what every agent call pays for and what loads on demand.
- [OKF evaluation](explanation/okf-evaluation.md) — the knowledge-format spike.

## Reference

*Information-oriented — dry, accurate lookup.*

- [CLI](reference/cli.md) — `orchestrate.py` flags, `just` recipes, helper scripts.
- [Environment variables](reference/environment.md) — every `LAB_*` / sandbox variable.
- [Commit format](reference/commit-format.md) — the canonical commit shape (subject + `Why:` body + trailers).
- [Status line](reference/status-line.md) — what `.claude/statusline.py` shows.
- [Agents & skills](reference/agents-and-skills.md) — sub-agents, skills, hooks.

---

`export-notes.md` and `export-usage.md` at this root are **outputs of the `export-devis`
example feature** (written by its `tasks.md`), not lab documentation — kept here for that
example's integrity.
