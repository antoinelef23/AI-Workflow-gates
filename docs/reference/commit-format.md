# Commit format — git history is where the "why" lives

The repo is the memory (no Confluence, no Jira). A `version:` bump on an artifact is
only a **tripwire** — it proves a substance change was *intentional*, it does NOT
record *why*. The "why" belongs in the commit message, where `git log` / `git blame`
can recover it forever. This is the single canonical format, honored by **both** the
human `/commit` skill and the orchestrator's `[auto]` commits, so machine and human
history read the same and agents can mine it.

## Shape

```
<type>(<feature>): <node> <title> [ID, ID, …]

Why: <1-3 sentences. The decision, the trigger, the workshop outcome, the OQ that
got resolved — the reasoning a future reader (or agent) needs to NOT re-litigate
this choice. Not "what changed" (the diff shows that) — WHY it changed.>

Spec-IDs: INV-1, BHV-2, EVAL-3
Artifacts: src/devis/calc.py, work/devis-pose/spec.md
Version-Bump: spec.md 1.0.0→1.1.0
Checkpoint: CP-1
Run: auto
```

- **Subject** — `<type>(<feature>): <node> <title> [IDs]`. `type` follows
  [Conventional Commits](https://www.conventionalcommits.org/): feat/fix/docs/style/
  refactor/perf/test/build/ci/chore/revert, picked by the change's *primary intent* (a
  feature shipped with tests is `feat`, not `test`). The orchestrator's `[auto]` commits
  always emit `feat`. Keep the `[IDs]` (or `[auto]`) tag: the reviewer greps subjects for
  spec-ID ↔ diff traceability. ≤ ~72 chars where reasonable.
- **Why** — the prose **body paragraph** (NOT a trailer). Mandatory; this is the whole
  point of the format. Recover it with `git log --format='%b'` (or `%h %s%n%b`), never
  `%(trailers:key=Why)` — Why sits before the trailer block, so git does not treat it as a
  trailer. For an orchestrator `[auto]` commit the Why is auto-generated (`title` +
  `done_when`): the approved task is itself the decision, so its "why" is the task. The
  human `/commit` Why records the live decision / trigger / trade-off.
- **Trailers** — a CONTIGUOUS block of `Key: value` lines at the very end (no blank line
  inside it, and it must be the last paragraph, else git won't parse them). Machine-parsable
  via `git interpret-trailers --parse` or `git log --format='%(trailers:key=Spec-IDs,valueonly)'`:
  - `Spec-IDs:` — the spec IDs this commit implements/touches.
  - `Artifacts:` — the files / 3-artifact docs changed (optional; the diff is authoritative).
  - `Version-Bump:` — **only** when a substance change bumped an artifact: `spec.md 1.0.0→1.1.0`.
    Its presence is the human-readable counterpart of the `content_guard` fusible. By the
    "spec immutable during a task" rule, substance amendments are SEPARATE human commits
    (via `/commit`); so orchestrator `[auto]` task-commits legitimately omit both this and
    `Checkpoint:`, carrying only `Spec-IDs`/`Artifacts`/`Run: auto`. The fusible itself is
    enforced by `content_guard` at the gate (pre-commit + CI), independent of who commits.
  - `Checkpoint:` — the CP this work belongs to, when relevant (human / checkpoint commits).
  - `Run:` — `auto` (orchestrator), `owner` (human via `/commit`), or `human` (hand-edited,
    exceptional — pair with a `Why` justifying the manual line per the "every hand-written
    line is a justified exception" rule).

## How agents recover the why (archaeology)

Before challenging or re-deciding a choice, read the history rather than guessing:

```bash
git log --oneline -- work/<feature>/spec.md           # what amended the contract, when
git log --format='%h %s%n%b' -- src/devis/calc.py     # full message incl. the Why: body line
git blame -L <line>,<line> work/<feature>/spec.md     # who/why on a specific ID line
git log --format='%(trailers:key=Version-Bump,valueonly)' -- work/<feature>/spec.md  # Version-Bump IS a trailer
```

A deliberate prior decision recorded in a `Why:` outranks a fresh guess — surface it,
don't silently override it.
