# Ingest raw client inputs into the three artifacts

The business rarely hands you a spec. It hands you **raw material** — slides, meeting
transcripts, existing quotes, schemas, screenshots. Those live in a per-feature bucket:

```
work/<feature>/assets/      (or work/<domain>/<feature>/assets/)
├── kickoff-transcript.md
├── current-pricing.xlsx
└── screens/…
```

During the early iterations (typically the [spec workshop](../../.claude/skills/vibe-workshop/SKILL.md)),
you read `assets/` and turn it into the structured triplet — `spec.md`, `design.md`,
`tasks.md`. The assets are the *source*; the triplet is the *derived contract*.

## `assets/` is gitignored by default

`work/**/assets/` is **not versioned** (see `.gitignore`):

- raw client inputs are often **sensitive/confidential** data;
- the lab template stays **generic / org-neutral** — client material does not belong in
  its history;
- what gets committed is the **derived** spec/design/tasks, which carry the decisions.

A deployment that wants its assets versioned (for full reproducibility) opts in by
editing that `.gitignore` rule — that is a per-deployment choice, not a template default.

> **`assets` is a reserved directory name.** Because `work/**/assets/` is gitignored,
> do not name a feature or a domain `assets` — a `work/assets/` or `work/<domain>/assets/`
> feature directory would be silently ignored. Pick any other name.

## Brand names in assets are fine

The [brand guard](../reference/cli.md#brand_guardpy) deliberately **excludes** `assets/`
(and `work/`) from its scan: raw client inputs legitimately carry client and product
names. The rule binds the generic framework, not its usage.

## Workflow

```bash
mkdir -p work/<feature>/assets
# drop the raw inputs in (they stay local, gitignored)
cp ~/Downloads/kickoff.txt work/<feature>/assets/

# then author the triplet from them — in the spec workshop, or by asking an agent:
#   "read work/<feature>/assets/, draft work/<feature>/spec.md per lab/templates/spec.md,
#    and list the open questions you could not resolve from the inputs."
```

The triplet you commit should stand on its own: a reader (or an agent) must understand
the feature from `spec.md` without needing the assets. If an asset holds a decision the
spec doesn't, that decision belongs **in the spec**.
