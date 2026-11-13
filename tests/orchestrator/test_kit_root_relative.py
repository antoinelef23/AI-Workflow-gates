"""A relative LAB_ROOT is resolved (lab-fix 11).

The orchestrator compares the project with the kit (`PROJECT != LAB`); PROJECT is resolved,
so an unresolved relative LAB_ROOT made `--project <the same folder>` look external.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "lab" / "engine"))

import kit  # noqa: E402


def test_relative_lab_root_is_resolved(tmp_path, monkeypatch):
    (tmp_path / "kit").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LAB_ROOT", "kit")
    root = kit.kit_root()
    assert root.is_absolute()
    assert root == (tmp_path / "kit").resolve()


def test_same_folder_compares_equal_to_a_resolved_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LAB_ROOT", ".")
    assert (
        kit.kit_root() == Path(".").resolve()
    )  # what orchestrate does with --project .
