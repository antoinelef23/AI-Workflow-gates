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
import subprocess
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
) -> list[str]:
    """Build the `claude -p` argv. Shared by the host and sandbox runners so the
    agent-facing command is identical in both.

    add_dirs grants the agent read access to directories outside its cwd — used when
    the build runs in an external project (cwd=PROJECT) but the agent must read the
    framework files under the LAB. Empty/None by default, so the in-repo path and every
    test produce an unchanged argv."""
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
    ) -> RunResult:
        cmd = claude_argv(
            prompt,
            model=model,
            resume=resume,
            allowed_tools=allowed_tools,
            max_turns=max_turns,
            permission_mode=permission_mode,
            add_dirs=add_dirs,
        )
        try:
            p = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return RunResult(
                False, "", None, 0.0, f"timeout: agent killed after {timeout}s"
            )
        return parse_claude_json(p.returncode, p.stdout, p.stderr)


def get_runner() -> AgentRunner:
    """Pick the runner from LAB_RUNNER (default: claude-cli)."""
    name = (os.environ.get("LAB_RUNNER") or "claude-cli").strip().lower()
    if name in ("", "claude-cli", "host"):
        return ClaudeCliRunner()
    if name == "sandbox":
        from sandbox_runner import SandboxedClaudeRunner

        return SandboxedClaudeRunner()
    raise ValueError(f"unknown LAB_RUNNER={name!r} (expected: claude-cli | sandbox)")
