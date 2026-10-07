"""Lockfile guard (spec 1.2.0 — BHV-4, INV-3, EVAL-3): supply-chain integrity is
delegated to uv's hash-pinned lockfile; the lab maintains no dependency list."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.eval
def test_lockfile_is_committed_and_in_sync():
    # uv.lock is tracked (hash-pinned source of truth)…
    tracked = subprocess.run(
        ["git", "ls-files", "uv.lock"], cwd=REPO, capture_output=True, text=True
    )
    assert tracked.stdout.strip() == "uv.lock"
    # …and agrees with pyproject.toml (what `just check-lock` gates)
    p = subprocess.run(
        ["uv", "lock", "--check"], cwd=REPO, capture_output=True, text=True
    )
    assert p.returncode == 0, p.stderr


@pytest.mark.eval
def test_gate_wiring_is_locked():
    justfile = (REPO / "justfile").read_text(encoding="utf-8")
    assert "uv sync --locked" in justfile  # install refuses lockfile drift
    for recipe in ("gate:", "gate-ci:"):
        line = next(ln for ln in justfile.splitlines() if ln.startswith(recipe))
        assert "check-lock" in line
    # the superseded allowlist guard is fully gone (spec 1.2.0, NG-1)
    assert "dep_guard" not in justfile
    assert not (REPO / "lab" / "engine" / "dep_guard.py").exists()
    assert not (REPO / "lab" / "engine" / "dep_allowlist.txt").exists()
