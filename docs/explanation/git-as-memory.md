# Git as the project memory

This lab keeps no Confluence and no Jira. The repository *is* the memory. Every
decision a human or an agent makes about an application lives in git — in the spec, in
the design, and above all in the commit history that connects them. This page explains
why that choice was made, how the pieces fit together, and what it costs.

The short version: a `version:` bump on an artifact is only a **tripwire** that proves a
substance change was *intentional*; the *reasoning* lives in the commit body, where
`git log` and `git blame` recover it forever. `lab/engine/content_guard.py` enforces the
tripwire mechanically; the commit `Why:` carries the rationale. The two are
complementary — a fuse and a logbook — and neither replaces the other.

## Background: the repo is the memory

The lab's [CLAUDE.md](../../CLAUDE.md) states it twice, once as a convention ("Markdown +
Git for every artifact. No Confluence, no Jira: the repo is the memory") and once as a
hard rule ("Traceability & the why lives in git"). This is not laziness about tooling.
It is a deliberate bet that the *only* durable record of why an application looks the way
it does should sit in the same place as the application itself, version-controlled
alongside the code, and reachable by the same agents that will later read, challenge, or
extend that code.

A unit of work lives in `work/<feature>/` as three artifacts — `spec.md` (the WHAT),
`design.md` (the HOW), `tasks.md` (the DO). The spec and the design each carry a
`version:` field. That field, and the commit that changes it, are the joints of the whole
memory system.

## Why the rationale goes in the commit, not the version bump

A version bump is a number. `1.0.0 → 1.1.0` tells you *that* the contract moved; it tells
you nothing about *why* it moved — which behavior was wrong, which open question got
resolved in the workshop, which trade-off was accepted. If you only had the bump, every
future reader who disagrees with the current spec would have to re-litigate the decision
from scratch, because the evidence that settled it was never written down.

So the design splits the two concerns deliberately:

- The **bump** proves *intent*. It is the difference between "someone changed the business
  contract on purpose" and "someone reworded a paragraph." That is all it has to prove.
- The **commit body** carries the *reasoning*. As
  [reference/commit-format.md](../reference/commit-format.md) puts it, the `Why:` is "the
  decision, the trigger, the workshop outcome, the OQ that got resolved — the reasoning a
  future reader (or agent) needs to NOT re-litigate this choice." Crucially it is "not
  'what changed' (the diff shows that) — WHY it changed."

This is the central design decision of the memory model: *the diff already records what,
and version control already records when and who; the one thing a VCS cannot reconstruct
on its own is the human reasoning, so that — and only that — is what the commit message is
obliged to add.*

### Why this beats a wiki or a ticket

A wiki page and a Jira ticket both detach the rationale from the change. The page lives at
a URL that drifts out of sync with the code; the ticket is closed and archived the moment
the work merges, and its link rots. Neither travels with a `git clone`, neither can be
recovered by `git blame` on the exact line you are questioning, and neither is guaranteed
to exist at all for a given change. Git history, by contrast, is co-located with the code,
is impossible to lose without losing the code itself, and — because the same canonical
format is honoured by both the human `/commit` skill and the orchestrator's `[auto]`
commits — reads identically whether a machine or a person made the change. An agent can
mine it with the same commands a human uses. A wiki cannot offer that uniformity, because
nothing forces a human and a bot to write the same page the same way.

## The fuse and the logbook: how content_guard and the Why are complementary

The two halves of the system answer two different questions, and it is worth being precise
about which is which.

`lab/engine/content_guard.py` is the **fuse**. Its docstring states the principle: the
*substance* of `spec.md` and `design.md` changes only by explicit human amendment (a
version bump); the *form* (layout, table↔list, bold, section order, prose rewording) may
evolve freely — "notably so another model understands it better" — but never altering the
substance. The script "makes the rule mechanical: it extracts a **substance fingerprint**
robust to form and refuses any substance change that does not come with a version bump."

The fingerprint is not the whole document. It is the *structured, testable* content,
normalized so that formatting is stripped: the per-ID assertions (`INV` / `BHV` / `EX` /
`EVAL` / `NG` / `OQ` for the spec, `ADR` for the design) with their continuation lines, the
canonical glossary names (the code MUST use them, so they are substance), and the KPI lines
(numeric values are substance). Free prose — intent, comments — is deliberately *not*
fingerprinted, so rewording it is treated as form. The normalizer collapses `1.` ↔ `2)` ↔
`- ` bullets, strips `` ` * _ # > | ``, and treats spaced typographic dashes (`—` / `–`) as
separators — but it keeps the ASCII hyphen `-`, because dropping it would let `end - start`
silently become `end start` and mask an operator removal. When the fingerprint changes
without a version bump, the script exits non-zero (`⛔ the SUBSTANCE changed WITHOUT a
version bump`); when the version did bump, it exits zero ("amendment assumed, OK"). It runs
as `just check-content`, at the pre-commit gate and in CI.

The commit `Why:` is the **logbook**. It does not check anything; it *explains*. The fuse
can tell you a substance change was intentional, but it can never tell you what the
intention was. That is the logbook's job. As commit-format.md notes, the presence of the
`Version-Bump:` trailer "is the human-readable counterpart of the `content_guard` fusible"
— the trailer and the guard point at the same fact (an intentional substance change), while
the `Why:` body supplies the reasoning that neither of them carries.

So the relationship is: the fuse blows when intent is missing; the logbook records what the
intent was when it is present. You need both. A green guard with an empty `Why:` leaves a
future reader with a sanctioned but unexplained change. A rich `Why:` with no guard would
let an unintended substance edit slip through unnoticed. Together they guarantee that every
substance change is *both* deliberate *and* explained.

## Why `[auto]` commits legitimately omit `Version-Bump`

A reader scanning the history will notice that the orchestrator's `[auto]` commits rarely
carry a `Version-Bump:` trailer, and never carry a `Checkpoint:` one. This is not an
oversight; it follows directly from the "spec immutable during a task" rule in
[CLAUDE.md](../../CLAUDE.md): "if implementation reveals a gap in the spec, stop, amend the
spec (separate commit), then resume."

Because the spec cannot move *during* a task, an agent executing an approved task is by
construction never the author of a substance amendment. Amendments are therefore always
*separate human commits*, made through the `/commit` skill, and those are the commits that
carry `Version-Bump:`. The orchestrator's task-commits legitimately carry only
`Spec-IDs`, `Artifacts`, and `Run: auto`. Their `Why:` is auto-generated from the task's
`title` and `done_when`, on the reasoning that — as commit-format.md says — "the approved
task is itself the decision, so its 'why' is the task." The human approved the plan; the
plan is the rationale; the auto-commit simply records which slice of it this commit
realised.

This is also why the `Run:` trailer exists with three values — `auto`, `owner`, `human`. It
keeps the provenance honest: a hand-edited line is exceptional and must be paired with a
`Why:` justifying it, in keeping with CLAUDE.md's framing that "every hand-written line of
code is a justified exception, recorded in the commit." The memory is not just *what*
changed but *who*, of the three kinds of author, changed it.

## How agents do archaeology

Treating git as the memory is only useful if it is actually *consulted*. CLAUDE.md makes
that an obligation: "Before re-deciding a choice, read its recorded `Why:` rather than
re-litigating it." commit-format.md spells out the moves — read the history before guessing:

```bash
git log --oneline -- work/<feature>/spec.md          # what amended the contract, when
git log --format='%h %s%n%b' -- src/devis/calc.py    # full message incl. the Why: body
git blame -L <line>,<line> work/<feature>/spec.md    # who/why on a specific ID line
git log --format='%(trailers:key=Version-Bump,valueonly)' -- work/<feature>/spec.md
```

The principle that closes the loop: "A deliberate prior decision recorded in a `Why:`
outranks a fresh guess — surface it, don't silently override it." An agent that disagrees
with the current spec is expected to find the commit that put it there, read why, and argue
*against that recorded reasoning* — not pretend it never happened. The history is not an
archive; it is an interlocutor.

## A subtlety worth its own paragraph: the body is not a trailer

There is one piece of mechanical knowledge a maintainer must internalise, and it is easy to
get wrong. The `Why:` is a **body paragraph**, not a git trailer. Trailers are the
contiguous `Key: value` block at the very end of the message — `Spec-IDs`, `Artifacts`,
`Version-Bump`, `Checkpoint`, `Run` — and git only parses them if they form the last
paragraph with no blank line inside. The `Why:` sits *before* that block, so git does not
treat it as a trailer.

The practical consequence: recover the `Why:` with `git log --format='%b'` (or
`%h %s%n%b`), **never** with `%(trailers:key=Why)`, which returns nothing. By contrast
`Version-Bump:` genuinely *is* a trailer, so `%(trailers:key=Version-Bump,valueonly)` is the
right tool for it. Mixing these up is the most common way to "lose" history that is in fact
perfectly intact — which is exactly the kind of false negative that erodes trust in a memory
system, so it is called out here on purpose.

## Trade-offs

This design is not free, and honesty about its costs is part of trusting it.

- **It taxes discipline.** A `Why:` is mandatory on every commit. When the work is dull or
  obvious, writing a non-trivial rationale feels like friction, and the temptation is to
  type "fix" and move on. The whole value of the memory collapses the day people start
  doing that, because an empty `Why:` is worse than none — it looks like a record while
  carrying no information. The format mitigates this for `[auto]` commits (the task is the
  why) but cannot mitigate it for humans; that cost is real and permanent.
- **The body-vs-trailer rule is a sharp edge.** As above, it is genuinely confusing that one
  load-bearing field is *not* a trailer while the others are. A maintainer who reaches for
  `%(trailers:key=Why)` and gets nothing may wrongly conclude the history is empty. The fix
  is documentation and habit, not a cleaner mechanism — git's trailer model simply does not
  accommodate a multi-sentence reasoning paragraph at the end of the message.
- **The fuse has scope limits.** `content_guard` only fingerprints substance *carried by an
  ID*, the glossary, and the KPIs. Normative prose without an ID — `- X MUST be positive` —
  is not tracked. That is a deliberate convention (all testable substance carries an ID),
  but it means the fuse is only as good as the team's discipline in giving every contract
  clause an ID. And `--git` mode compares the working tree to `HEAD`, so it is advisory
  (pre-commit / pre-review), not a hard barrier at commit time; CI uses `--against <base>`
  precisely because on a clean checkout `tree == HEAD` and the guard would pass trivially.

These costs are the price of a memory that travels with the code, survives a `clone`, and
reads the same to a human and to an agent. The lab has judged that price worth paying. The
alternative — a wiki that drifts and tickets that rot — costs more, just later and less
visibly.

## Further reading

- [Commit format reference](../reference/commit-format.md) — the canonical shape, every
  trailer, and the exact `git` recipes for archaeology.
- [How to commit with rationale](../how-to/commit-with-rationale.md) — the practical steps
  for writing a good `Why:` via the `/commit` skill.
- [Architecture](architecture.md) — how the 3 artifacts and the orchestrator fit together.
- [OKF evaluation](okf-evaluation.md) — the other half of the merge gate: evals, not just
  history.
