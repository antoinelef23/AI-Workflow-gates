"""EVAL-1 — interrupting a run stops it entirely (BHV-1, BHV-1a, BHV-1b, INV-1).

Real signals sent to the orchestrator subprocess, with the deterministic claude shim of
the orchestrator suite. The shim agent drops a marker file when its turn starts, then
sleeps: the signal is sent only once the markers show the turn is running."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.orchestrator.conftest import ORCH, TEST_SECRET, approve

# Reuse the orchestrator suite's git sandbox + claude shim fixture.
pytest_plugins = ["tests.orchestrator.conftest"]

FM = "---\ntype: tasks\nfeature: feat\nstatus: approved\n---\n\n# Tasks — feat\n"
SLEEP_MARK = "13.37"  # unique sleep duration: lets the test find stray shim processes
WAVE = """
### T0 — First
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t0.txt`
- **done_when :** ok
- **verify :** `true`

### T1 — Slow one
- **depends_on :** [T0]
- **parallel_group :** A
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`

### T2 — Slow two
- **depends_on :** [T0]
- **parallel_group :** A
- **implements :** [doc]
- **files_touched :** `t2.txt`
- **done_when :** ok
- **verify :** `true`
"""
CP_PLAN = """
### T1 — Quick
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
OWNER_PLAN = """
### T1 — By hand
- **depends_on :** —
- **agent :** owner
- **implements :** [doc]
- **files_touched :** `owner.txt`
- **done_when :** ok
- **verify :** `python3 .shim/slow_verify.py`
"""


def _start(sb: Path) -> subprocess.Popen:
    env = dict(os.environ)
    env.update(
        LAB_ROOT=str(sb),
        LAB_NO_NOTIFY="1",
        LAB_TASK_TIMEOUT="120",
        LAB_APPROVAL_SECRET=TEST_SECRET,
        PATH=str(sb / "bin") + os.pathsep + os.environ["PATH"],
    )
    return subprocess.Popen(
        [sys.executable, str(ORCH), "work/feat"],
        cwd=sb,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _wait_for(cond, what: str, timeout: float = 60) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return
        time.sleep(0.1)
    raise AssertionError("timeout waiting for " + what)


def _slow_shim(sb: Path, tid: str) -> None:
    (sb / ".shim" / (tid + ".sh")).write_text(
        f"touch .shim/started_{tid}\nsleep {SLEEP_MARK}\n"
        f'echo x > {tid.lower()}.txt\necho "STATUS: done"\n'
    )


def _commits(sb: Path) -> int:
    return int(
        subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=sb,
            capture_output=True,
            text=True,
        ).stdout
    )


def _feat(sb: Path) -> Path:
    return sb / "work" / "feat"


def _events(sb: Path) -> list[dict]:
    j = _feat(sb) / ".runs" / "journal.jsonl"
    return [json.loads(ln) for ln in j.read_text().splitlines()]


def _state(sb: Path) -> dict:
    return json.loads((_feat(sb) / ".runs" / "state.json").read_text())["tasks"]


def _stray_shim() -> bool:
    r = subprocess.run(["pgrep", "-f", "sleep " + SLEEP_MARK], capture_output=True)
    return r.returncode == 0


def _wave_running(sb: Path) -> None:
    (_feat(sb) / "tasks.md").write_text(FM + WAVE)
    _slow_shim(sb, "T1")
    _slow_shim(sb, "T2")


@pytest.mark.eval
@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_eval_1_interrupt_during_a_parallel_wave(sandbox: Path, sig) -> None:
    _wave_running(sandbox)
    proc = _start(sandbox)
    try:
        _wait_for(
            lambda: (
                (sandbox / ".shim" / "started_T1").exists()
                and (sandbox / ".shim" / "started_T2").exists()
            ),
            "both agent turns to start",
        )
        before = _commits(sandbox)  # T0 is done and committed
        proc.send_signal(sig)
        out, _ = proc.communicate(timeout=60)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert proc.returncode == 130, out
    assert _commits(sandbox) == before  # INV-1: no new commit
    assert not _stray_shim()
    assert _state(sandbox) == {"T0": "done", "T1": "pending", "T2": "pending"}
    last = _events(sandbox)[-1]
    assert last["event"] == "run_interrupted"
    assert last["inflight"] == ["T1", "T2"]
    assert last["signal"] == sig.name
    assert "Resume" in out
    assert not (sandbox / "t1.txt").exists()  # the killed agents never finished


@pytest.mark.eval
def test_eval_1_a_second_signal_exits_at_once(sandbox: Path) -> None:
    _wave_running(sandbox)
    # An agent that ignores SIGTERM keeps the graceful drain waiting for its grace period.
    (sandbox / ".shim" / "T1.sh").write_text(
        f"trap '' TERM\ntouch .shim/started_T1\nsleep {SLEEP_MARK}\n"
    )
    proc = _start(sandbox)
    try:
        _wait_for(lambda: (sandbox / ".shim" / "started_T1").exists(), "T1 to start")
        before = _commits(sandbox)
        proc.send_signal(signal.SIGINT)
        time.sleep(0.5)
        t0 = time.monotonic()
        proc.send_signal(signal.SIGINT)
        proc.communicate(timeout=30)
        assert time.monotonic() - t0 < 4  # well under the 5 s SIGTERM grace
    finally:
        if proc.poll() is None:
            proc.kill()
    assert proc.returncode == 130
    assert _commits(sandbox) == before
    state = _state(sandbox)  # whole file, never partial (atomic write)
    assert state["T0"] == "done"
    _wait_for(lambda: not _stray_shim(), "stray agents to be killed", timeout=10)


@pytest.mark.eval
def test_eval_1_interrupt_at_a_blocking_checkpoint_leaves_it_pending(
    sandbox: Path,
) -> None:
    (_feat(sandbox) / "tasks.md").write_text(FM + CP_PLAN)
    proc = _start(sandbox)
    try:
        seen = ""
        end = time.monotonic() + 60
        while "waiting for" not in seen and time.monotonic() < end:
            line = proc.stdout.readline()
            if not line:
                break
            seen += line
        assert "waiting for" in seen, seen
        before = _commits(sandbox)
        proc.send_signal(signal.SIGINT)
        out, _ = proc.communicate(timeout=30)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert proc.returncode == 130, seen + out
    assert _commits(sandbox) == before
    assert _state(sandbox) == {"T1": "done", "CP-1": "pending"}
    last = _events(sandbox)[-1]
    assert last["event"] == "run_interrupted" and last["inflight"] == []
    assert not list((_feat(sandbox) / ".approvals").glob("CP-1*"))


def _read_until(proc: subprocess.Popen, needle: str) -> str:
    seen = ""
    end = time.monotonic() + 60
    while needle not in seen and time.monotonic() < end:
        line = proc.stdout.readline()
        if not line:
            break
        seen += line
    assert needle in seen, seen
    return seen


@pytest.mark.eval
def test_eval_1_interrupt_waiting_for_an_owner_signature_is_not_inflight(
    sandbox: Path,
) -> None:
    (_feat(sandbox) / "tasks.md").write_text(FM + OWNER_PLAN)
    proc = _start(sandbox)
    try:
        seen = _read_until(proc, "waiting for")
        before = _commits(sandbox)
        proc.send_signal(signal.SIGINT)
        out, _ = proc.communicate(timeout=30)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert proc.returncode == 130, seen + out
    assert _commits(sandbox) == before
    assert _state(sandbox) == {"T1": "pending"}
    last = _events(sandbox)[-1]
    assert last["event"] == "run_interrupted" and last["inflight"] == []


@pytest.mark.eval
def test_eval_1_interrupt_after_an_owner_signature_requires_a_new_signature(
    sandbox: Path,
) -> None:
    (_feat(sandbox) / "tasks.md").write_text(FM + OWNER_PLAN)
    (sandbox / "owner.txt").write_text("done by hand\n")
    (sandbox / ".shim" / "slow_verify.py").write_text(
        "import pathlib, sys, time\n"
        "pathlib.Path('.shim/verify_started').touch()\n"
        "time.sleep(3)\n"
        "sys.exit(0 if pathlib.Path('owner.txt').exists() else 1)\n"
    )
    approve(sandbox, "T1")
    before = _commits(sandbox)
    proc = _start(sandbox)
    try:
        _wait_for(lambda: (sandbox / ".shim" / "verify_started").exists(), "verify")
        proc.send_signal(signal.SIGINT)
        out, _ = proc.communicate(timeout=60)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert proc.returncode == 130, out
    assert _commits(sandbox) == before  # INV-1: signed, interrupted, never committed
    assert _state(sandbox) == {"T1": "pending"}
    last = _events(sandbox)[-1]
    assert last["event"] == "run_interrupted" and last["inflight"] == ["T1"]

    # Restart: the consumed signature is not reused — the engine waits for a new one.
    proc = _start(sandbox)
    try:
        seen = _read_until(proc, "waiting for")
        assert _commits(sandbox) == before
        approve(sandbox, "T1")
        out, _ = proc.communicate(timeout=60)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert proc.returncode == 0, seen + out
    assert _commits(sandbox) == before + 1


PANEL_PLAN = CP_PLAN.replace(
    "- **mode :** blocking", "- **mode :** blocking\n- **reviewers :** 2"
)


@pytest.mark.eval
def test_eval_1_interrupt_during_a_two_reviewer_panel_starts_no_second_reviewer(
    sandbox: Path,
) -> None:
    (_feat(sandbox) / "tasks.md").write_text(FM + PANEL_PLAN)
    # Each reviewer turn logs itself, then sleeps: the signal lands during panelist 1.
    (sandbox / ".shim" / "REVIEW.sh").write_text(
        f"echo turn >> .shim/review_turns\nsleep {SLEEP_MARK}\necho 'VERDICT: PASS'\n"
    )
    proc = _start(sandbox)
    try:
        _wait_for(lambda: (sandbox / ".shim" / "review_turns").exists(), "reviewer 1")
        before = _commits(sandbox)
        proc.send_signal(signal.SIGINT)
        out, _ = proc.communicate(timeout=60)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert proc.returncode == 130, out
    assert _commits(sandbox) == before
    turns = (sandbox / ".shim" / "review_turns").read_text().split()
    assert turns == ["turn"]  # INV-1: the second reviewer never started
    assert not _stray_shim()
    assert _state(sandbox) == {"T1": "done", "CP-1": "pending"}
    events = _events(sandbox)
    assert not [e for e in events if e["event"] == "review"]
    assert events[-1]["event"] == "run_interrupted" and events[-1]["inflight"] == []
    assert not (_feat(sandbox) / ".runs" / "CP-1-review.md").exists()
    assert not list((_feat(sandbox) / ".approvals").glob("CP-1*"))
