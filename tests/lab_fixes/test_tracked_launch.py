"""T1 — tracked launcher (spec BHV-1 / INV-1, design ADR-1). Plain tests, not evals."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lab" / "engine"))
import runner  # noqa: E402

# Spawns a child (prints both pids), then sleeps.
PARENT = (
    "import subprocess, sys, os, time\n"
    "c = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
    "print(os.getpid(), c.pid, flush=True)\n"
    "time.sleep(60)\n"
)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:  # a zombie is not "alive" for our purpose
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return False


def _pgid(pid: int) -> int | None:
    try:
        return os.getpgid(pid)
    except ProcessLookupError:
        return None


def _wait_tracked() -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and not runner._TRACKED:
        time.sleep(0.05)
    assert runner._TRACKED


def _fake_claude(tmp_path: Path, body: str) -> dict:
    shim = tmp_path / "bin"
    shim.mkdir()
    c = shim / "claude"
    c.write_text(f"#!{sys.executable}\n{body}\n")
    c.chmod(0o755)
    return {**os.environ, "PATH": f"{shim}:{os.environ['PATH']}"}


def test_normal_run_returns_rc_stdout_stderr(tmp_path):
    code = "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)"
    rc, out, err = runner.run_tracked([sys.executable, "-c", code], tmp_path, None, 30)
    assert (rc, out.strip(), err.strip()) == (3, "out", "err")
    assert not runner._TRACKED


def test_terminate_all_kills_group_and_children(tmp_path):
    t = threading.Thread(
        target=lambda: runner.run_tracked(
            [sys.executable, "-c", PARENT], tmp_path, None, 120
        )
    )
    t.start()
    _wait_tracked()
    p = next(iter(runner._TRACKED))
    time.sleep(1)  # let the parent spawn its child
    pgid = os.getpgid(p.pid)
    assert pgid == p.pid  # own session / group
    members = [
        int(d) for d in os.listdir("/proc") if d.isdigit() and _pgid(int(d)) == pgid
    ]
    assert len(members) >= 2  # parent + child
    assert runner.terminate_all(grace_s=5) == 1
    t.join(20)
    assert not t.is_alive()
    assert all(not _alive(m) for m in members)
    assert not runner._TRACKED


def test_terminate_all_with_nothing_running():
    assert runner.terminate_all(grace_s=0.1) == 0


def test_terminate_all_sigkills_survivors(tmp_path):
    ignore = "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"
    t = threading.Thread(
        target=lambda: runner.run_tracked(
            [sys.executable, "-c", ignore], tmp_path, None, 120
        )
    )
    t.start()
    _wait_tracked()
    time.sleep(1)
    assert runner.terminate_all(grace_s=0.5) == 1
    t.join(20)
    assert not t.is_alive()


def test_timeout_raises_and_kills_group(tmp_path):
    with pytest.raises(subprocess.TimeoutExpired):
        runner.run_tracked([sys.executable, "-c", PARENT], tmp_path, None, 2)
    assert not runner._TRACKED


def test_cli_runner_timeout_result_unchanged(tmp_path):
    env = _fake_claude(tmp_path, "import time\ntime.sleep(60)")
    r = runner.ClaudeCliRunner().run("p", cwd=tmp_path, timeout=1, env=env)
    assert not r.ok
    assert r.error == "timeout: agent killed after 1s"


def test_cli_runner_normal_run(tmp_path):
    env = _fake_claude(tmp_path, 'print(\'{"result": "hi", "session_id": "s"}\')')
    r = runner.ClaudeCliRunner().run("p", cwd=tmp_path, timeout=30, env=env)
    assert r.ok and r.text == "hi" and r.session_id == "s"
