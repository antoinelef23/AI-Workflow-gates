"""A parallel wave shares one working tree: a task must be judged neither on a sibling's
half-done edits nor charged with a stopped sibling's leftovers (fde-kit iteration 2,
wave T20 ∥ T22: T22's lint gate red on T20's WIP; T22's docs charged to T20)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .conftest import JUSTFILE, run_orch

FM = "---\ntype: tasks\nfeature: feat\nstatus: approved\n---\n\n# Tasks — feat\n"
PLAN = """
### T1 — Fast task
- **depends_on :** —
- **parallel_group :** A
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`

### T2 — Slow sibling
- **depends_on :** —
- **parallel_group :** A
- **implements :** [doc]
- **files_touched :** `t2.txt`
- **done_when :** ok
- **verify :** `true`
"""
LINT = """
lint-check:
    #!/usr/bin/env bash
    if [ -f .shim/lint_fail ]; then echo "would reformat t2.txt"; exit 1; fi
    echo "[stub] lint ok"
"""


def _setup(sb: Path) -> None:
    (sb / "justfile").write_text(JUSTFILE + LINT)
    subprocess.run(["git", "commit", "-qam", "lint recipe"], cwd=sb, check=True)
    (sb / "work" / "feat" / "tasks.md").write_text(FM + PLAN)


def _events(sb: Path) -> list[dict]:
    j = sb / "work" / "feat" / ".runs" / "journal.jsonl"
    return [json.loads(ln) for ln in j.read_text().splitlines()]


def test_a_task_is_not_judged_on_a_sibling_mid_turn(sandbox: Path) -> None:
    _setup(sandbox)
    (sandbox / ".shim" / "T1.sh").write_text('echo a > t1.txt\necho "STATUS: done"\n')
    # T2's half-done state turns the project lint red until its turn ends.
    (sandbox / ".shim" / "T2.sh").write_text(
        "touch .shim/lint_fail\nsleep 3\nrm -f .shim/lint_fail\n"
        'echo b > t2.txt\necho "STATUS: done"\n'
    )
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    attempts = [e for e in _events(sandbox) if e["event"] == "task_attempt"]
    assert [e["id"] for e in attempts].count("T1") == 1, r.stdout  # no false LINT RED


def test_a_stopped_siblings_leftovers_are_not_a_scope_leak(sandbox: Path) -> None:
    _setup(sandbox)
    (sandbox / ".shim" / "T2.sh").write_text(
        'echo b > t2.txt\necho "STATUS: blocked — needs the Owner"\n'
    )
    (sandbox / ".shim" / "T1.sh").write_text(
        'sleep 2\necho a > t1.txt\necho "STATUS: done"\n'
    )
    r = run_orch(sandbox)
    assert "scope leak" not in r.stdout, r.stdout
    state = json.loads((sandbox / "work" / "feat" / ".runs" / "state.json").read_text())
    assert state == {"T1": "done", "T2": "blocked"}


def test_a_wave_larger_than_max_parallel_neither_deadlocks_nor_misjudges(
    sandbox: Path,
) -> None:
    # 3 tasks, 2 workers: T3 is queued, then edits while T1/T2 may be judging.
    lab = sandbox / ".lab" / "lab.toml"
    lab.write_text(lab.read_text() + "\n[overrides]\nmax_parallel = 2\n")
    _setup(sandbox)
    (sandbox / "work" / "feat" / "tasks.md").write_text(
        FM
        + PLAN
        + PLAN.split("### T2")[1]
        .replace(" — Slow sibling", "### T3 — Queued sibling", 1)
        .replace("t2.txt", "t3.txt")
    )
    (sandbox / ".shim" / "T1.sh").write_text('echo a > t1.txt\necho "STATUS: done"\n')
    (sandbox / ".shim" / "T2.sh").write_text('echo b > t2.txt\necho "STATUS: done"\n')
    (sandbox / ".shim" / "T3.sh").write_text(
        "touch .shim/lint_fail\nsleep 2\nrm -f .shim/lint_fail\n"
        'echo c > t3.txt\necho "STATUS: done"\n'
    )
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    state = json.loads((sandbox / "work" / "feat" / ".runs" / "state.json").read_text())
    assert state == {"T1": "done", "T2": "done", "T3": "done"}
    ids = [e["id"] for e in _events(sandbox) if e["event"] == "task_attempt"]
    assert sorted(ids) == ["T1", "T2", "T3"], r.stdout  # one attempt each, no LINT RED
