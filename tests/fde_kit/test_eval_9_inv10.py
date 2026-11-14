"""EVAL-9 (INV-10) — a task whose working tree touches spec.md / design.md fails, and the
scoped commit never stages them."""

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
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`
"""


def _git(sb: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=sb, capture_output=True, text=True, check=True
    ).stdout


@pytest.mark.parametrize("name", ["spec.md", "design.md"])
def test_eval_9_agent_edit_of_human_artefact_fails_the_task(
    sandbox: Path,  # noqa: F811
    name: str,
) -> None:
    feat = sandbox / "work" / "feat"
    (feat / "design.md").write_text("# design\n")
    (feat / "tasks.md").write_text(FM + T1)
    _git(sandbox, "add", "-A")
    _git(sandbox, "commit", "-qm", "plan")
    head = _git(sandbox, "rev-parse", "HEAD").strip()
    (sandbox / ".shim" / "T1.sh").write_text(
        f"echo data > t1.txt\necho '- OQ-9 sneaked in' >> work/feat/{name}\n"
        'echo "STATUS: done"\n'
    )
    r = run_orch(sandbox)
    assert r.returncode == 1, r.stdout + r.stderr
    state = json.loads((feat / ".runs" / "state.json").read_text())["tasks"]
    assert state["T1"] == "failed"
    assert _git(sandbox, "rev-parse", "HEAD").strip() == head  # nothing committed
    assert f"modified work/feat/{name}" in r.stdout, r.stdout


def test_eval_9_commit_never_stages_spec_or_design(sandbox: Path) -> None:  # noqa: F811
    """Direct guard on scoped_commit: even if a path of the feature were listed, the
    human artefacts are not staged."""
    import orchestrate

    feat = sandbox / "work" / "feat"
    (feat / "design.md").write_text("# design\n")
    (feat / "tasks.md").write_text(FM + T1)
    _git(sandbox, "add", "-A")
    _git(sandbox, "commit", "-qm", "plan")
    (feat / "spec.md").write_text("changed\n")
    (feat / "design.md").write_text("changed\n")
    (sandbox / "t1.txt").write_text("x\n")
    old = orchestrate.PROJECT
    orchestrate.PROJECT = sandbox
    try:
        node = orchestrate.Node(
            "T1",
            "t",
            False,
            files=["t1.txt", "work/feat/spec.md", "work/feat/design.md"],
        )
        orchestrate.scoped_commit(
            node, feat, "feat(feat): t [BHV-1]\n\nWhy: x\n\nRun: t"
        )
    finally:
        orchestrate.PROJECT = old
    shown = _git(sandbox, "show", "--name-only", "--format=", "HEAD").split()
    assert "t1.txt" in shown
    assert "work/feat/spec.md" not in shown and "work/feat/design.md" not in shown
