"""AGENTS.md shim (spec BHV-5, EVAL-5) — a pointer to CLAUDE.md, never a copy."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.eval
def test_agents_md_points_to_claude_md_without_duplicating_rules():
    shim = REPO / "AGENTS.md"
    assert shim.is_file()
    text = shim.read_text(encoding="utf-8")
    assert "CLAUDE.md" in text  # single source of truth referenced…
    # …and not restated: a distinctive hard-rule sentence must live ONLY in CLAUDE.md
    assert "no green eval, no merge" not in text.lower()
    # a pointer stays a pointer — an order of magnitude smaller than the rules
    assert len(text) < len((REPO / "CLAUDE.md").read_text(encoding="utf-8")) / 5
