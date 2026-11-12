"""AGENTS.md shim (spec BHV-5, EVAL-5) — a pointer to CLAUDE.md and the rules file,
never a copy. The rules live in lab/plugin/rules/hard-rules.md (fde-kit ADR-3)."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RULES = REPO / "lab" / "plugin" / "rules" / "hard-rules.md"


@pytest.mark.eval
def test_agents_md_points_to_claude_md_without_duplicating_rules():
    shim = REPO / "AGENTS.md"
    assert shim.is_file()
    text = shim.read_text(encoding="utf-8")
    assert "CLAUDE.md" in text  # single source of truth referenced…
    assert "hard-rules.md" in text  # …and the rules file where the rules now live
    # …and not restated: a distinctive hard-rule sentence must live ONLY in the rules file
    sentence = "no green eval, no merge"
    assert sentence in RULES.read_text(encoding="utf-8").lower()
    assert sentence not in text.lower()
    assert sentence not in (REPO / "CLAUDE.md").read_text(encoding="utf-8").lower()
    # a pointer stays a pointer — an order of magnitude smaller than the rules
    assert len(text) < len(RULES.read_text(encoding="utf-8")) / 5
