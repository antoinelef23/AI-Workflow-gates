"""Plan-lint ignores the spec's Changelog when it checks spec IDs (lab-fix item 1).

A changelog row such as "BHV-4 dropped" names an ID that no longer exists. Before the fix the
existence check was a search over the whole spec, so a task could still implement BHV-4 and
pass, and an EVAL only named in the changelog was reported as uncarried.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "lab" / "engine"))

from plan import Node  # noqa: E402
from planlint import spec_body, validate  # noqa: E402

SPEC = """---
version: 1.1.0
---
# Spec

## 4. Behaviors

- **BHV-1** — kept.

## 7. Evals

- **EVAL-1** — covers BHV-1.

## 9. Changelog

| Version | Date | Author | Change |
|---|---|---|---|
| 1.1.0 | 2026-11-14 | Owner | BHV-4 and EVAL-4 dropped |
| 1.0.0 | 2026-11-01 | Spec Workshop | Created |
"""


class _NoRegistry:
    models: dict = {}


def _task(implements: list[str]) -> Node:
    return Node(
        "T1",
        "Task T1",
        False,
        [],
        prompt="p",
        implements=implements,
        files=["src/t1.py"],
        verify="true",
        done_when="ok",
    )


def _lint(tmp_path: Path, implements: list[str]):
    (tmp_path / "spec.md").write_text(SPEC, encoding="utf-8")
    return validate(tmp_path, {}, [_task(implements)], _NoRegistry())


def test_an_id_named_only_in_the_changelog_is_not_found(tmp_path):
    errors, _ = _lint(tmp_path, ["BHV-1", "BHV-4", "EVAL-1"])
    assert "T1: implements [BHV-4] not found in spec.md" in errors
    assert not any("[BHV-1]" in e or "[EVAL-1]" in e for e in errors)


def test_an_eval_named_only_in_the_changelog_is_not_required(tmp_path):
    _, warnings = _lint(tmp_path, ["BHV-1", "EVAL-1"])
    assert not any("EVAL-4" in w for w in warnings)


def test_spec_body_keeps_the_sections_after_the_changelog():
    text = "## 1. A\nBHV-1\n## 9. Changelog\nBHV-9 dropped\n## 10. Annex\nINV-2\n"
    body = spec_body(text)
    assert "BHV-1" in body and "INV-2" in body and "BHV-9" not in body


def test_an_id_is_matched_whole_not_as_a_prefix(tmp_path):
    """BHV-1 must not be found inside BHV-10 (the check used a substring test)."""
    (tmp_path / "spec.md").write_text(
        "## 4. Behaviors\n\n- **BHV-10** — only this one.\n\n## 7. Evals\n\n- **EVAL-1**\n",
        encoding="utf-8",
    )
    errors, _ = validate(tmp_path, {}, [_task(["BHV-1", "EVAL-1"])], _NoRegistry())
    assert "T1: implements [BHV-1] not found in spec.md" in errors
