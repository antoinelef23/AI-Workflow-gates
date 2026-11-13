"""A task commit takes spec/design/tasks from the feature directory, not the whole folder
(lab-fix 12): a pending `.runs/CP-n-review.md` stays out of it, for its own review commit."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .conftest import run_orch

FM = "---\ntype: tasks\nfeature: feat\nstatus: approved\n---\n\n# Tasks — feat\n"
TASK = """
### T1 — Task
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `a.txt`
- **done_when :** ok
- **verify :** `true`
"""
# As in the real repo: run state ignored, review reports tracked for the audit.
GITIGNORE = (
    ".shim/\n**/.approvals/\n**/.runs/state.json\n"
    "**/.runs/journal.jsonl\n**/.runs/orchestrator.lock\n"
)


def _paths(sb: Path, rev: str = "HEAD") -> list[str]:
    return subprocess.run(
        ["git", "show", "--no-renames", "--name-only", "--format=", rev],
        cwd=sb,
        capture_output=True,
        text=True,
    ).stdout.split()


def test_task_commit_leaves_a_pending_review_report_out(sandbox: Path) -> None:
    (sandbox / ".gitignore").write_text(GITIGNORE)
    feat = sandbox / "work" / "feat"
    (feat / "tasks.md").write_text(FM + TASK)
    (feat / ".runs").mkdir(exist_ok=True)
    (feat / ".runs" / "CP-1-review.md").write_text("# Review CP-1\nVERDICT: PASS\n")
    (feat / "notes.md").write_text("scratch\n")  # not a feature artifact either
    (sandbox / ".shim" / "T1.sh").write_text('echo x > a.txt\necho "STATUS: done"\n')
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    committed = _paths(sandbox)
    assert "a.txt" in committed and "work/feat/tasks.md" in committed
    assert "work/feat/.runs/CP-1-review.md" not in committed
    assert "work/feat/notes.md" not in committed
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=sandbox,
        capture_output=True,
        text=True,
    ).stdout
    assert "work/feat/.runs/CP-1-review.md" in status  # left for its own commit
