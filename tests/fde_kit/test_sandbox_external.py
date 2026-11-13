"""T20 — sandbox + external instance: the kit is mounted read-only at /kit (design ADR-15,
supersedes ADR-10; spec INV-1, BHV-3 `sandbox_required`). Argv only: a `docker` shim on PATH
logs the call, no Docker needed. Kit mode stays on cwd-relative paths."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ENGINE = REPO / "lab" / "engine"
ORCH = ENGINE / "orchestrate.py"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).parent))

import sandbox_runner  # noqa: E402
from test_eval_2_run_preflight import (  # noqa: E402
    JUSTFILE,
    SPEC,
    TASKS,
    _git,
    _make_instance,
    _make_kit,
)

DOCKER_SHIM = """#!/usr/bin/env bash
# One argv element per line, a marker between calls.
{ printf '%s\\n' "--- call"; printf '%s\\n' "$@"; } >> "$LAB_ROOT/.shim/docker.log"
OUT="STATUS: done" python3 -c 'import json, os; print(json.dumps({"type": "result", "result": os.environ["OUT"], "session_id": "s", "total_cost_usd": 0.0}))'
"""


def _docker_calls(kit: Path) -> list[list[str]]:
    p = kit / ".shim" / "docker.log"
    if not p.exists():
        return []
    calls: list[list[str]] = []
    for line in p.read_text().splitlines():
        if line == "--- call":
            calls.append([])
        else:
            calls[-1].append(line)
    return calls


def _mounts(argv: list[str]) -> list[str]:
    return [argv[i + 1] for i, a in enumerate(argv[:-1]) if a == "-v"]


def _run_sandboxed(kit: Path, *flags: str):
    shim = kit / "bin" / "docker"
    shim.write_text(DOCKER_SHIM)
    shim.chmod(0o755)
    env = {
        **os.environ,
        "LAB_ROOT": str(kit),
        "LAB_NO_NOTIFY": "1",
        "LAB_TASK_TIMEOUT": "60",
        "LAB_APPROVAL_SECRET": "s",
        "LAB_RUNNER": "sandbox",
        "PATH": f"{kit / 'bin'}:{os.environ['PATH']}",
    }
    env.pop("LAB_PROJECT_ROOT", None)
    return subprocess.run(
        [sys.executable, str(ORCH), "work/feat", *flags],
        cwd=kit,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _engine_eval(code: str, **env_extra: str) -> subprocess.CompletedProcess:
    """Run `code` in a fresh interpreter with orchestrate imported (module globals are
    resolved at import from the env, so no in-process reload)."""
    env = {**os.environ, **env_extra}
    env["PYTHONPATH"] = str(ENGINE) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-c", "import orchestrate as o\n" + code],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


# ---- runner level: build_docker_argv ----------------------------------------------


def _docker_argv(**kw):
    base = dict(
        image="img",
        network="net",
        workspace=Path("/host/inst"),
        claude_cmd=["claude", "-p", "x"],
        env={},
        uid_gid="1000:1000",
    )
    return sandbox_runner.build_docker_argv(**{**base, **kw})


def test_docker_argv_external_mounts_instance_rw_and_kit_ro():
    argv = _docker_argv(kit=Path("/host/kit"))
    assert _mounts(argv) == ["/host/inst:/workspace:rw", "/host/kit:/kit:ro"]
    assert argv[argv.index("-w") + 1] == "/workspace"


def test_docker_argv_kit_mode_is_a_single_workspace_mount():
    argv = _docker_argv()
    assert _mounts(argv) == ["/host/inst:/workspace:rw"]
    assert "/kit" not in " ".join(argv)


def test_docker_argv_kit_mount_is_never_writable():
    argv = _docker_argv(kit=Path("/host/kit"))
    kit_mounts = [m for m in _mounts(argv) if m.split(":")[1] == "/kit"]
    assert len(kit_mounts) == 1 and kit_mounts[0].endswith(":/kit:ro")


def test_runner_passes_kit_mount_and_add_dirs_to_docker(monkeypatch, tmp_path):
    seen: dict = {}

    def fake_run(argv, cwd, env, timeout):
        seen["argv"] = argv
        return 0, '{"result": "ok"}', ""

    monkeypatch.setattr(sandbox_runner, "run_tracked", fake_run)
    r = sandbox_runner.SandboxedClaudeRunner().run(
        "p",
        cwd=tmp_path / "inst",
        add_dirs=["/kit"],
        plugin_dir="/kit/lab/plugin",
        settings="/kit/lab/engine/run_settings.json",
        kit_mount=tmp_path / "kit",
    )
    assert r.ok
    argv = seen["argv"]
    assert f"{tmp_path / 'kit'}:/kit:ro" in _mounts(argv)
    assert argv[argv.index("--add-dir") + 1] == "/kit"
    assert argv[argv.index("--plugin-dir") + 1] == "/kit/lab/plugin"


# ---- engine level: argv carries /kit paths, no host path ---------------------------


@pytest.fixture()
def world(tmp_path):
    return _make_kit(tmp_path / "kit"), _make_instance(tmp_path / "inst")


def test_external_sandbox_run_mounts_kit_ro_and_uses_kit_paths(world):
    k, i = world
    r = _run_sandboxed(k, "--project", str(i))
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _docker_calls(k)
    assert calls, "no docker call recorded"
    for argv in calls:
        assert _mounts(argv) == [f"{i}:/workspace:rw", f"{k}:/kit:ro"]
        assert argv[argv.index("--plugin-dir") + 1] == "/kit/lab/plugin"
        assert argv[argv.index("--settings") + 1] == "/kit/lab/engine/run_settings.json"
        assert "/kit" in [argv[j + 1] for j, a in enumerate(argv) if a == "--add-dir"]
        # No host path anywhere but the two bind-mount sources.
        rest = [a for j, a in enumerate(argv) if not (j and argv[j - 1] == "-v")]
        leaks = [a for a in rest if str(k) in a or str(i) in a]
        assert leaks == []


def test_external_sandbox_preflight_no_longer_refuses(world):
    k, i = world
    r = _run_sandboxed(k, "--project", str(i), "--dry-run")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "not supported before iteration 2" not in r.stdout + r.stderr


def test_kit_mode_sandbox_argv_unchanged(tmp_path):
    k = _make_kit(tmp_path / "kit")
    (k / "work" / "feat").mkdir(parents=True)
    (k / "work" / "feat" / "spec.md").write_text(SPEC)
    (k / "work" / "feat" / "tasks.md").write_text(TASKS)
    (k / "justfile").write_text(JUSTFILE)
    _git(k, "init", "-q")
    _git(k, "config", "user.email", "t@lab")
    _git(k, "config", "user.name", "t")
    _git(k, "add", "-A")
    _git(k, "commit", "-qm", "init")
    r = _run_sandboxed(k)
    assert r.returncode == 0, r.stdout + r.stderr
    for argv in _docker_calls(k):
        assert _mounts(argv) == [f"{k}:/workspace:rw"]
        assert argv[argv.index("--plugin-dir") + 1] == "lab/plugin"
        assert argv[argv.index("--settings") + 1] == "lab/engine/run_settings.json"
        assert "--add-dir" not in argv


# ---- engine level: add_dirs translation --------------------------------------------


def test_add_dirs_inside_kit_are_translated_and_others_refused(tmp_path):
    kit_dir, inst = tmp_path / "kit", tmp_path / "inst"
    (kit_dir / "lab").mkdir(parents=True)
    inst.mkdir()
    env = dict(LAB_ROOT=str(kit_dir), LAB_PROJECT_ROOT=str(inst), LAB_RUNNER="sandbox")
    ok = _engine_eval(
        f"print(o.translate_add_dirs([{str(kit_dir)!r}, {str(kit_dir / 'lab')!r}]))",
        **env,
    )
    assert ok.returncode == 0, ok.stderr
    assert ok.stdout.strip().splitlines()[-1] == "['/kit', '/kit/lab']"
    bad = _engine_eval(
        f"o.translate_add_dirs([{str(tmp_path / 'elsewhere')!r}])", **env
    )
    assert bad.returncode != 0
    assert "elsewhere" in bad.stderr


def test_guardrail_options_host_paths_outside_sandbox(tmp_path):
    """External instance on the host runner: absolute kit paths, as before."""
    kit_dir, inst = tmp_path / "kit", tmp_path / "inst"
    (kit_dir / "lab" / "plugin" / "rules").mkdir(parents=True)
    (kit_dir / "lab" / "plugin" / "rules" / "hard-rules.md").write_text("R")
    inst.mkdir()
    r = _engine_eval(
        "g = o.guardrail_options(); print(g['plugin_dir']); print(g['settings'])",
        LAB_ROOT=str(kit_dir),
        LAB_PROJECT_ROOT=str(inst),
        LAB_RUNNER="",
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().splitlines()[-2:] == [
        f"{kit_dir}/lab/plugin",
        f"{kit_dir}/lab/engine/run_settings.json",
    ]
