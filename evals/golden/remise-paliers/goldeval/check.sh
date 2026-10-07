#!/usr/bin/env bash
# LOGIC verdict (name-agnostic): does ANY callable compute the tiers + clamp?
# Independent of file/function name (separate API verdict). Tests the logic, not the contract.
set -uo pipefail
python3 - <<'PY'
import sys, importlib.util, pathlib, inspect
sys.path.insert(0, ".")

def funcs():
    out = []
    for p in pathlib.Path(".").rglob("*.py"):
        if "goldeval" in p.parts:
            continue
        try:
            s = importlib.util.spec_from_file_location(p.stem, p)
            m = importlib.util.module_from_spec(s)
            s.loader.exec_module(m)
        except Exception:
            continue
        out += [f for _, f in inspect.getmembers(m, inspect.isfunction)]
    return out

def approx(a, b): return abs(float(a) - b) < 0.01

cases = [
    # Examples from the spec (tier boundaries)
    ((1000, 0), {"products_eur": 1000.00}),     # low boundary: 0 %
    ((1000.01, 0), {"products_eur": 950.01}),    # just above: 5 %
    ((5000, 10), {"products_eur": 4750.00, "installation_eur": 450.00}),  # high boundary 5 % inclusive
    ((5000.01, 0), {"products_eur": 4500.01}),   # just above: 10 %
    # Held-out (finding M8): OFF-spec values, derived from the tiers (<=1000 -> 0 %,
    # 1000<p<=5000 -> 5 %, p>5000 -> 10 %; installation 45 EUR/m2) — defeat a lookup table.
    ((999.99, 5), {"products_eur": 999.99}),       # below the 1st tier
    ((1500, 0), {"products_eur": 1425.0}),         # middle of the 5 % tier
    ((5000.00, 10), {"total_eur": 5200.0}),        # high boundary 5 % + installation
    ((5001, 0), {"products_eur": 4500.9}),         # just above -> 10 %
    ((50000, 200), {"total_eur": 54000.0}),        # large amount 10 % + installation
]

def works(fn):
    try:
        for args, exp in cases:
            r = fn(*args)
            for k, v in exp.items():
                if not approx(r[k], v):
                    return False
        # clamp INV-1 AND is_estimate MUST be True (finding M9)
        return float(fn(-100, -5)["total_eur"]) == 0.0 and fn(1500, 10).get("is_estimate") is True
    except Exception:
        return False

ok = any(works(f) for f in funcs())
print("logic OK" if ok else "logic FAIL: no callable computes the tiers correctly")
sys.exit(0 if ok else 1)
PY
