"""T11 — cutover: nothing tracked under `.claude/`, engine follows the plugin
(spec BHV-2, INV-1; design ADR-3, I-15)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENGINE = REPO / "lab" / "engine"
# `.claude/` as a path of its own (not `.claude-plugin/`).
LEGACY = re.compile(r"\.claude/")
# The plan-lint / plan modules legitimately NAME the protected config dir to
# detect Owner-lane tasks (tests/orchestrator/test_owner_lane.py); they never read it.
OWNER_LANE_DETECTION = {"planlint.py", "plan.py"}


def test_no_tracked_file_under_dot_claude():
    out = subprocess.run(
        ["git", "ls-files", ".claude"], cwd=REPO, capture_output=True, text=True
    )
    assert out.returncode == 0
    assert out.stdout.strip() == ""


def test_no_engine_file_references_dot_claude():
    offenders = []
    for p in sorted(ENGINE.rglob("*")):
        if (
            not p.is_file()
            or "__pycache__" in p.parts
            or p.name in OWNER_LANE_DETECTION
        ):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if LEGACY.search(text):
            offenders.append(str(p.relative_to(REPO)))
    assert offenders == []
