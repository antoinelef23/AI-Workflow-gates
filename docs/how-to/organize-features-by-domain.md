# Organize features by domain

By default a feature is a single directory under `work/`:

```
work/<feature>/
├── spec.md      # the WHAT
├── design.md    # the HOW
└── tasks.md     # the DO
```

When a product grows into several **large domains** (say `agent/`, `rag/`, `mcp/`),
you can add an optional domain layer:

```
work/<domain>/<feature>/
├── spec.md
├── design.md
└── tasks.md
```

The **triplet stays the unit of work** — a domain folder is just an organizational
parent. The templates are unchanged; nothing about authoring a spec changes.

## When to introduce a domain layer

Add `work/<domain>/<feature>/` when **both** hold:

- the product genuinely has several stable, separable domains, and
- features within a domain are related enough that grouping aids navigation.

Until then, keep features flat under `work/`. A handful of features does not need
domains.

## When NOT to split

- **Do not split a spec just because it is long.** A spec follows the rule "zero
  ambiguity, every line testable" — a 130-line spec that earns its length is fine.
  Split a spec only when it has become genuinely *incomprehensible*, never by reflex.
- **Do not introduce domains speculatively.** Add the layer when a domain actually
  exists, not in anticipation of one.

## It just works (no engine change needed)

The engine is depth-agnostic — flat and nested features behave identically:

- the orchestrator takes the feature directory as its argument
  (`python3 lab/engine/orchestrate.py work/agent/booking`);
- `just check-content` / `ci_checks.sh` and the pre-commit hook find the feature as
  the nearest ancestor of a changed file that holds a `spec.md`;
- the status line discovers runs recursively and labels them `domain/feature`.

## Create a nested feature

```bash
mkdir -p work/agent/booking
cp lab/templates/spec.md   work/agent/booking/spec.md
cp lab/templates/design.md work/agent/booking/design.md
cp lab/templates/tasks.md  work/agent/booking/tasks.md
# … fill them in, then:
python3 lab/engine/orchestrate.py work/agent/booking --validate
```
