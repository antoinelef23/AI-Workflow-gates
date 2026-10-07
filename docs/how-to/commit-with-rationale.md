# How to commit a change with its rationale

This guide shows you how to land a change in git so its **reasoning** travels with it.
The repo is the lab's memory: the diff already records *what* changed, so your job is to
record *why* — the decision, the trigger, the resolved OQ — where `git log` and `git blame`
recover it forever. It operationalizes the `/commit` skill for a human driving by hand.

For the exact message shape and the trailer grammar, this guide defers to the
[commit-format reference](../reference/commit-format.md) — do not re-derive it here.

## Prerequisites

- A working tree with the change you intend to commit (code, artifact, or both).
- `just` and `python3` available (the fusible runs through `lab/engine/content_guard.py`).
- You know which `work/<feature>/` the change belongs to.

## Steps

### 1. Stage only the intended scope

Never `git add -A`. Inspect first, then stage exactly the files this one coherent change
touches:

```bash
git status --short
git diff                       # working tree, to confirm what you're about to stage
git add <only the files for this change>
git diff --cached              # re-read what is now staged — this is what ships
```

If the staged diff spans unrelated reasons, split it into separate commits — one coherent
change per commit.

**Never commit these generated/scratch paths** even if they show up as untracked:
`deploy/.last-url`, `sbom.json`, `work/repartition/`, `work/webhook-*/`. They are run
outputs, not source. If they appear under your `git add`, you staged too broadly.

### 2. Derive the Spec-IDs

Collect every `INV/BHV/EX/EVAL/NG/OQ/ADR` the diff implements or touches. Grep both the
diff and the artifact, and only keep IDs that actually exist in `spec.md` — do not invent
IDs:

```bash
git diff --cached | grep -oE '(INV|BHV|EX|EVAL|NG|OQ|ADR)-[A-Za-z0-9]+' | sort -u
grep -oE '(INV|BHV|EX|EVAL|NG|OQ|ADR)-[A-Za-z0-9]+' work/<feature>/spec.md | sort -u
```

These IDs go in the subject's `[…]` tag and the `Spec-IDs:` trailer. The reviewer agent
greps the subject for them, so keep the tag (`[BHV-3, INV-2]`, or `[auto]` for orchestrator
commits) even when the body already lists them.

### 3. Run the fusible if a spec or design changed substantively

The "fusible" is the substance-vs-form guardrail. If a *substance* line of `spec.md` or
`design.md` changed — an ID assertion (INV/BHV/EX/EVAL/NG/OQ/ADR and its continuation
lines), a canonical glossary name, or a KPI number — the artifact's `version:` MUST be
bumped in this same commit. Reformatting that leaves substance untouched (table↔list,
bold, reordered prose, rewording) needs **no** bump.

Verify mechanically before committing. The recipe takes the feature directory:

```bash
just check-content work/<feature>
# under the hood: python3 lab/engine/content_guard.py --git work/<feature>/spec.md
#                 (and design.md if present), comparing the working tree to HEAD
```

- `✅ … substance identical` — form-only change, no bump needed. Proceed.
- `✅ … version bumped (X → Y): amendment assumed, OK` — you bumped `version:`; the
  amendment is recorded. Proceed and note it in the `Version-Bump:` trailer.
- `⛔ the SUBSTANCE changed WITHOUT a version bump` — defect, not something to commit
  around. Either bump `version:` (if the amendment is intentional) or restore the substance
  and keep only the formatting. Re-run until it passes.

Note that `--git` compares against HEAD, so run it *before* you commit. Bump in the **same
commit** as the substance change — never weaken the fusible by deferring it.

### 4. Write a real Why

One to three sentences of reasoning, in this order of value: the live session/workshop
decision you just made; the OQ resolved / ADR applied / trade-off taken; or — for a
hand-written, non-generated line — the justification that makes it a deliberate exception.

Write *why it changed*, not *what changed* (the diff already shows what).

- **Bad** — `update calc.py` (restates the diff, recovers nothing).
- **Good** — `BHV-2a was ambiguous on the exact-threshold case; the workshop ruled
  strictly-greater (a €X order is below the tier), so the discount predicate uses > not >=.`

### 5. Compose and commit per the reference format

Build the message exactly as specified in
[reference/commit-format.md](../reference/commit-format.md): subject
`type(feature): node title [IDs]`, a blank line, the `Why:` body paragraph, a blank line,
then the contiguous trailer block (`Spec-IDs:`, `Artifacts:`, `Version-Bump:` if any,
`Checkpoint:` if any, `Run: owner`). The `Why:` is a body paragraph, **not** a trailer —
keep it before the trailer block. Use `Run: owner` for a human `/commit`.

Then commit, preserving the multi-line body:

```bash
git commit -m "$(cat <<'EOF'
fix(devis-pose): T4 threshold predicate [BHV-2a]

Why: BHV-2a was ambiguous on the exact-threshold case; the workshop ruled
strictly-greater (a €X order is below the tier), so the discount predicate
uses > not >=.

Spec-IDs: BHV-2a
Artifacts: src/devis/calc.py
Run: owner
EOF
)"
```

Do not add a Claude/AI co-author trailer unless your global git convention requires it,
and do not push unless asked.

## Troubleshooting

### `just check-content` reports a substance change you didn't intend

You altered a fingerprinted element (an ID assertion, a glossary name, or a KPI) while
trying to only reformat. Diff the artifact against HEAD, restore the substance, and keep
only the formatting — then re-run.

### `git log --format='%(trailers:key=Why)'` returns nothing

That is expected. `Why:` is a body paragraph, not a trailer. Recover it with
`git log --format='%h %s%n%b'`. `Version-Bump:` and `Spec-IDs:`, by contrast, *are*
trailers and are recoverable with `%(trailers:key=…)`.

### You staged a never-commit path by accident

Unstage it before committing: `git restore --staged <path>` (e.g. `deploy/.last-url`,
`sbom.json`, `work/repartition/`, `work/webhook-*/`).

## See also

- [reference/commit-format.md](../reference/commit-format.md) — the canonical message shape, trailer grammar, and how agents recover the why.
- [explanation/git-as-memory.md](../explanation/git-as-memory.md) — why the repo is the memory and the reasoning belongs in git.
