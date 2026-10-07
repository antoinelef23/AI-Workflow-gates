"""AgentRunner abstraction + sandbox argv security invariants (no Docker needed)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "lab" / "engine"))

import runner as rn  # noqa: E402
import sandbox_runner as sb  # noqa: E402
from approvals import ENV_SECRET  # noqa: E402


# ---------------------------------------------------------------- runner selection


def test_get_runner_default_is_claude_cli(monkeypatch):
    monkeypatch.delenv("LAB_RUNNER", raising=False)
    assert isinstance(rn.get_runner(), rn.ClaudeCliRunner)


def test_get_runner_sandbox(monkeypatch):
    monkeypatch.setenv("LAB_RUNNER", "sandbox")
    assert isinstance(rn.get_runner(), sb.SandboxedClaudeRunner)


def test_get_runner_unknown_raises(monkeypatch):
    monkeypatch.setenv("LAB_RUNNER", "bogus")
    import pytest

    with pytest.raises(ValueError):
        rn.get_runner()


# ---------------------------------------------------------------- claude argv


def test_claude_argv_shape():
    cmd = rn.claude_argv(
        "do X",
        model="claude-opus-4-8",
        resume="sess-1",
        allowed_tools=["Bash(uv:*)"],
        max_turns=42,
        permission_mode="acceptEdits",
    )
    assert cmd[:3] == ["claude", "-p", "do X"]
    assert "--output-format" in cmd and cmd[cmd.index("--output-format") + 1] == "json"
    assert cmd[cmd.index("--model") + 1] == "claude-opus-4-8"
    assert cmd[cmd.index("--resume") + 1] == "sess-1"
    assert cmd[cmd.index("--max-turns") + 1] == "42"
    assert cmd[cmd.index("--allowedTools") + 1] == "Bash(uv:*)"


# ---------------------------------------------------------------- sandbox security


def test_curate_env_drops_secret_and_unlisted():
    env = {
        ENV_SECRET: "topsecret",
        "ANTHROPIC_API_KEY": "k",
        "AWS_SECRET_ACCESS_KEY": "nope",
        "LANG": "en_US.UTF-8",
    }
    out = sb.curate_env(env)
    assert ENV_SECRET not in out
    assert "AWS_SECRET_ACCESS_KEY" not in out  # not in allowlist
    assert out == {"ANTHROPIC_API_KEY": "k", "LANG": "en_US.UTF-8"}


def test_build_docker_argv_excludes_secret_even_if_passed():
    # Defense in depth: even if the secret somehow reaches the builder, it must not
    # land in the argv (curate_env already drops it; this guards the builder too).
    claude_cmd = rn.claude_argv(
        "go",
        model=None,
        resume=None,
        allowed_tools=None,
        max_turns=100,
        permission_mode="acceptEdits",
    )
    argv = sb.build_docker_argv(
        image="lab-agent:latest",
        network="lab-egress",
        workspace=Path("/repo"),
        claude_cmd=claude_cmd,
        env=sb.curate_env({ENV_SECRET: "topsecret", "ANTHROPIC_API_KEY": "k"}),
        uid_gid="1000:1000",
    )
    flat = " ".join(argv)
    assert "topsecret" not in flat
    assert ENV_SECRET not in flat


def test_build_docker_argv_hardening_and_mount():
    claude_cmd = ["claude", "-p", "go", "--output-format", "json"]
    argv = sb.build_docker_argv(
        image="img",
        network="lab-egress",
        workspace=Path("/repo"),
        claude_cmd=claude_cmd,
        env={"ANTHROPIC_API_KEY": "k"},
        uid_gid="1000:1000",
    )
    # least privilege
    assert argv[:2] == ["docker", "run"]
    assert "--cap-drop" in argv and argv[argv.index("--cap-drop") + 1] == "ALL"
    assert ["--security-opt", "no-new-privileges"] == argv[
        argv.index("--security-opt") : argv.index("--security-opt") + 2
    ]
    assert "--read-only" in argv
    assert argv[argv.index("--user") + 1] == "1000:1000"
    assert argv[argv.index("--network") + 1] == "lab-egress"
    assert "--pids-limit" in argv and "--memory" in argv
    # only the repo is mounted, workdir is the mount
    assert "-v" in argv and argv[argv.index("-v") + 1] == "/repo:/workspace:rw"
    assert argv[argv.index("-w") + 1] == "/workspace"
    # agent-facing command is the claude argv, appended last
    assert argv[-len(claude_cmd) :] == claude_cmd
    assert "img" in argv


def test_build_docker_argv_skips_user_when_none():
    argv = sb.build_docker_argv(
        image="img",
        network="none",
        workspace=Path("/r"),
        claude_cmd=["claude"],
        env={},
        uid_gid=None,
    )
    assert "--user" not in argv
