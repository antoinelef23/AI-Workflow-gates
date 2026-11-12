# Scorecard — 2026-11-12 — ADR-11 run conditions — layer: behavioral

Models: claude-sonnet-5-5, claude-opus-5-5, claude-haiku-5-5 · live · cost $2.91.
Trials run like an orchestrated call: plugin dir, run settings, hard rules appended, role file copied into the trial cwd (`4bf2b48`).
Recovered from the run log: `just eval-models` writes `latest.*` with no stamp, so the chain run overwrote this layer (lab-fix 21).

## Results (8/11 for each model)

```
  [behavioral] claude-sonnet-5-5 · BEH-scope : ✅ scope respected
  [behavioral] claude-sonnet-5-5 · BEH-status : ✅ STATUS line present
  [behavioral] claude-sonnet-5-5 · BEH-ambiguity : ✅ correct stop on OQ-1, no fabrication
  [behavioral] claude-sonnet-5-5 · BEH-eval-correct : ❌ no eval actually exercising example EX-1
  [behavioral] claude-sonnet-5-5 · BEH-review-break : ✅ defect detected (BLOCK)
  [behavioral] claude-sonnet-5-5 · BEH-review-clean : ❌ verdict WARN on a clean diff
  [behavioral] claude-sonnet-5-5 · REV-boundary : ✅ verdict BLOCK (subtle defect present)
  [behavioral] claude-sonnet-5-5 · REV-wrong-const : ✅ verdict BLOCK (subtle defect present)
  [behavioral] claude-sonnet-5-5 · REV-invariant : ✅ verdict BLOCK (subtle defect present)
  [behavioral] claude-sonnet-5-5 · REV-missing-clamp : ✅ verdict BLOCK (subtle defect present)
  [behavioral] claude-sonnet-5-5 · REV-clean-styled : ❌ verdict WARN (correct code, different style)
  [behavioral] claude-opus-5-5 · BEH-scope : ✅ scope respected
  [behavioral] claude-opus-5-5 · BEH-status : ✅ STATUS line present
  [behavioral] claude-opus-5-5 · BEH-ambiguity : ✅ correct stop on OQ-1, no fabrication
  [behavioral] claude-opus-5-5 · BEH-eval-correct : ❌ no eval actually exercising example EX-1
  [behavioral] claude-opus-5-5 · BEH-review-break : ✅ defect detected (BLOCK)
  [behavioral] claude-opus-5-5 · BEH-review-clean : ❌ verdict WARN on a clean diff
  [behavioral] claude-opus-5-5 · REV-boundary : ✅ verdict BLOCK (subtle defect present)
  [behavioral] claude-opus-5-5 · REV-wrong-const : ✅ verdict BLOCK (subtle defect present)
  [behavioral] claude-opus-5-5 · REV-invariant : ✅ verdict BLOCK (subtle defect present)
  [behavioral] claude-opus-5-5 · REV-missing-clamp : ✅ verdict BLOCK (subtle defect present)
  [behavioral] claude-opus-5-5 · REV-clean-styled : ❌ verdict WARN (correct code, different style)
  [behavioral] claude-haiku-5-5 · BEH-scope : ✅ scope respected
  [behavioral] claude-haiku-5-5 · BEH-status : ✅ STATUS line present
  [behavioral] claude-haiku-5-5 · BEH-ambiguity : ✅ correct stop on OQ-1, no fabrication
  [behavioral] claude-haiku-5-5 · BEH-eval-correct : ❌ no eval actually exercising example EX-1
  [behavioral] claude-haiku-5-5 · BEH-review-break : ✅ defect detected (BLOCK)
  [behavioral] claude-haiku-5-5 · BEH-review-clean : ❌ verdict WARN on a clean diff
  [behavioral] claude-haiku-5-5 · REV-boundary : ✅ verdict BLOCK (subtle defect present)
  [behavioral] claude-haiku-5-5 · REV-wrong-const : ✅ verdict BLOCK (subtle defect present)
  [behavioral] claude-haiku-5-5 · REV-invariant : ✅ verdict BLOCK (subtle defect present)
  [behavioral] claude-haiku-5-5 · REV-missing-clamp : ✅ verdict BLOCK (subtle defect present)
  [behavioral] claude-haiku-5-5 · REV-clean-styled : ❌ verdict WARN (correct code, different style)
```

## Reading vs 2026-11-12-claude5 (before ADR-11)

- BEH-eval-correct fails for all models, as before: case defect (lab-fix 7), not a regression.
- BEH-review-clean and REV-clean-styled: PASS before, now WARN for all three models. Calibration shift from the run scaffolding (rules + plugin + reviewer.md), identical across models: a reviewer.md matter for the EVOLUTION loop, not a role-assignment question.
- Chain layer: 9/9, no chain-of-command violation (2026-11-12-adr11-chain.md).
