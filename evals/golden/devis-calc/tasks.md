---
type: tasks
feature: devis-calc
status: approved
---

# Tasks — devis-calc (golden task)

### T1 — Implement compute_quote
- **files_touched:** `compute.py`
- **prompt:** Implement `compute_quote(products_subtotal_eur, surface_m2) -> dict` in
  `compute.py` per spec.md (INV-1, INV-2, BHV-1, BHV-2, key contract, Examples).
- **done_when:** `compute.py` exposes `compute_quote` conforming to the Examples.
