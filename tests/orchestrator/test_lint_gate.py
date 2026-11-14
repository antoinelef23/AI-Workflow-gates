"""The project's own `just lint-check` is part of a task's gate (fde-kit CP-5:
T14's verify ran only its test, unformatted code reached the merge checkpoint)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .conftest import JUSTFILE, run_orch

FM = "---\ntype: tasks\nfeature: feat\nstatus: approved\n---\n\n# Tasks — feat\n"
T1 = """
### T1 — Task
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`
"""
LINT = """
lint-check:
    #!/usr/bin/env bash
    if [ -f .shim/lint_fail ]; then echo "would reformat t1.txt"; exit 1; fi
    echo "[stub] lint ok"
"""


def _setup(sb: Path) -> None:
    (sb / "justfile").write_text(JUSTFILE + LINT)
    subprocess.run(["git", "commit", "-qam", "lint recipe"], cwd=sb, check=True)
    (sb / "work" / "feat" / "tasks.md").write_text(FM + T1)


def _state(sb: Path) -> dict:
    return json.loads((sb / "work" / "feat" / ".runs" / "state.json").read_text())[
        "tasks"
    ]


def test_red_lint_is_sent_back_and_fixed_on_retry(sandbox: Path) -> None:
    _setup(sandbox)
    (sandbox / ".shim" / "T1.sh").write_text(
        "echo x >> .shim/n\n"
        'if [ "$(grep -c x .shim/n)" -ge 2 ]; then rm -f .shim/lint_fail;'
        " else touch .shim/lint_fail; fi\n"
        'echo data > t1.txt\necho "STATUS: done"\n'
    )
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _state(sandbox)["T1"] == "done"
    argv = (sandbox / ".shim" / "argv.log").read_text()
    assert "LINT RED" in argv  # the retry prompt carried the lint feedback


def test_lint_that_stays_red_never_commits(sandbox: Path) -> None:
    _setup(sandbox)
    (sandbox / ".shim" / "T1.sh").write_text(
        'touch .shim/lint_fail\necho data > t1.txt\necho "STATUS: done"\n'
    )
    r = run_orch(sandbox)
    assert r.returncode == 1, r.stdout + r.stderr
    assert _state(sandbox)["T1"] == "failed"
    shown = subprocess.run(
        ["git", "log", "--name-only", "--format="],
        cwd=sandbox,
        capture_output=True,
        text=True,
    ).stdout
    assert "t1.txt" not in shown


def test_no_lint_recipe_means_no_lint(sandbox: Path) -> None:
    (sandbox / "work" / "feat" / "tasks.md").write_text(FM + T1)
    (sandbox / ".shim" / "T1.sh").write_text(
        'touch .shim/lint_fail\necho data > t1.txt\necho "STATUS: done"\n'
    )
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
