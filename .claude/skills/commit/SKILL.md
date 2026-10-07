---
name: commit
description: Writes a structured git commit whose body records WHY the change exists (the workshop decision, the resolved OQ, the trade-off), not just what changed. Grounded in the Conventional Commits spec and commit-message best practices, adapted to the lab's canonical format. Use when committing artifact or code changes in the AI-Native Lab so the reasoning lands in git history where agents can mine it. Honors the content_guard fusible (substance change ⇒ version bump). Same format as the orchestrator's auto-commits.
---

# /commit — put the "why" in git

You help the user commit their staged (indexed) changes following the
[Conventional Commits](https://www.conventionalcommits.org/) spec and commit-message best
practices, expressed in the lab's **canonical format** (`docs/reference/commit-format.md`).
The repo is the memory: the diff already says *what* changed — your job is to capture
*why*, so a future reader or agent recovers the reasoning with `git log` instead of
re-litigating the choice.

## Pre-flight checks

Before crafting a message, always:

1. **`git status --short`** — see what is staged.
2. **`git diff --cached`** (and `--stat`) — review the actual staged changes; never guess.
3. **`git log --oneline -50`** — confirm the repo's type/scope conventions (here: the
   canonical format below).
4. **If nothing is staged**, stage only the intended scope — **never `git add -A`**. In
   this repo the untracked `deploy/.last-url`, `sbom.json`, `work/repartition/`,
   `work/webhook-*/` must never be committed. If scope is ambiguous, confirm with the user.
   Do not create an empty commit.

## The canonical format (output shape)

```
<type>(<feature>): <node> <title> [ID, ID, …]

Why: <1-3 sentences. The decision, the trigger, the workshop outcome, the OQ that got
resolved — the reasoning a future reader or agent needs in order NOT to re-litigate this
choice. Not "what changed" (the diff shows that) — WHY it changed.>

Spec-IDs: INV-1, BHV-2, EVAL-3
Artifacts: src/devis/calc.py, work/devis-pose/spec.md
Version-Bump: spec.md 1.0.0→1.1.0
Checkpoint: CP-1
Run: owner
```

- **Subject** — `<type>(<feature>): <node> <title> [IDs]`. Keep the `[IDs]` (or `[auto]`)
  tag — the reviewer greps subjects for spec-ID ↔ diff traceability.
- **Why** — a prose **body paragraph** (NOT a trailer), separated by a blank line.
  Mandatory; this is the whole point of the format.
- **Trailers** — a contiguous `Key: value` block at the very end (no blank line inside it).

See `docs/reference/commit-format.md` for the authoritative spec and the archaeology
commands that recover the why later.

### Types

| Type | When to use |
| ---------- | ---------------------------------------------------- |
| `feat` | A new feature or capability |
| `fix` | A bug fix |
| `docs` | Documentation-only changes |
| `style` | Formatting, whitespace — no logic change |
| `refactor` | Code restructuring without behavior change |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `build` | Build system or dependency changes |
| `ci` | CI/CD configuration changes |
| `chore` | Maintenance (deps, tooling, config) |
| `revert` | Reverting a previous commit |

The type reflects the **primary intent**, not every file touched: a feature that ships
with tests is `feat`, not `test`; a fix that includes a refactor is `fix`. Comment-only
changes are `style`/`chore` — never `feat`/`fix`.

### Subject / title rules

- **Imperative mood, lowercase, no trailing period**: "add discount predicate", not
  "Added…" / "adds…".
- Complete the sentence "If applied, this commit will _\<title\>_".
- Keep the whole subject ≤ ~72 chars where reasonable.
- **feature** = the `work/<feature>/` the change belongs to (or the repo area for infra).
- **node** = the task/checkpoint id (`T3`, `CP-1`) when this maps to one; else omit.

## Step 1 — Analyze the staged changes

Identify what changed and its purpose, whether this is one logical change or several
unrelated ones, and the primary intent (feature, fix, refactor, docs…).

## Step 2 — Check for multiple logical changes

If the staged diff spans **unrelated** reasons, tell the user and suggest splitting for a
cleaner history. Classify into tidying / infrastructure-build / feature / fix / docs, keep
dependency manifests with their lock files, and suggest an order that tells a story
(tidying → docs → infra → feature/fix last). Let the user decide whether to split or
proceed as one commit. One coherent change — one `Why:` — per commit.

## Step 3 — Derive the lab facts

- **Spec-IDs** — every `INV/BHV/EX/EVAL/NG/OQ/ADR` the diff implements or touches. Grep the
  diff and the artifact for them; don't invent IDs absent from `spec.md`.
- **Version bump?** — did a *substance* line (an ID assertion, glossary name, KPI) of
  `spec.md`/`design.md` change? If yes the artifact's `version:` MUST be bumped in this
  same commit, recorded in `Version-Bump:`. Verify mechanically: `just check-content` (or
  `python3 lab/engine/content_guard.py --git work/<feature>/spec.md`) must pass. If it fails,
  substance changed without a bump — fix that **before** committing; never weaken the fusible.

## Step 4 — Write the WHY (the actual point)

One to three sentences of reasoning. Sources, in order of value:

1. The workshop / session context you're in (what the Owner just decided and why).
2. The OQ being resolved, the ADR being applied, the trade-off being made.
3. For a hand-written (non-generated) line: the justification that makes it a *deliberate*
   exception ("every hand-written line is a justified exception, recorded in the commit").

Write *why it changed*, not *what changed*. Bad: "update calc.py". Good: "BHV-2a was
ambiguous on the exact-threshold case; the workshop ruled strictly-greater (a €X order is
below the tier), so the discount predicate uses `>` not `>=`."

## Step 5 — Present and confirm

Show the complete message and wait for approval before committing. Adjust if the user wants
changes.

## Step 6 — Commit

```bash
git commit -m "$(cat <<'EOF'
<the full composed message>
EOF
)"
```

- **Never** `--no-verify` — respect pre-commit hooks (incl. `content_guard`). If a hook
  fails, investigate and fix, then commit again.
- **Never** `--amend` unless the user explicitly asks.
- Do **not** add a Claude/AI co-author trailer (the lab convention forbids it).
- Do not push unless asked.
- After committing, `git status` to confirm.

## Fixup commits

When the user signals a fixup ("this is a fixup", "attach to the previous commit"):

1. **Find the branch boundary** — `git log --oneline $(git merge-base HEAD origin/main)..HEAD`.
   Only commits in this range may be targeted; never rewrite history shared with `main`.
2. **Identify the target** — `git log --oneline $(git merge-base HEAD origin/main)..HEAD -- <files>`,
   pick the commit whose subject best matches. **Guardrail**: if the target is not in the
   branch range (it's on `main` or earlier), do **not** fixup — tell the user and make a
   normal `fix`/`ci`/… commit instead.
3. **Create it** — `git commit --fixup <target-sha>` (yields `fixup! <original subject>`).
4. **Ask about autosquash** — "Autosquash it into the target now?"
5. **If yes** — `GIT_SEQUENCE_EDITOR=true git rebase --autosquash $(git merge-base HEAD origin/main)`.
   Never rebase beyond the merge-base.
6. **If no** — leave the fixup for a future rebase.

## Guardrails & anti-patterns

- **Never commit secrets** (`.env`, `*.pem`, tokens, credentials) — warn and suggest
  unstaging if any are staged.
- Never weaken the fusible: a substance change without a `version:` bump is a defect, not a
  thing to commit around.
- Keep the subject's `[IDs]`/`[auto]` tag — the reviewer greps it for traceability.
- The `Why:` is mandatory and is a body paragraph, never a trailer.
- Avoid uninformative subjects: `fix: fix bug`, `update code`, `WIP`, `misc changes`.
  Describe the actual change in imperative mood instead.
