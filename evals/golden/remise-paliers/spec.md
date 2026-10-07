---
type: spec
feature: remise-paliers (golden task)
version: 1.0.0
status: validated
---

# Spec — Tiered discount (harder golden task)

> Isolates the capability: the **tier boundaries** and the **clamp** are easy to get wrong.

## Invariants
- **INV-1** — total ≥ 0; negative `products_subtotal_eur` and `surface_m2` clamped to 0.
- **INV-3** — the discount applies to the PRODUCTS subtotal only, never to installation.

## Behaviors
- **BHV-1** — `installation_eur = surface_m2 × 45.0`.
- **BHV-2** — tiered discount on the products subtotal (upper bounds INCLUSIVE):
  - `products ≤ 1000` → 0 %
  - `1000 < products ≤ 5000` → 5 %
  - `products > 5000` → 10 %

## Contract
`compute_total(products_subtotal_eur: float, surface_m2: float) -> dict` →
keys `products_eur`, `installation_eur`, `total_eur`, `is_estimate` (rounded to 2 decimals).

## Examples
- EX-1: (1000, 0) → products 1000.00 (tier 0 %), total 1000.00
- EX-2: (1000.01, 0) → products 950.01 (tier 5 %)
- EX-3: (5000, 10) → products 4750.00 (5 %), installation 450.00, total 5200.00
- EX-4: (5000.01, 0) → products 4500.01 (tier 10 %)
- EX-5: (-100, -5) → total 0.00 (clamp)
