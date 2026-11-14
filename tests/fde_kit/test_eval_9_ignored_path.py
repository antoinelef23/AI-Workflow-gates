"""EVAL-9 (INV-10, ADR-22 (4)) — a `files_touched` path ignored by git fails the task,
named with its ignore rule, and nothing is committed (real case K3: a fixture under an
ignored `build/` was skipped in silence)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests.orchestrator.conftest import (  # noqa: F401  (sandbox = fixture)
    run_orch,
    sandbox,
)

pytestmark = pytest.mark.eval

FM = "---\ntype: tasks\nfeature: feat\nstatus: approved\n---\n\n# Tasks — feat\n"
T1 = """
### T1 — Task one
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`, `tests/fixtures/build/x.txt`
- **done_when :** ok
- **verify :** `true`
"""
SHIM = (
    "echo data > t1.txt\nmkdir -p tests/fixtures/build\n"
    'echo fx > tests/fixtures/build/x.txt\necho "STATUS: done"\n'
)


def _git(sb: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=sb, capture_output=True, text=True, check=True
    ).stdout


def _setup(sb: Path, ignore: bool) -> str:
    feat = sb / "work" / "feat"
    (feat / "design.md").write_text("# design\n")
    (feat / "tasks.md").write_text(FM + T1)
    if ignore:
        with (sb / ".gitignore").open("a") as fh:
            fh.write("\nbuild/\n")
    _git(sb, "add", "-A")
    _git(sb, "commit", "-qm", "plan")
    (sb / ".shim" / "T1.sh").write_text(SHIM)
    return _git(sb, "rev-parse", "HEAD").strip()


def test_eval_9_ignored_files_touched_path_fails_the_task(sandbox: Path) -> None:  # noqa: F811
    head = _setup(sandbox, ignore=True)
    r = run_orch(sandbox)
    assert r.returncode == 1, r.stdout + r.stderr
    state = json.loads((sandbox / "work/feat/.runs/state.json").read_text())["tasks"]
    assert state["T1"] == "failed"
    assert _git(sandbox, "rev-parse", "HEAD").strip() == head  # nothing committed
    assert "tests/fixtures/build/x.txt" in r.stdout, r.stdout
    assert "build/" in r.stdout and ".gitignore" in r.stdout, r.stdout  # the rule


def test_eval_9_same_task_without_ignore_rule_is_committed(sandbox: Path) -> None:  # noqa: F811
    head = _setup(sandbox, ignore=False)
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    state = json.loads((sandbox / "work/feat/.runs/state.json").read_text())["tasks"]
    assert state["T1"] == "done"
    assert _git(sandbox, "rev-parse", "HEAD").strip() != head
    shown = _git(sandbox, "show", "--name-only", "--format=", "HEAD").split()
    assert "tests/fixtures/build/x.txt" in shown
