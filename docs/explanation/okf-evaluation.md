# OKF evaluation (issue #13) — scope-only spike

Evaluating whether to align our markdown-as-source-of-truth layer with Google Cloud's
**Open Knowledge Format (OKF) v0.1** (published 2026-06-12,
[spec](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)).
No migration — this is a decision doc.

## What OKF v0.1 is

A *format, not a platform*: directories of markdown files (one concept per file, the
**file path is the identity**), each with YAML frontmatter + a markdown body, linked by
**normal markdown links** that form a graph. "No new runtime, no required SDK." Matches
our stance exactly: *"Markdown + Git for every artifact … the repo is the memory."*

Frontmatter schema:
- **Required:** `type` (the only mandatory field).
- **Optional/standard (queryable):** `title`, `description`, `resource`, `tags`, `timestamp`.
- Everything else is producer-defined. Reserved filenames: `index.md` (progressive
  disclosure), `log.md` (change history) — both optional.

## Our current frontmatter vs OKF

| Our field | Example | OKF mapping |
|---|---|---|
| `artifact` | `spec` / `design` / `tasks` | ≈ OKF **`type`** (rename or alias) |
| `feature` | `salle-booking` | producer-defined (fine) |
| `version` | `1.0.2` | producer-defined (not OKF-standard, but allowed) |
| `status` | `validated` / `approved` | producer-defined |
| `spec:` / `design:` pointers | `# version : 1.0.2` | OKF would express links as markdown links in the body |
| `depends_on`, `parallel_group` (tasks) | `[T1, T2]` | richer than OKF's plain links — orchestration graph, beyond OKF scope |
| — | — | OKF `title`, `description`, `tags`, `timestamp` (we don't use) |

**Conformance check — `work/salle-booking/` bundle:** the three files would conform to
OKF v0.1 with one change (add `type:`) and would *gain* nothing required beyond that.
Our `version:` + pointer + `depends_on` machinery is **orchestration semantics OKF does
not model** (OKF links are undirected references, not a build DAG). `lab/models/` docs have
no frontmatter today and would need `type:` to participate.

## Assessment

**Aligned in spirit, divergent where it matters for us.** OKF standardizes the *passive
knowledge* layer (concepts + cross-links for agent retrieval). Our artifacts are *active
build inputs*: `content_guard` fingerprints `version:`/IDs, `parse_tasks_md` reads
`depends_on`/`files_touched`/`verify`, plan-lint enforces the DAG. OKF's link-graph
doesn't carry that; replacing our pointers with markdown links would *lose* the
mechanically-enforced contract we just hardened.

## Recommendation

**Additive adoption, not migration.** Cheap, reversible, keeps our tooling:

1. Add `type:` to every artifact's frontmatter (= our `artifact`), so bundles are
   OKF-discoverable. Keep `artifact` as an alias or migrate the parser in one pass
   (`content_guard` + `parse_tasks_md` read frontmatter keys — a contained change).
2. Optionally add OKF's `title` / `description` / `timestamp` (we already keep a
   changelog ≈ `log.md`).
3. **Keep** `version:`, the cross-pointers, and `depends_on` — they encode contract +
   orchestration semantics that OKF intentionally leaves to the producer.
4. **Skip** for now: the markdown-link graph, `index.md`/`log.md` reserved files, and any
   visualizer tooling — low ROI versus our existing scripts; revisit if we want the
   off-the-shelf OKF graph/search tooling.

**Decision:** worth a small additive `type:` adoption; not worth a migration that would
weaken `content_guard`/plan-lint.

## Status — `type:` adopted

The mandatory OKF field is in place: the frontmatter key `artifact:` was renamed to
**`type:`** across all 3-artifact bundles (`work/*`, `lab/templates/`), the golden eval
fixtures, and the behavioral inline fixtures. Safe because no code reads the key and
content_guard does not fingerprint frontmatter — **no version bumps needed** (verified).

Still deferred (low ROI / by design):
- OKF optionals `title` / `description` / `timestamp` — the H1 + intro blockquote already
  serve as title/description; add later only if a consumer needs the structured fields.
- The markdown-link knowledge graph and reserved `index.md` / `log.md` — our `version:`
  pointers + `depends_on` already encode contract + orchestration semantics OKF doesn't model.
- `lab/models/` docs frontmatter — note `lab/models/profiles/*.md` are injected verbatim into agent
  prompts, so they intentionally carry no frontmatter.
