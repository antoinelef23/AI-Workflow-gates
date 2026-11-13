"""A behavioral case may not ask for a file outside its own `files_touched` (lab-fix 7).

BEH-eval-correct asked the implementer to write `test_eval_1_add.py` while its tasks.md only
allowed `allowed.py`: every scope-respecting model refused and failed the case.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _cases():
    spec = importlib.util.spec_from_file_location(
        "cases_scope", REPO / "evals" / "behavioral" / "cases.py"
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules["cases_scope"] = m
    spec.loader.exec_module(m)
    return m


def test_eval_correct_case_allows_the_eval_file_it_asks_for():
    m = _cases()
    case = next(c for c in m.CASES if c.id == "BEH-eval-correct")
    allowed = re.findall(
        r"`([^`]+)`",
        case.files["tasks.md"].split("files_touched", 1)[1].splitlines()[0],
    )
    asked = re.findall(r"`([\w./-]+\.py)`", case.prompt)
    assert asked, "the case prompt names no file"
    assert set(asked) <= set(allowed), f"asked {asked}, allowed {allowed}"
