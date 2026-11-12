---
type: spec
feature: devis-pose
version: 1.0.1
status: validated
owner: Antoine (simulation)
validated_by: simulated business — 2026-06-10
---

# Spec — Bathroom installation quote

> **The WHAT. The business contract.** Simulation feature: compute and format the installation
> quote from the product amount and the surface area. Scope deliberately pure
> (no I/O, no API) to validate the orchestrated pipeline end to end.

## 1. Intent

The customer has assembled their product cart; they want an estimate of the total cost including
installation, in one second, with no commitment. This feature computes the quote and formats it for display.

**Target KPI:** rate of adding the quote to the cart (baseline 0 → measured in the lab)

## 2. Glossary

| Business term (EN) | Canonical name (code) | Definition |
|---|---|---|
| Quote | `quote` | Non-contractual costed estimate: products + installation |
| Installation | `installation` | Installation service billed per m² |
| Products subtotal | `products_subtotal_eur` | Sum of the cart's product prices, in euros |
| Volume discount | `volume_discount` | Reduction applied to the products subtotal only |

## 3. Invariants

- **INV-1** — A quote's total MUST be ≥ 0, whatever the inputs.
- **INV-2** — Every quote MUST carry `is_estimate = true`: a quote is NEVER contractual.
- **INV-3** — The volume discount MUST apply to the products subtotal only, never to installation.

## 4. Behaviors

### BHV-1 — Installation per m²
- **Given** an installation surface `surface_m2` > 0
- **When** the quote is computed
- **Then** the installation cost equals `surface_m2 × 45.00 €`
- **Edge cases:** BHV-1a — `surface_m2 = 0`: installation = 0 €, valid quote (products only)

### BHV-2 — Volume discount
- **Given** a products subtotal strictly greater than 2000 €
- **When** the quote is computed
- **Then** a 5% discount is applied to the products subtotal (not to installation — INV-3)
- **Edge cases:** BHV-2a — subtotal = 2000.00 € exactly: NO discount (strictly greater)

### BHV-3 — Customer formatting
- **Given** a computed quote
- **When** it is formatted for display
- **Then** the text contains the word "estimate", the total in euros with exactly 2 decimals,
  and the products / installation breakdown on separate lines

## 5. Examples

### EX-1 — nominal case without discount
```yaml
input:
  products_subtotal_eur: 1500.00
  surface_m2: 10
expected_output:
  products_eur: 1500.00
  installation_eur: 450.00
  total_eur: 1950.00
  is_estimate: true
covers: [BHV-1, BHV-2a-implicit, INV-2]
```

### EX-2 — volume discount, installation intact
```yaml
input:
  products_subtotal_eur: 2500.00
  surface_m2: 20
expected_output:
  products_eur: 2375.00   # 2500 × 0.95
  installation_eur: 900.00  # 20 × 45, NOT discounted (INV-3)
  total_eur: 3275.00
  is_estimate: true
covers: [BHV-2, INV-3]
```

### EX-3 — zero surface
```yaml
input:
  products_subtotal_eur: 100.00
  surface_m2: 0
expected_output:
  total_eur: 100.00
covers: [BHV-1a]
```

## 6. Non-goals

- **NG-1** — VAT: out of scope, handled by the downstream billing engine.
- **NG-2** — Currencies other than EUR.

## 7. Evals — merge gate

*Convention: a pytest test marked `@pytest.mark.eval`, name containing the ID in lowercase.*

| ID | Type | Description | Covers | Success threshold |
|---|---|---|---|---|
| EVAL-1 | deterministic | EX-1, EX-2, EX-3 verified to the euro | BHV-1, BHV-2, BHV-1a, BHV-2a, INV-3 | 100% |
| EVAL-2 | property-based | total ≥ 0 and is_estimate=true on generated inputs (amounts 0→10⁶, surfaces 0→500) | INV-1, INV-2 | 100% |
| EVAL-3 | deterministic | the format of EX-2 contains "estimate", "3275.00", distinct products/installation lines | BHV-3 | 100% |

## 8. Open questions

*(none — spec closed for the simulation)*

## 9. Changelog

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0.0 | 2026-06-10 | simulation | Creation |
| 1.0.1 | 2026-06-18 | translation | English translation (form only, no substance change) |
