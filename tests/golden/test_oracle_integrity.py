"""Golden oracle integrity — gated in CI (was: only the paid live campaign ran these).

Each golden `goldeval/check.sh` is run against a KNOWN-GOOD reference impl (must pass,
exit 0) and a deliberately BROKEN impl (must fail, nonzero). This proves the oracle
still discriminates correct from incorrect code, so a translation/edit that rots an
oracle's math is caught by `just gate` instead of silently failing a correct model
in a billed run (review finding: golden integrity was un-gated).
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "evals" / "golden"

# Correct reference for devis-calc = the real in-repo implementation.
DEVIS_GOOD = (REPO / "src" / "devis" / "calc.py").read_text(encoding="utf-8")
DEVIS_BAD = """
def compute_quote(products_subtotal_eur, surface_m2):
    p = max(0.0, products_subtotal_eur); s = max(0.0, surface_m2)
    if p > 2000: p *= 0.95
    pe = round(p, 2); ie = round(s * 45, 2)
    return {"products_eur": pe, "installation_eur": ie, "total_eur": round(pe + ie, 2)}
"""  # omits is_estimate (INV-2) → oracle must reject (M9)

REMISE_GOOD = """
def compute_total(products_subtotal_eur, surface_m2):
    p = max(0.0, products_subtotal_eur); s = max(0.0, surface_m2)
    if p > 5000: p *= 0.90
    elif p > 1000: p *= 0.95
    pe = round(p, 2); ie = round(s * 45, 2)
    return {"products_eur": pe, "installation_eur": ie,
            "total_eur": round(pe + ie, 2), "is_estimate": True}
"""
REMISE_BAD = REMISE_GOOD.replace(', "is_estimate": True', "")  # omits INV → reject

ARRONDI_GOOD = """
from decimal import Decimal, ROUND_HALF_UP
def round_half_up(x, n):
    return float(Decimal(str(x)).quantize(Decimal(10) ** -n, rounding=ROUND_HALF_UP))
def compute_ttc(price_ht):
    return round_half_up(float(Decimal(str(price_ht)) * Decimal("1.20")), 2)
"""
ARRONDI_BAD = """
def round_half_up(x, n):
    return round(x, n)            # native banker's rounding → oracle must reject (M8)
def compute_ttc(price_ht):
    return round(price_ht * 1.20, 2)
"""

CASES = [
    ("devis-calc", DEVIS_GOOD, DEVIS_BAD),
    ("remise-paliers", REMISE_GOOD, REMISE_BAD),
    ("arrondi-comptable", ARRONDI_GOOD, ARRONDI_BAD),
]


def _run_oracle(golden: str, impl_code: str) -> int:
    check = GOLDEN / golden / "goldeval" / "check.sh"
    with tempfile.TemporaryDirectory() as d:
        wd = Path(d)
        (wd / "impl.py").write_text(impl_code, encoding="utf-8")
        (wd / "goldeval").mkdir()
        (wd / "goldeval" / "check.sh").write_text(check.read_text(encoding="utf-8"))
        return subprocess.run(["bash", "goldeval/check.sh"], cwd=wd).returncode


@pytest.mark.parametrize("golden,good,bad", CASES, ids=[c[0] for c in CASES])
def test_oracle_accepts_reference_and_rejects_broken(golden, good, bad):
    assert _run_oracle(golden, good) == 0, f"{golden}: oracle rejected a correct impl"
    assert _run_oracle(golden, bad) != 0, f"{golden}: oracle accepted a broken impl"
