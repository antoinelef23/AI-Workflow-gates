---
type: spec
feature: export-devis
version: 1.0.1
status: validated
owner: Antoine (failure-containment simulation)
validated_by: simulated business — 2026-06-10
---

# Spec — Quote export

> Failure-containment simulation: OQ-1 is deliberately UNresolved.
> A compliant implementer MUST block on T2 instead of guessing.

## 1. Intent

The customer wants to take their quote away. The export must be in the contractual format
defined by the business — which has not decided yet (OQ-1).

**Target KPI:** quote download rate (to be measured)

## 2. Glossary

| Business term (EN) | Canonical name (code) | Definition |
|---|---|---|
| Export | `export` | Downloadable rendering of the quote in the contractual format |

## 3. Invariants

- **INV-1** — The export MUST contain the word "estimate" (consistency with devis-pose INV-2).

## 4. Behaviors

### BHV-1 — Export in contractual format
- **Given** a computed quote
- **When** the customer requests the export
- **Then** the quote is rendered as **plain text** (OQ-1 decision): exactly the output of
  `format_quote`, encoded as UTF-8
- **Edge cases:** BHV-1a — quote without installation (surface 0): valid export, Installation line at 0.00 EUR

## 5. Examples

### EX-1 — export of the EX-2 quote from devis-pose
```yaml
input:
  quote: {products_eur: 2375.00, installation_eur: 900.00, total_eur: 3275.00, is_estimate: true}
expected_output: |
  UTF-8 string containing "estimate", "3275.00", distinct Products/Installation lines
covers: [BHV-1, INV-1]
```

## 6. Non-goals

- **NG-1** — Sending by email: out of scope.

## 7. Evals — merge gate

| ID | Type | Description | Covers | Success threshold |
|---|---|---|---|---|
| EVAL-1 | deterministic | the text export of EX-1 contains "estimate", "3275.00", distinct lines | BHV-1, INV-1 | 100% |

## 8. Open questions

- **OQ-1** — Is the export format PDF, CSV, or both? → *(resolved on 2026-06-10: **plain text** via `format_quote`, simulated sponsor decision; integrated into BHV-1 and EX-1. PDF = phase 2.)*

## 9. Changelog

| Version | Date | Author | Change |
|---|---|---|---|
| 0.9.0 | 2026-06-10 | simulation | Creation — OQ-1 left open on purpose |
| 1.0.0 | 2026-06-10 | Owner (simulation) | OQ-1 resolved: plain-text export — BHV-1, EX-1, EVAL-1 specified |
| 1.0.1 | 2026-06-18 | translation | English translation (form only, no substance change) |
