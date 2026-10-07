---
type: tasks
feature: arrondi-comptable
status: approved
---

# Tasks — arrondi-comptable (golden task)

### T1 — Implement round_half_up + compute_ttc
- **files_touched:** `compute.py`
- **prompt:** Implement `round_half_up(x, ndigits=2)` (half-up, INV-1) and
  `compute_ttc(price_ht)` (BHV-2) in `compute.py` per spec.md and its Examples.
- **done_when:** `compute.py` exposes both functions, conforming to the Examples.
