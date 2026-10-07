#!/usr/bin/env python3
"""Sandboxed agent runner — the confinement that makes the approval boundary HARD.

Threat it closes (finding M3/M4): on the host, an implementer that runs its own
tests inherently has code execution, so it can read the Owner's dotfiles/keychain
to steal LAB_APPROVAL_SECRET and then forge a *signed* checkpoint approval. The
signed-approval gate is therefore only defense-in-depth on the host.

This runner executes the SAME `claude -p` call inside a hardened container that:
  - mounts ONLY the repo (so $HOME / dotfiles / keychain are unreachable);
  - never receives LAB_APPROVAL_SECRET (curated env allowlist + explicit exclusion);
  - has restricted egress (an allowlist network/proxy — model API + package registry);
  - runs as the host uid (non-root), read-only rootfs + tmpfs, all caps dropped,
    no-new-privileges, pids/memory limits.

With the agent unable to reach the secret or the open internet, an unsigned token
it writes is rejected by the orchestrator (which verifies on the host with the
secret) — so the boundary holds.

Enable with LAB_RUNNER=sandbox. Tune with LAB_SANDBOX_IMAGE / LAB_SANDBOX_NETWORK /
LAB_SANDBOX_MEMORY. See docs/how-to/use-the-sandbox.md. End-to-end requires a Docker host with the
agent image built and `claude` auth available inside it; the argv construction
(the security-relevant part) is unit-tested without Docker.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from approvals import ENV_SECRET
from runner import AgentRunner, RunResult, claude_argv, parse_claude_json

# Only these env vars are forwarded INTO the container. LAB_APPROVAL_SECRET is not
# here (and is asserted-excluded below) — the whole point is that the agent can't
# get it. ANTHROPIC_* is the agent's own model credential (distinct from the secret).
SANDBOX_ENV_ALLOW = frozenset(
    {
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "LANG",
        "LC_ALL",
        "TZ",
        "CI",
        "NO_COLOR",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "UV_CACHE_DIR",
    }
)

DEFAULT_IMAGE = "lab-agent:latest"
# Default to a NAMED egress-restricted network the operator creates (see
# docs/how-to/use-the-sandbox.md). "none" would be max isolation but breaks the model call, so we
# require an explicit allowlist network for real runs.
DEFAULT_NETWORK = "lab-egress"
DEFAULT_MEMORY = "2g"
DEFAULT_PIDS = 512


def curate_env(env: dict | None) -> dict:
    """Forward only the allowlisted env vars; guarantee the approval secret is absent."""
    src = env or {}
    out = {k: v for k, v in src.items() if k in SANDBOX_ENV_ALLOW}
    out.pop(ENV_SECRET, None)  # belt-and-suspenders: never, ever
    return out


def build_docker_argv(
    *,
    image: str,
    network: str,
    workspace: Path,
    claude_cmd: list[str],
    env: dict,
    uid_gid: str | None,
    memory: str = DEFAULT_MEMORY,
    pids: int = DEFAULT_PIDS,
    home: str = "/home/agent",
) -> list[str]:
    """Pure builder for the hardened `docker run … claude …` argv (unit-tested).

    SECURITY INVARIANTS asserted by tests:
      - LAB_APPROVAL_SECRET never appears in the argv;
      - rootfs read-only, caps dropped, no-new-privileges, non-root, limited;
      - only the repo is bind-mounted (no host $HOME);
      - the agent-facing `claude` command is identical to the host runner.
    """
    argv = [
        "docker",
        "run",
        "--rm",
        "-i",
        "--network",
        network,
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev",
        "--tmpfs",
        f"{home}:rw,nosuid,nodev",
        "--pids-limit",
        str(pids),
        "--memory",
        memory,
        "-v",
        f"{workspace}:/workspace:rw",
        "-w",
        "/workspace",
        "-e",
        f"HOME={home}",
    ]
    if uid_gid:  # run as the host user → non-root AND can write the bind mount
        argv += ["--user", uid_gid]
    for k in sorted(env):
        argv += ["-e", f"{k}={env[k]}"]
    argv += [image, *claude_cmd]
    return argv


class SandboxedClaudeRunner(AgentRunner):
    """Runs the agent in a hardened container (LAB_RUNNER=sandbox)."""

    name = "sandbox"

    def __init__(self) -> None:
        self.image = os.environ.get("LAB_SANDBOX_IMAGE") or DEFAULT_IMAGE
        self.network = os.environ.get("LAB_SANDBOX_NETWORK") or DEFAULT_NETWORK
        self.memory = os.environ.get("LAB_SANDBOX_MEMORY") or DEFAULT_MEMORY

    def _uid_gid(self) -> str | None:
        getuid = getattr(os, "getuid", None)
        getgid = getattr(os, "getgid", None)
        if getuid and getgid:
            return f"{getuid()}:{getgid()}"
        return None  # non-Unix host: skip --user

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
        # NOTE: add_dirs (host paths outside the workspace, e.g. the LAB when building an
        # external project) is intentionally NOT forwarded — the sandbox bind-mounts ONLY
        # the workspace, so a host path would not exist inside the container. Driving an
        # external project from the sandbox would require also mounting the LAB read-only
        # (operator work, see docs/how-to/use-the-sandbox.md). Accepted here to keep the
        # AgentRunner interface uniform.
        claude_cmd = claude_argv(
            prompt,
            model=model,
            resume=resume,
            allowed_tools=allowed_tools,
            max_turns=max_turns,
            permission_mode=permission_mode,
        )
        argv = build_docker_argv(
            image=self.image,
            network=self.network,
            workspace=Path(cwd),
            claude_cmd=claude_cmd,
            env=curate_env(env),
            uid_gid=self._uid_gid(),
            memory=self.memory,
        )
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        except FileNotFoundError:
            return RunResult(
                False,
                "",
                None,
                0.0,
                "docker not found — the sandbox runner needs Docker",
            )
        except subprocess.TimeoutExpired:
            return RunResult(
                False,
                "",
                None,
                0.0,
                f"timeout: sandboxed agent killed after {timeout}s",
            )
        return parse_claude_json(p.returncode, p.stdout, p.stderr)
