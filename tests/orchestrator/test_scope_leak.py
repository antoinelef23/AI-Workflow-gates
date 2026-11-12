"""Scope leak — a task must not go green thanks to edits its commit will not carry.

Found live at fde-kit CP-3: T9 removed a pyproject key and fixed the test that
asserted it, but that test was outside T9's files_touched. `verify` ran on the
working tree (green), scoped_commit staged only files_touched → the committed
tree was red while the run log said "done, evals green".
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .conftest import run_orch

FM = "---\ntype: tasks\nfeature: feat\nstatus: approved\n---\n\n# Tasks — feat\n"


def _git(sb: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=sb, capture_output=True, text=True, check=True
    ).stdout


def _setup(sb: Path, body: str) -> None:
    (sb / "other.txt").write_text("v1\n")
    _git(sb, "add", "-A")
    _git(sb, "commit", "-qm", "other")
    (sb / "work" / "feat" / "tasks.md").write_text(FM + body)


def _state(sb: Path) -> dict:
    return json.loads((sb / "work" / "feat" / ".runs" / "state.json").read_text())


T1 = """
### T1 — Task with a narrow scope
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`
"""


def test_out_of_scope_edit_is_not_done_and_not_committed(sandbox: Path) -> None:
    (sandbox / ".shim" / "T1.sh").write_text(
        'echo data > t1.txt\necho "v2" > other.txt\necho "STATUS: done"\n'
    )
    _setup(sandbox, T1)
    r = run_orch(sandbox)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "scope leak — other.txt" in r.stdout
    assert _state(sandbox)["T1"] == "failed"
    assert _git(sandbox, "show", "HEAD:other.txt") == "v1\n"  # leak never committed
    journal = (sandbox / "work" / "feat" / ".runs" / "journal.jsonl").read_text()
    assert '"event": "scope_leak"' in journal


def test_agent_reverting_the_leak_on_retry_is_done(sandbox: Path) -> None:
    # Attempt 1 leaks; on the retry (the feedback names the file) it reverts.
    (sandbox / ".shim" / "T1.sh").write_text(
        "echo x >> .shim/n\n"
        'if [ "$(grep -c x .shim/n)" -ge 2 ]; then git checkout -q -- other.txt;'
        " else echo v2 > other.txt; fi\n"
        'echo data > t1.txt\necho "STATUS: done"\n'
    )
    _setup(sandbox, T1)
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _state(sandbox)["T1"] == "done"
    assert "t1.txt" in _git(sandbox, "show", "--name-only", "--format=", "HEAD")
    dirty = [
        ln
        for ln in _git(sandbox, "status", "--porcelain").splitlines()
        if "work/feat/" not in ln  # run state / journal (gitignored in a real repo)
    ]
    assert dirty == []


def test_preexisting_dirt_and_parallel_siblings_are_not_leaks(sandbox: Path) -> None:
    (sandbox / ".shim" / "T1.sh").write_text('echo a > t1.txt\necho "STATUS: done"\n')
    (sandbox / ".shim" / "T2.sh").write_text('echo b > t2.txt\necho "STATUS: done"\n')
    _setup(
        sandbox,
        T1
        + """
### T2 — Sibling in the same wave
- **depends_on :** —
- **parallel_group :** A
- **implements :** [doc]
- **files_touched :** `t2.txt`
- **done_when :** ok
- **verify :** `true`
""",
    )
    (sandbox / "other.txt").write_text("dirty before the run\n")  # Owner's WIP
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "scope leak" not in r.stdout
    assert _state(sandbox) == {"T1": "done", "T2": "done"}
    assert "other.txt" in _git(sandbox, "status", "--porcelain")  # untouched WIP
