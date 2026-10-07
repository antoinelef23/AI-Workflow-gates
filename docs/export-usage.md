# Usage — Quote export (`src/devis/export.py`)

> Feature `export-devis` — spec v1.0.0 (OQ-1 resolved: **plain text** export, PDF in phase 2).

## Function

```python
from devis.export import export_quote

payload: bytes = export_quote(quote)
```

`export_quote(quote: dict) -> bytes` returns the downloadable quote (BHV-1):
exactly the output of `format_quote`, UTF-8 encoded. Pure function, no side effects
(devis-pose foundation, ADR-1).

## Input contract

`quote` follows the contract of the devis-pose Examples:

| Key | Type | Example |
|---|---|---|
| `products_eur` | float | `2375.00` |
| `installation_eur` | float | `900.00` |
| `total_eur` | float | `3275.00` |
| `is_estimate` | bool | `true` |

## Output

Plain UTF-8 text, one header line then the Products / Installation / Total lines:

```
Quote — non-binding estimate
Products: 2375.00 EUR
Installation: 900.00 EUR
Total: 3275.00 EUR
```

- The "estimate" mention is always present (INV-1, carried by `format_quote`).
- Quote without installation (surface 0): valid export, line `Installation: 0.00 EUR` (BHV-1a).

## Out of scope

- Sending by e-mail (NG-1).
- PDF/CSV format: phase 2 (cf. OQ-1 resolution in spec.md §8).

## Verification

```sh
uv run pytest -q tests/devis_export          # tests + eval EVAL-1
```
