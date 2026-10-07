---
type: spec
feature: devis-calc (golden task)
version: 1.0.0
status: validated
---

# Spec — Quote calculation (golden task of the harness)

> Golden task for the scorecard: the model writes the implementation, judged against OUR
> hidden evals (`goldeval/`, not provided to the model). Pure, deterministic scope.

## Invariants
- **INV-1** — the total MUST be ≥ 0 whatever the inputs (negative inputs clamped to 0).
- **INV-2** — `is_estimate` MUST always be `True`.

## Behaviors
- **BHV-1** — installation: `installation_eur = surface_m2 × 45.0`.
- **BHV-2** — discount: if `products_subtotal_eur > 2000`, 5 % discount on products ONLY.

## Contract
`compute_quote(products_subtotal_eur: float, surface_m2: float) -> dict` returns the keys
`products_eur`, `installation_eur`, `total_eur`, `is_estimate`, rounded to 2 decimals.

## Examples
- EX-1: (1500, 10) → products 1500.00, installation 450.00, total 1950.00
- EX-2: (2500, 20) → products 2375.00, installation 900.00, total 3275.00
- EX-3: (100, 0)  → total 100.00
