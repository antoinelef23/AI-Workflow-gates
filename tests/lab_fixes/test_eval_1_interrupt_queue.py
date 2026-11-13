"""EVAL-1 (queue) — a task still queued when the signal arrives is not in flight (BHV-1).

3 tasks, max_parallel = 2: SIGINT while the first two are mid-turn ⇒ `inflight` lists only
those two; the queued third stays pending."""

from __future__ import annotations

import signal
from pathlib import Path

import pytest

from tests.lab_fixes.test_eval_1_interrupt import (
    FM,
    _commits,
    _events,
    _feat,
    _slow_shim,
    _start,
    _state,
    _stray_shim,
    _wait_for,
)

pytest_plugins = ["tests.orchestrator.conftest"]

WAVE3 = "".join(
    f"""
### T{i} — Slow {i}
- **depends_on :** —
- **parallel_group :** A
- **implements :** [doc]
- **files_touched :** `t{i}.txt`
- **done_when :** ok
- **verify :** `true`
"""
    for i in (1, 2, 3)
)


@pytest.mark.eval
def test_eval_1_queued_task_is_not_inflight(sandbox: Path) -> None:
    lab_toml = sandbox / ".lab" / "lab.toml"
    lab_toml.write_text(lab_toml.read_text() + "\n[overrides]\nmax_parallel = 2\n")
    (_feat(sandbox) / "tasks.md").write_text(FM + WAVE3)
    for t in ("T1", "T2", "T3"):
        _slow_shim(sandbox, t)
    proc = _start(sandbox)
    try:
        _wait_for(
            lambda: (
                (sandbox / ".shim" / "started_T1").exists()
                and (sandbox / ".shim" / "started_T2").exists()
            ),
            "the first two agent turns to start",
        )
        before = _commits(sandbox)
        proc.send_signal(signal.SIGINT)
        out, _ = proc.communicate(timeout=60)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert proc.returncode == 130, out
    assert _commits(sandbox) == before
    assert not (sandbox / ".shim" / "started_T3").exists()  # never got a turn
    assert not _stray_shim()
    assert _state(sandbox) == {"T1": "pending", "T2": "pending", "T3": "pending"}
    last = _events(sandbox)[-1]
    assert last["event"] == "run_interrupted"
    assert last["inflight"] == ["T1", "T2"]
