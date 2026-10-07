# Static vs dynamic context — a versioned boundary

> Diátaxis: **explanation**. Why the lab treats the static/dynamic context split as a
> design decision, not an accident. Mechanism: `lab/engine/context_budget.py`
> (`just context-budget`). Decided in work/sdlc-rework (ADR-2, ADR-4), prompted by the
> *New SDLC With Vibe Coding* whitepaper (May 2026).

## The problem

Every agent call pays for its **static context** on every turn: `CLAUDE.md`, the role's
`.md` under `.claude/agents/`, and (for models on a non-`base` profile) the injected
profile from `lab/models/profiles/`. This payload has a natural ratchet: the standard
remedy when an agent misbehaves is *add a rule*, and rules only ever accumulate. Too much
static context wastes tokens **and dilutes signal** — the rules that matter drown among
the ones that rarely apply.

**Dynamic context** is loaded only when needed: skills (`.claude/skills/`, progressive
disclosure), tool results, files the agent reads. It costs nothing on the turns that
don't use it.

## The rule

Where a piece of knowledge lives is a **first-class, versioned decision**:

| Belongs in static (CLAUDE.md / role `.md`) | Belongs in dynamic (skill / doc / reference) |
|---|---|
| Hard rules that bind EVERY task (eval gate, human checkpoints, brand guard) | Procedures used on explicit occasions (`/commit`, `/diataxis`, workshop) |
| The vocabulary any agent needs to parse the triplet | Deep reference material (commit-format details, model-eval how-to) |
| Chain-of-command constraints | Anything an agent can `Read` when its task calls for it |

Demotion is the default direction: when a static rule is only exercised by one kind of
task, it becomes a skill. The precedents are `commit` and `diataxis` — both started as
prose rules, both are skills today, both are referenced (one line each) from CLAUDE.md.

## The counterweight

`just context-budget` prints the measured static payload per role (chars/4 heuristic —
a *relative* number, which is all a budget needs; no tokenizer dependency). It gates
nothing until the Owner declares `[context] max_static_tokens` in
`lab/models/registry.toml` — same fusible philosophy as `content_guard`: the mechanism
first, enforcement by explicit opt-in. Once declared, a PR that inflates the static
payload past the budget fails, and the author must either demote content to dynamic or
bump the budget in the same commit (which the reviewer sees).
