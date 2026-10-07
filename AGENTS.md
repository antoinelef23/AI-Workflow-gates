# AGENTS.md — vendor-neutral entry point

This repository is an **AI-native lab**: applications are (re)built from scratch by
agents, a single Owner drives, evals gate every merge.

All rules live in **one place: [CLAUDE.md](CLAUDE.md)** — hard rules, conventions,
vocabulary, agent roster. This file is deliberately a pointer, not a copy: a second
source of truth would drift (work/sdlc-rework ADR-5).

Whatever coding agent you are, before touching anything:

1. Read [CLAUDE.md](CLAUDE.md) in full.
2. For any feature, read its triplet in order: `work/<feature>/spec.md` →
   `design.md` → `tasks.md`.
3. Recover past decisions from git history (`git log --format='%h %s%n%b'`) before
   re-deciding anything.
