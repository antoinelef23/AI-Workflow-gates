#!/usr/bin/env bash
# LOGIC verdict (name-agnostic): is there a callable that rounds half-up
# AND one that computes the gross (TTC)? Independent of names (separate API verdict). Discriminates native round().
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

def approx(a, b): return abs(float(a) - b) < 0.005  # < 0.01: the banker's/half-up gap is discriminating

fs = funcs()

def is_round(fn):  # half-up (2 args)
    try:
        spec = approx(fn(2.675, 2), 2.68) and approx(fn(0.125, 2), 0.13) and approx(fn(2.674, 2), 2.67)
        # Held-out (finding M8): off-spec half-ups — discriminate native round().
        held = (
            approx(fn(1.005, 2), 1.01)
            and approx(fn(3.445, 2), 3.45)
            and approx(fn(99.995, 2), 100.00)
            and approx(fn(10.156, 2), 10.16)
        )
        return spec and held
    except Exception:
        return False

def is_ttc(fn):  # VAT 20 % (1 arg)
    try:
        spec = approx(fn(10.0), 12.0)
        # Held-out (finding M8): off-spec gross (x1.20, half-up rounding 2 dec.).
        held = approx(fn(0.01), 0.01) and approx(fn(999.99), 1199.99) and approx(fn(1.234), 1.48)
        return spec and held
    except Exception:
        return False

ok = any(is_round(f) for f in fs) and any(is_ttc(f) for f in fs)
print("logic OK" if ok else "logic FAIL: half-up rounding and/or gross (TTC) missing (native round()?)")
sys.exit(0 if ok else 1)
PY
