"""Orchestrator test harness: git sandbox + deterministic `claude` shim.

The shim replaces the real claude CLI via PATH. It extracts the task ID from the
prompt and runs the scenario `$LAB_ROOT/.shim/<ID>.sh` if it exists (its output =
the agent's reply), otherwise it replies `STATUS: done` (or `VERDICT: PASS` for
the reviewer). The reply is wrapped in the real CLI's `--output-format json` JSON.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ORCH = REPO / "lab" / "engine" / "orchestrate.py"
sys.path.insert(0, str(REPO / "lab" / "engine"))
import approvals  # noqa: E402

# Test secret: the tests exercise the SECURE path (signed tokens) by default.
TEST_SECRET = "test-approval-secret"

SHIM = """#!/usr/bin/env bash
# claude shim for the orchestrator tests — deterministic, instant.
[ -n "${LAB_ROOT:-}" ] && echo "$@" >> "$LAB_ROOT/.shim/argv.log"
PROMPT="$2"
ID=""
if echo "$PROMPT" | grep -q "reviewer agent"; then
  ID="REVIEW"
else
  ID=$(echo "$PROMPT" | grep -oE "task (T[0-9]+|CP-[0-9]+)" | head -1 | awk '{print $2}')
fi
OUT="STATUS: done"
[ "$ID" = "REVIEW" ] && OUT="VERDICT: PASS"
if [ -n "$ID" ] && [ -f "$LAB_ROOT/.shim/$ID.sh" ]; then
  OUT=$(bash "$LAB_ROOT/.shim/$ID.sh")
fi
OUT="$OUT" python3 -c 'import json, os; print(json.dumps({"type": "result", "result": os.environ["OUT"], "session_id": "shim-session", "total_cost_usd": 0.001}))'
"""

JUSTFILE = """evals:
    #!/usr/bin/env bash
    if [ -f .evals_fail ]; then echo "EVALS RED (stub)"; exit 1; fi
    echo "[stub] evals ok"
"""

SPEC = """---
type: spec
feature: feat
version: 1.0.0
status: validated
---

# Spec — feat (sandbox)

- **INV-1** — The system MUST exist.
- **BHV-1** — Given/When/Then test.
- EVAL-1: test eval.
"""


@pytest.fixture()
def sandbox(tmp_path: Path) -> Path:
    sb = tmp_path / "sb"
    (sb / "work" / "feat").mkdir(parents=True)
    (sb / "bin").mkdir()
    (sb / ".shim").mkdir()
    (sb / "justfile").write_text(JUSTFILE)
    (sb / "work" / "feat" / "spec.md").write_text(SPEC)
    shim = sb / "bin" / "claude"
    shim.write_text(SHIM)
    shim.chmod(0o755)
    subprocess.run(["git", "init", "-q"], cwd=sb, check=True)
    subprocess.run(["git", "config", "user.email", "test@lab"], cwd=sb, check=True)
    subprocess.run(["git", "config", "user.name", "lab-test"], cwd=sb, check=True)
    subprocess.run(["git", "add", "-A"], cwd=sb, check=True)
    subprocess.run(["git", "commit", "-qm", "init sandbox"], cwd=sb, check=True)
    return sb


def run_orch(
    sandbox: Path,
    *flags: str,
    feature: str = "work/feat",
    env_extra: dict | None = None,
):
    env = {
        **os.environ,
        "LAB_ROOT": str(sandbox),
        "LAB_NO_NOTIFY": "1",
        "LAB_TASK_TIMEOUT": "60",
        "LAB_APPROVAL_SECRET": TEST_SECRET,  # secure path by default (signed tokens)
        "PATH": f"{sandbox / 'bin'}:{os.environ['PATH']}",
        **(env_extra or {}),
    }
    return subprocess.run(
        [sys.executable, str(ORCH), feature, *flags],
        cwd=sandbox,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def approve(sandbox: Path, cp: str, feature: str = "work/feat") -> None:
    """Drop a SIGNED approval token with TEST_SECRET (as lab/engine/approve.sh would
    with LAB_APPROVAL_SECRET set)."""
    fdir = (sandbox / feature).resolve()
    d = fdir / ".approvals"
    d.mkdir(parents=True, exist_ok=True)
    old = os.environ.get(approvals.ENV_SECRET)
    os.environ[approvals.ENV_SECRET] = TEST_SECRET
    try:
        (d / cp).write_text(approvals.sign(fdir, cp, "test", "2026-01-01T00:00:00"))
    finally:
        if old is None:
            os.environ.pop(approvals.ENV_SECRET, None)
        else:
            os.environ[approvals.ENV_SECRET] = old


def write_registry(sandbox: Path, toml: str) -> None:
    (sandbox / "lab" / "models").mkdir(parents=True, exist_ok=True)
    (sandbox / "lab" / "models" / "registry.toml").write_text(toml)


def argv_log(sandbox: Path) -> str:
    p = sandbox / ".shim" / "argv.log"
    return p.read_text() if p.exists() else ""
