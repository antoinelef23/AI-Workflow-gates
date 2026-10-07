"""Regression of the eval_gate.sh hook — findings H7/H8 (interactive eval gate)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .conftest import REPO

HOOK = REPO / ".claude" / "hooks" / "eval_gate.sh"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_eval_gate_sees_new_untracked_package_dir(tmp_path: Path) -> None:
    # finding H7: a new untracked module shows as `?? newpkg/` (a single line);
    # without --untracked-files=all the grep misses it and the gate SKIPS. Here the
    # evals are red: the fixed gate MUST run and exit 2 (not skip with 0).
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname = 'x'\nversion = '0'\n")
    (repo / "justfile").write_text("evals:\n    @echo 'EVALS RED'; exit 1\n")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@lab")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")

    # Feature delivered as a NEW untracked package.
    (repo / "newpkg").mkdir()
    (repo / "newpkg" / "mod.py").write_text("x = 1\n")

    r = subprocess.run(
        ["bash", str(HOOK)], cwd=repo, input="{}", text=True, capture_output=True
    )
    assert r.returncode == 2, (
        f"the gate should RUN (red) on a new untracked module, "
        f"not skip; rc={r.returncode}\n{r.stdout}{r.stderr}"
    )
    assert "EVAL GATE RED" in r.stderr


def test_eval_gate_skips_when_no_code_changed(tmp_path: Path) -> None:
    # Sanity: with no code change, the gate does not pay for the evals (exit 0).
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname = 'x'\nversion = '0'\n")
    (repo / "justfile").write_text("evals:\n    @echo 'EVALS RED'; exit 1\n")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@lab")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")

    r = subprocess.run(
        ["bash", str(HOOK)], cwd=repo, input="{}", text=True, capture_output=True
    )
    assert r.returncode == 0, f"nothing changed → no gate; {r.stderr}"
