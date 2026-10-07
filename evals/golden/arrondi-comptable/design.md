---
type: design
feature: arrondi-comptable
version: 1.0.0
status: validated
spec: ./spec.md          # version: 1.0.0
---

# Design — arrondi-comptable (golden task)

`decimal.Decimal` + `ROUND_HALF_UP`. Convert via `Decimal(str(x))` to avoid the binary
representation error (`Decimal(2.675)` ≠ `Decimal('2.675')`). Return a `float`.
