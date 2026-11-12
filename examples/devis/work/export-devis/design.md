---
type: design
feature: export-devis
version: 1.0.1
status: validated
owner: Antoine (failure-containment simulation)
validated_by: simulated FDE — 2026-06-10
spec: ./spec.md          # version : 1.0.1
---

# Design — Quote export

Reuses the devis-pose foundation (ADR-1: pure functions). OQ-1 resolved (spec v1.0.1):
**plain-text** export — `src/devis/export.py::export_quote` encodes the output of
`format_quote` as UTF-8. Documentation: `docs/export-notes.md` (history) and
`docs/export-usage.md` (usage).
