#!/usr/bin/env python3
"""Agent runner abstraction — decouples the orchestrator from the execution backend.

The orchestrator depends on the AgentRunner interface, not on the `claude` CLI.
This is the seam that lets the runtime be swapped without touching orchestration
logic:
  - ClaudeCliRunner   — runs the agent via the local `claude` CLI on the host (default)
  - SandboxedClaudeRunner — runs the same call inside a hardened container with no
                            host filesystem access and an egress allowlist (see
                            lab/engine/sandbox_runner.py); the only configuration that
                            makes the signed-approval boundary a HARD boundary.

Select via LAB_RUNNER (claude-cli | sandbox). A future provider runner (Vertex /
Gemini / …) is just another AgentRunner implementation — no orchestrator change.
"""

from __future__ import annotations

import abc
import json
import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

# Minimal Bash whitelist so the implementer can run its tests (acceptEdits covers
# edits, not Bash). NOT a security boundary — confinement is the sandbox runner.
DEFAULT_ALLOWED_TOOLS = [
    "Bash(uv:*)",
    "Bash(make:*)",
    "Bash(python3:*)",
    "Bash(mkdir:*)",
    "Bash(ls:*)",
    "Bash(git diff:*)",
    "Bash(git log:*)",
]


# --- Tracked launcher (design ADR-1) -------------------------------------------
# Every agent process is started in its own session/process group and registered
# here while it runs, so the engine can terminate all of them (and their children)
# on an interrupt. `docker run --rm` for the sandbox: the container goes with its
# client's group.
_TRACKED: set[subprocess.Popen] = set()
_TRACKED_LOCK = threading.Lock()
# Set (under _TRACKED_LOCK) by the first terminate_all / kill_all_now: the engine is shutting
# down. A process registered after that snapshot was taken would escape it, so run_tracked
# checks this flag in the same locked block as its registration and kills its own group
# (INV-1: no agent turn runs after an interrupt).
_STOPPING = False


def _killpg(p: subprocess.Popen, sig: int) -> None:
    try:
        os.killpg(p.pid, sig)  # session leader ⇒ pgid == pid
    except (ProcessLookupError, PermissionError):
        pass


def run_tracked(
    cmd: list[str], cwd: Path | str | None, env: dict | None, timeout: float | None
) -> tuple[int, str, str]:
    """Run `cmd` in its own process group, tracked until it ends.

    Returns (returncode, stdout, stderr). On timeout the whole group is killed and
    subprocess.TimeoutExpired is re-raised (callers keep their timeout message)."""
    p = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd is not None else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    with _TRACKED_LOCK:
        _TRACKED.add(p)
        stopping = _STOPPING
    if stopping:  # launched after the shutdown snapshot: it must not run
        _killpg(p, signal.SIGKILL)
    try:
        try:
            out, err = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _killpg(p, signal.SIGKILL)
            p.communicate()
            raise
        return p.returncode, out, err
    finally:
        with _TRACKED_LOCK:
            _TRACKED.discard(p)


def terminate_all(grace_s: float = 5) -> int:
    """SIGTERM every registered group, wait up to `grace_s`, SIGKILL the survivors.

    Returns the number of groups signalled. From then on, any new launch kills itself."""
    global _STOPPING
    with _TRACKED_LOCK:
        _STOPPING = True
        procs = list(_TRACKED)
    for p in procs:
        _killpg(p, signal.SIGTERM)
    deadline = time.monotonic() + grace_s
    for p in procs:
        # The leader may exit before its children: wait on the group, not the leader.
        while time.monotonic() < deadline and _group_alive(p):
            time.sleep(0.05)
    for p in procs:
        if _group_alive(p):
            _killpg(p, signal.SIGKILL)
    return len(procs)


def kill_all_now() -> int:
    """SIGKILL every registered group at once, no grace (second signal). Returns the
    number of groups signalled. From then on, any new launch kills itself."""
    global _STOPPING
    with _TRACKED_LOCK:
        _STOPPING = True
        procs = list(_TRACKED)
    for p in procs:
        _killpg(p, signal.SIGKILL)
    return len(procs)


def _group_alive(p: subprocess.Popen) -> bool:
    p.poll()  # reap the leader if it already exited, so it is not a zombie
    try:
        os.killpg(p.pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@dataclass
class RunResult:
    ok: bool
    text: str
    session_id: str | None
    cost_usd: float
    error: str


def claude_argv(
    prompt: str,
    *,
    model: str | None,
    resume: str | None,
    allowed_tools: list[str] | None,
    max_turns: int,
    permission_mode: str,
    add_dirs: list[str] | None = None,
    plugin_dir: str | None = None,
    settings: str | None = None,
    append_system_prompt: str | None = None,
) -> list[str]:
    """Build the `claude -p` argv. Shared by the host and sandbox runners so the
    agent-facing command is identical in both.

    add_dirs grants the agent read access to directories outside its cwd — used when
    the build runs in an external project (cwd=PROJECT) but the agent must read the
    framework files under the LAB. Empty/None by default, so the in-repo path and every
    test produce an unchanged argv.

    plugin_dir / settings / append_system_prompt carry the kit guardrails into the call
    (design ADR-2: `--plugin-dir`, `--settings` for the denies, `--append-system-prompt`
    for the hard rules). None by default ⇒ the argv is byte-identical to before. The
    engine never passes `--bare`."""
    cmd = [
        "claude",
        "-p",
        prompt,
        "--permission-mode",
        permission_mode,
        "--max-turns",
        str(max_turns),
        "--allowedTools",
        ",".join(allowed_tools or DEFAULT_ALLOWED_TOOLS),
        "--output-format",
        "json",
    ]
    for d in add_dirs or []:
        cmd += ["--add-dir", d]
    if model:
        cmd += ["--model", model]
    if resume:
        cmd += ["--resume", resume]
    if plugin_dir:
        cmd += ["--plugin-dir", plugin_dir]
    if settings:
        cmd += ["--settings", settings]
    if append_system_prompt:
        cmd += ["--append-system-prompt", append_system_prompt]
    return cmd


def parse_claude_json(returncode: int, stdout: str, stderr: str) -> RunResult:
    """Parse the `--output-format json` result. Shared by host/sandbox runners."""
    if returncode != 0:
        return RunResult(False, stdout, None, 0.0, stderr[-2000:] or stdout[-2000:])
    text, session_id, cost = stdout, None, 0.0
    try:
        data = json.loads(stdout)
        text = data.get("result") or ""
        session_id = data.get("session_id")
        cost = float(data.get("total_cost_usd") or 0.0)
    except (json.JSONDecodeError, TypeError):
        pass  # non-JSON output: keep the raw text
    return RunResult(True, text, session_id, cost, "")


class AgentRunner(abc.ABC):
    """Runs one headless agent turn and returns a structured result."""

    @abc.abstractmethod
    def run(
        self,
        prompt: str,
        *,
        cwd: Path,
        model: str | None = None,
        resume: str | None = None,
        allowed_tools: list[str] | None = None,
        max_turns: int = 100,
        permission_mode: str = "acceptEdits",
        timeout: int = 2400,
        env: dict | None = None,
        add_dirs: list[str] | None = None,
        plugin_dir: str | None = None,
        settings: str | None = None,
        append_system_prompt: str | None = None,
    ) -> RunResult: ...


class ClaudeCliRunner(AgentRunner):
    """Default runner: invokes the local `claude` CLI directly on the host.

    Confinement here is tool-allowlist only (NOT an OS boundary). The deterministic
    test shim intercepts the `claude` binary on PATH, so this path is what the
    orchestrator suite exercises."""

    name = "claude-cli"

    def run(
        self,
        prompt: str,
        *,
        cwd: Path,
        model: str | None = None,
        resume: str | None = None,
        allowed_tools: list[str] | None = None,
        max_turns: int = 100,
        permission_mode: str = "acceptEdits",
        timeout: int = 2400,
        env: dict | None = None,
        add_dirs: list[str] | None = None,
        plugin_dir: str | None = None,
        settings: str | None = None,
        append_system_prompt: str | None = None,
    ) -> RunResult:
        cmd = claude_argv(
            prompt,
            model=model,
            resume=resume,
            allowed_tools=allowed_tools,
            max_turns=max_turns,
            permission_mode=permission_mode,
            add_dirs=add_dirs,
            plugin_dir=plugin_dir,
            settings=settings,
            append_system_prompt=append_system_prompt,
        )
        try:
            rc, out, err = run_tracked(cmd, cwd, env, timeout)
        except subprocess.TimeoutExpired:
            return RunResult(
                False, "", None, 0.0, f"timeout: agent killed after {timeout}s"
            )
        return parse_claude_json(rc, out, err)


def get_runner() -> AgentRunner:
    """Pick the runner from LAB_RUNNER (default: claude-cli)."""
    name = (os.environ.get("LAB_RUNNER") or "claude-cli").strip().lower()
    if name in ("", "claude-cli", "host"):
        return ClaudeCliRunner()
    if name == "sandbox":
        from sandbox_runner import SandboxedClaudeRunner

        return SandboxedClaudeRunner()
    raise ValueError(f"unknown LAB_RUNNER={name!r} (expected: claude-cli | sandbox)")
