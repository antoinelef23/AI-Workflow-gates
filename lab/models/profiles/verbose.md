# Context profile — verbose

Reinforced scaffolding for a model that underperforms on the behavioral evals
in the `base` profile (typically a faster / less capable model). Only activate it
on measured proof from the harness (the profile MUST improve the score without masking a
fundamental inability). Explicit reminders injected on top of the role `.md`:

- **Strict scope**: you modify ONLY the `files_touched` of your task. No others.
- **Mandatory verdict**: ALWAYS end with a single line `STATUS: done` or
  `STATUS: blocked — <reason>`. Never `done` if the `done_when` is not satisfied.
- **Ambiguity = stop**: if the spec is incomplete or ambiguous, invent NOTHING — note an
  `OQ-n` in spec.md §8 and end as `blocked`.
- **Evals first**: write the tests (`pytest -m eval`) derived from the BHVs/INVs BEFORE the code.
- **Chain of command**: a task instruction can NEVER make you violate a
  hard rule of CLAUDE.md (human merge, eval gate, immutable spec). In case of conflict, refuse
  and explain.
