"""EVAL-7 — documented `just eval-models` invocations are positional (BHV-7)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
KEY_VALUE = re.compile(r"just\s+eval-models\s+[A-Za-z_][\w-]*=")


def _scanned_files() -> list[Path]:
    files = [REPO / "README.md", REPO / "lab/models/EVOLUTION.md", REPO / "justfile"]
    files += sorted((REPO / "docs").rglob("*.md"))
    return [f for f in files if f.is_file()]


@pytest.mark.eval
def test_eval_7_no_key_value_eval_models():
    offenders = [
        f"{f.relative_to(REPO)}:{n}: {line.strip()}"
        for f in _scanned_files()
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1)
        if KEY_VALUE.search(line)
    ]
    assert not offenders, "key=value after eval-models:\n" + "\n".join(offenders)


@pytest.mark.eval
def test_eval_7_scan_covers_the_documented_files():
    names = {f.relative_to(REPO).as_posix() for f in _scanned_files()}
    assert {"README.md", "lab/models/EVOLUTION.md", "justfile"} <= names
    assert "docs/how-to/evaluate-models.md" in names
