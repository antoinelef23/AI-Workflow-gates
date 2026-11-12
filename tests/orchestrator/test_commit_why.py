"""The auto commit's Why carries a checkpoint-rejection rework reason (why in git)."""

from __future__ import annotations

import sys
from pathlib import Path

from .conftest import REPO

sys.path.insert(0, str(REPO / "lab" / "engine"))
import orchestrate  # noqa: E402
from plan import Node  # noqa: E402


def _node(rework: str = "") -> Node:
    n = Node("T3", "Do the thing", False, done_when="tests green", files=["a.py"])
    n.rework = rework
    return n


def test_plain_task_why_is_title_and_done_when(tmp_path: Path) -> None:
    msg = orchestrate._commit_message(_node(), tmp_path / "feat", ["BHV-1"])
    assert "Why: Do the thing — done when: tests green\n" in msg
    assert "Rework" not in msg


def test_rework_why_records_the_rejection_reason(tmp_path: Path) -> None:
    rework = (
        "\n\n⚠️ OWNER REVIEW FEEDBACK (rejection CP-4): trials cannot read the role"
        " file\nFix accordingly before re-delivering."
    )
    msg = orchestrate._commit_message(_node(rework), tmp_path / "feat", ["BHV-1"])
    assert "Rework after the CP-4 rejection: trials cannot read the role file" in msg
    assert "Fix accordingly" not in msg  # boilerplate stays out of git
    assert msg.index("Rework after") < msg.index("Spec-IDs:")
