---
type: spec
feature: arrondi-comptable (golden task)
version: 1.0.0
status: validated
---

# Spec — Accounting rounding (harder golden task)

> Isolates the capability: Python's native `round()` does *banker's* rounding (half-even)
> and stumbles on floats. Accounting requires an exact **half-up**.

## Invariants
- **INV-1** — rounding is a **ROUND_HALF_UP** (half-up) on the decimal value,
  NOT Python's native `round()`. `2.675 → 2.68`, `0.125 → 0.13`, `1.005 → 1.01`.

## Behaviors
- **BHV-1** — `round_half_up(x, ndigits=2)` rounds `x` to `ndigits` decimals, half-up.
- **BHV-2** — `compute_ttc(price_ht) = round_half_up(price_ht × 1.20, 2)` (VAT 20 %).

## Contract
The module exposes `round_half_up(x: float, ndigits: int = 2) -> float` and
`compute_ttc(price_ht: float) -> float`.
Hint: `Decimal(str(x)).quantize(..., rounding=ROUND_HALF_UP)`.

## Examples
- EX-1: round_half_up(2.675, 2) → 2.68   (native round() would give 2.67)
- EX-2: round_half_up(0.125, 2) → 0.13   (native round(): 0.12)
- EX-3: round_half_up(2.674, 2) → 2.67   (down)
- EX-4: compute_ttc(10.0) → 12.00
