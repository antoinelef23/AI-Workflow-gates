# AGENTS.md — vendor-neutral entry point

This repository is an **AI-native lab**: applications are (re)built from scratch by
agents, a single Owner drives, evals gate every merge.

Rules live in **one place: [lab/plugin/rules/hard-rules.md](lab/plugin/rules/hard-rules.md)**;
kit specifics are in [CLAUDE.md](CLAUDE.md). This file is deliberately a pointer, not a
copy (work/sdlc-rework ADR-5).

Whatever coding agent you are, before touching anything:

1. Read [CLAUDE.md](CLAUDE.md), then the rules file it points to.
2. For any feature, read its triplet in order: `work/<feature>/spec.md` →
   `design.md` → `tasks.md`.
3. Recover past decisions from git history before re-deciding anything.
