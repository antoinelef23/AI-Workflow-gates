"""EVAL-5 (BHV-5, BHV-5c, INV-3, ADR-20) — one pure classifier picks the route; the
structured ``STATUS:`` grammar; route modes come from the effective policy."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lab" / "engine"))

import policy  # noqa: E402
import routes  # noqa: E402

pytestmark = pytest.mark.eval


def _status(line: str) -> dict:
    return {"kind": "status", "text": "some work.\n" + line + "\n"}


def test_eval_5_r1_red_before_last_attempt():
    sig = {"kind": "verify_red", "attempt": 1, "max_attempts": 3}
    assert routes.classify(sig)[0] == "R1"
    sig["attempt"] = 2
    assert routes.classify(sig)[0] == "R1"


def test_eval_5_r2_red_on_last_attempt():
    sig = {"kind": "verify_red", "attempt": 3, "max_attempts": 3}
    assert routes.classify(sig)[0] == "R2"


@pytest.mark.parametrize(
    "line,route",
    [
        ("STATUS: blocked — OQ: the export format is unspecified", "R3"),
        ("STATUS: blocked — ADR: pattern I-12 is inapplicable", "R4"),
        ("STATUS: blocked — scope: files_touched gap: a.py, b.py", "R5"),
    ],
)
def test_eval_5_blocked_categories(line, route):
    r, detail = routes.classify(_status(line))
    assert r == route
    assert detail


def test_eval_5_blocked_detail_is_reason():
    _, detail = routes.classify(
        _status("STATUS: blocked — scope: files_touched gap: x.py")
    )
    assert detail == "files_touched gap: x.py"


def test_eval_5_r6_panel_block_on_auto_cp():
    assert routes.classify({"kind": "panel_block", "cp_mode": "auto"})[0] == "R6"


def test_eval_5_r7_signed_reject():
    assert routes.classify({"kind": "reject"})[0] == "R7"


@pytest.mark.parametrize(
    "line",
    [
        "STATUS: blocked",
        "STATUS: blocked — because reasons",
        "STATUS: blocked — OQ-3",  # old grammar: no category separator
        "STATUS: blocked — files_touched gap: x.py",  # old scope message
        "STATUS: blocked — unknown: whatever",
    ],
)
def test_eval_5_uncategorized_blocked_is_human_never_auto(line):
    r, _ = routes.classify(_status(line))
    assert r == "human"
    assert routes.route_mode(r, None) == "human"
    assert routes.route_mode(r, {"routes.R1": ("auto", "override")}) == "human"


def test_eval_5_status_done_is_not_a_route():
    assert routes.classify(_status("STATUS: done"))[0] is None


def test_eval_5_last_status_line_wins():
    text = 'Grammar: "STATUS: blocked — OQ: x"\nSTATUS: done\n'
    assert routes.classify({"kind": "status", "text": text})[0] is None


def test_eval_5_default_modes_follow_spec_table():
    rs = ("R1", "R2", "R3", "R4", "R5", "R6", "R7")
    assert {r: routes.route_mode(r, None) for r in rs} == {
        "R1": "auto",
        "R2": "proposal",
        "R3": "human",
        "R4": "proposal",
        "R5": "proposal",
        "R6": "auto",
        "R7": "auto",
    }


def test_eval_5_route_override_changes_applied_mode():
    pol = policy.effective_policy(
        {"profile": "solo", "overrides": {"routes": {"R6": "human"}}}
    )
    assert routes.route_mode("R6", pol) == "human"
    assert routes.route_mode("R7", pol) == "auto"


def test_eval_5_unknown_signal_is_human():
    assert routes.classify({"kind": "weird"})[0] == "human"


def test_eval_5_policy_note_removed():
    pol = policy.effective_policy(
        {"profile": "solo", "overrides": {"routes": {"R6": "human"}}}
    )
    assert "applied from iteration 3" not in "\n".join(policy.format_policy(pol))
