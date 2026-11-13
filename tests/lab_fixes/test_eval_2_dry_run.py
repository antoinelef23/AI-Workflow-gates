"""EVAL-2 — a dry run leaves no trace (BHV-2, INV-2)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from tests.orchestrator.conftest import run_orch

pytest_plugins = ["tests.orchestrator.conftest"]

PLAN = """---
type: tasks
feature: feat
status: approved
---

### T1 — A
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`

### CP-1 — CHECKPOINT : merge
- **trigger :** auto when [T1] done
- **validator :** Owner
- **mode :** blocking
"""


def _snapshot(runs: Path) -> dict[str, str] | None:
    if not runs.exists():
        return None
    return {
        str(p.relative_to(runs)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(runs.rglob("*"))
        if p.is_file()
    }


@pytest.mark.eval
def test_eval_2_dry_run_without_a_run_record_creates_nothing(sandbox: Path) -> None:
    feat = sandbox / "work" / "feat"
    (feat / "tasks.md").write_text(PLAN)
    r = run_orch(sandbox, "--dry-run")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "dry-run" in r.stdout
    assert not (feat / ".runs").exists()  # still absent


@pytest.mark.eval
def test_eval_2_dry_run_with_a_run_record_is_byte_identical(sandbox: Path) -> None:
    feat = sandbox / "work" / "feat"
    (feat / "tasks.md").write_text(PLAN)
    runs = feat / ".runs"
    runs.mkdir()
    (runs / "journal.jsonl").write_text('{"event": "run_start", "ts": "t"}\n')
    (runs / "state.json").write_text('{"T1": "done", "CP-1": "pending"}')
    before = _snapshot(runs)
    r = run_orch(sandbox, "--dry-run")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _snapshot(runs) == before
