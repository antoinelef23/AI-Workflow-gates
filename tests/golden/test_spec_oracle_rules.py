"""A golden oracle may only check rules its own spec states (lab-fix 8).

remise-paliers' oracle required `is_estimate is True` while its spec listed INV-1 and INV-3
but no INV-2: a model following the spec could not pass. Each oracle that checks
`is_estimate` must have a spec stating that `is_estimate` MUST be True.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

GOLDEN = Path(__file__).resolve().parents[2] / "evals" / "golden"
CASES = sorted(
    p.name for p in GOLDEN.iterdir() if (p / "goldeval" / "check.sh").exists()
)


@pytest.mark.parametrize("case", CASES)
def test_is_estimate_rule_is_in_the_spec_when_the_oracle_checks_it(case):
    oracle = (GOLDEN / case / "goldeval" / "check.sh").read_text(encoding="utf-8")
    if 'get("is_estimate") is True' not in oracle:
        pytest.skip("oracle does not check is_estimate")
    spec = (GOLDEN / case / "spec.md").read_text(encoding="utf-8")
    assert re.search(r"`is_estimate`\s+MUST always be\s+`True`", spec), (
        f"{case}: the oracle requires is_estimate True but spec.md does not state it"
    )


@pytest.mark.parametrize("case", CASES)
def test_invariant_numbering_has_no_gap(case):
    spec = (GOLDEN / case / "spec.md").read_text(encoding="utf-8")
    nums = sorted({int(n) for n in re.findall(r"\*\*INV-(\d+)\*\*", spec)})
    assert nums == list(range(1, len(nums) + 1)), f"{case}: INV numbering {nums}"
