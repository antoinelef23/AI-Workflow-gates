"""EVAL-5 (INV-4, BHV-5a, ADR-18) — the engine reads/writes run state v2: the CP rejection
counter survives a restart; git alone resumes done tasks; the old flat state.json resumes."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.orchestrator.conftest import (  # noqa: F401  (sandbox = fixture)
    ORCH,
    TEST_SECRET,
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
PLAN = (
    T1
    + """
### CP-1 — CHECKPOINT : merge
- **trigger :** auto when [T1] done
- **validator :** Owner
- **mode :** blocking
"""
)
PLAN_2T = (
    T1
    + """
### T2 — Task two
- **depends_on :** [T1]
- **implements :** [doc]
- **files_touched :** `t2.txt`
- **done_when :** ok
- **verify :** `true`
"""
)


def _feat(sb: Path) -> Path:
    return sb / "work" / "feat"


def _state(sb: Path) -> dict:
    return json.loads((_feat(sb) / ".runs" / "state.json").read_text())


def _reject(sb: Path) -> None:
    d = _feat(sb) / ".approvals"
    d.mkdir(parents=True, exist_ok=True)
    (d / "CP-1.rejected").write_text("reason=nope\ntasks=T1\n")


def _launch(sb: Path) -> subprocess.Popen:
    env = {
        **os.environ,
        "LAB_ROOT": str(sb),
        "LAB_NO_NOTIFY": "1",
        "LAB_TASK_TIMEOUT": "60",
        "LAB_APPROVAL_SECRET": TEST_SECRET,
        "PATH": str(sb / "bin") + os.pathsep + os.environ["PATH"],
    }
    return subprocess.Popen(
        [sys.executable, str(ORCH), "work/feat"],
        cwd=sb,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _wait_for(cond, timeout: float = 90.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.2)
    return False


def _calls(sb: Path, tid: str) -> int:
    log = sb / ".shim" / "argv.log"
    return log.read_text().count("task " + tid) if log.exists() else 0


def _persisted(sb: Path, n: int) -> bool:
    if not (_feat(sb) / ".runs" / "state.json").exists():
        return False
    try:
        return _state(sb).get("rejections", {}).get("CP-1") == n
    except ValueError:
        return False


def test_eval_5_cp_rejections_survive_restarts(sandbox: Path) -> None:  # noqa: F811
    (_feat(sandbox) / "tasks.md").write_text(FM + PLAN)
    # Two rejections (= the default budget), each in its own engine process, killed between.
    for n in (1, 2):
        _reject(sandbox)
        p = _launch(sandbox)
        try:
            assert _wait_for(lambda n=n: _persisted(sandbox, n)), (
                "rejection %d not persisted" % n
            )
            p.send_signal(signal.SIGINT)
            p.wait(timeout=60)
        finally:
            if p.poll() is None:
                p.kill()
        assert _state(sandbox)["schema_version"] == 2
    # Third engine: the third rejection exceeds the budget ⇒ the CP fails.
    _reject(sandbox)
    r = run_orch(sandbox)
    assert r.returncode != 0, r.stdout + r.stderr
    assert _state(sandbox)["tasks"]["CP-1"] == "failed"
    assert _state(sandbox)["rejections"]["CP-1"] == 3


def test_eval_5_done_task_with_commit_survives_state_deletion(sandbox: Path) -> None:  # noqa: F811
    (_feat(sandbox) / "tasks.md").write_text(FM + PLAN_2T)
    subprocess.run(
        ["git", "commit", "-q", "--allow-empty", "-m", "feat(feat): T1 first [BHV-1]"],
        cwd=sandbox,
        check=True,
    )
    assert not (_feat(sandbox) / ".runs" / "state.json").exists()
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _calls(sandbox, "T1") == 0, "T1 is done in git: it must not rerun"
    assert _calls(sandbox, "T2") >= 1
    assert "run state lost" in r.stdout + r.stderr


def test_eval_5_old_flat_state_json_resumes(sandbox: Path) -> None:  # noqa: F811
    (_feat(sandbox) / "tasks.md").write_text(FM + PLAN_2T)
    runs = _feat(sandbox) / ".runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "state.json").write_text(json.dumps({"T1": "done", "T2": "pending"}))
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _calls(sandbox, "T1") == 0
    assert _calls(sandbox, "T2") >= 1
    st = _state(sandbox)
    assert st["schema_version"] == 2 and st["tasks"]["T2"] == "done"
