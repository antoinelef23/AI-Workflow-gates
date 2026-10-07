---
type: design
feature: remise-paliers
version: 1.0.0
status: validated
spec: ./spec.md          # version: 1.0.0
---

# Design — remise-paliers (golden task)

Pure function, stdlib. Watch the boundaries: `≤` at the top of a tier, `>` to move to the next.
Clamp negative inputs to 0 before any computation (INV-1).
