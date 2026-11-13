"""EVAL-3 — engine commits carry `Artifacts:` = their staged paths (BHV-3, INV-3; EX-2)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.orchestrator.conftest import approve, run_orch

pytest_plugins = ["tests.orchestrator.conftest"]

FM = "---\ntype: tasks\nfeature: feat\nstatus: approved\n---\n\n# Tasks — feat\n"
TASK = """
### T1 — Task
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `a.txt`, `b.txt`, `untouched/`
- **done_when :** ok
- **verify :** `true`
"""
OWNER = """
### T1 — By hand
- **depends_on :** —
- **agent :** owner
- **implements :** [doc]
- **files_touched :** `owner.txt`
- **done_when :** ok
- **verify :** `true`
"""


def _last_message(sb: Path) -> str:
    return subprocess.run(
        ["git", "log", "-1", "--format=%B"], cwd=sb, capture_output=True, text=True
    ).stdout


def _last_paths(sb: Path) -> list[str]:
    return subprocess.run(
        ["git", "show", "--no-renames", "--name-only", "--format=", "HEAD"],
        cwd=sb,
        capture_output=True,
        text=True,
    ).stdout.split()


def _trailer(msg: str) -> str:
    lines = [ln for ln in msg.splitlines() if ln.startswith("Artifacts: ")]
    assert len(lines) == 1, msg
    return lines[0][len("Artifacts: ") :]


@pytest.mark.eval
def test_eval_3_task_commit_trailer_is_the_staged_paths(sandbox: Path) -> None:
    (sandbox / "work" / "feat" / "tasks.md").write_text(FM + TASK)
    # a.txt is produced; b.txt and untouched/ are declared but never created
    (sandbox / ".shim" / "T1.sh").write_text('echo x > a.txt\necho "STATUS: done"\n')
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    staged = _last_paths(sandbox)
    assert "a.txt" in staged and "work/feat/tasks.md" in staged
    trailer = _trailer(_last_message(sandbox))
    assert trailer == ", ".join(sorted(staged))
    assert "b.txt" not in trailer  # declared in files_touched, not in the commit
    assert "untouched" not in trailer


@pytest.mark.eval
def test_eval_3_owner_lane_commit_trailer_is_the_staged_paths(sandbox: Path) -> None:
    (sandbox / "work" / "feat" / "tasks.md").write_text(FM + OWNER)
    (sandbox / "owner.txt").write_text("by hand\n")
    approve(sandbox, "T1")
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    msg = _last_message(sandbox)
    staged = _last_paths(sandbox)
    assert "owner.txt" in staged
    assert _trailer(msg) == ", ".join(sorted(staged))
    assert "Run: owner" in msg


@pytest.mark.eval
def test_eval_3_run_log_only_commit_says_so(sandbox: Path) -> None:
    """EX-2: the work was committed earlier; this attempt only changes the run log."""
    (sandbox / ".gitignore").write_text(".shim/\n.runs/\n")  # as in a real repo
    (sandbox / "work" / "feat" / "tasks.md").write_text(FM + TASK)
    (sandbox / "a.txt").write_text("x\n")
    (sandbox / "b.txt").write_text("y\n")
    subprocess.run(
        ["git", "add", ".gitignore", "a.txt", "b.txt", "work"], cwd=sandbox, check=True
    )
    subprocess.run(
        ["git", "commit", "-qm", "work done earlier"], cwd=sandbox, check=True
    )
    r = run_orch(sandbox)  # the shim replies "STATUS: done" without changing any file
    assert r.returncode == 0, r.stdout + r.stderr
    assert _last_paths(sandbox) == ["work/feat/tasks.md"]
    assert _trailer(_last_message(sandbox)) == "work/feat/tasks.md"


@pytest.mark.eval
def test_eval_3_rename_lists_both_source_and_destination(sandbox: Path) -> None:
    """A rename deletes the source and adds the destination: both are in the commit."""
    (sandbox / "work" / "feat" / "tasks.md").write_text(FM + TASK)
    (sandbox / "a.txt").write_text(
        "some content long enough to be detected as a rename\n"
    )
    subprocess.run(["git", "add", "a.txt", "work"], cwd=sandbox, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=sandbox, check=True)
    (sandbox / ".shim" / "T1.sh").write_text(
        'git mv a.txt b.txt\necho "STATUS: done"\n'
    )
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    staged = _last_paths(sandbox)
    assert "a.txt" in staged and "b.txt" in staged
    assert _trailer(_last_message(sandbox)) == ", ".join(sorted(staged))
