"""T4 — EVAL-2: engine wiring + fail-closed pre-flight (spec BHV-2, BHV-2a, INV-1, INV-7, EX-5;
design ADR-2, ADR-6, ADR-10). Shim `claude`, no live session; the instance has neither
`.claude/` nor CLAUDE.md."""

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

import kit  # noqa: E402

pytestmark = pytest.mark.eval

RULES_SENTINEL = "HARD-RULES-SENTINEL-4242"

SHIM = """#!/usr/bin/env bash
if [ "$1" = "--version" ]; then
  echo "${SHIM_CLAUDE_VERSION:-2.1.300} (Claude Code)"
  exit 0
fi
echo "$@" >> "$LAB_ROOT/.shim/argv.log"
OUT="STATUS: done" python3 -c 'import json, os; print(json.dumps({"type": "result", "result": os.environ["OUT"], "session_id": "s", "total_cost_usd": 0.0}))'
"""

JUSTFILE = "evals:\n    #!/usr/bin/env bash\n    echo ok\n"

SPEC = """---
type: spec
feature: feat
version: 1.0.0
status: validated
---

# Spec — feat

- **INV-1** — The system MUST exist.
- EVAL-1: test eval.
"""

TASKS = """---
type: tasks
feature: feat
status: approved
---

# Tasks — feat

### T1 — Produces a file
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`
"""


def _git(cwd: Path, *a: str) -> None:
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


def _make_kit(root: Path, *, plugin: bool = True) -> Path:
    """A minimal kit tree: shim claude + plugin stub (manifest + rules) + run settings."""
    (root / "bin").mkdir(parents=True)
    (root / ".shim").mkdir()
    shim = root / "bin" / "claude"
    shim.write_text(SHIM)
    shim.chmod(0o755)
    (root / "lab" / "engine").mkdir(parents=True)
    (root / "lab" / "engine" / "run_settings.json").write_text(
        '{"permissions": {"deny": ["Edit(**/.approvals/**)", "Edit(**/.runs/**)"]}}'
    )
    if plugin:
        (root / "lab" / "plugin" / ".claude-plugin").mkdir(parents=True)
        (root / "lab" / "plugin" / ".claude-plugin" / "plugin.json").write_text(
            '{"name": "fde-kit", "version": "0"}'
        )
        (root / "lab" / "plugin" / "rules").mkdir()
        (root / "lab" / "plugin" / "rules" / "hard-rules.md").write_text(
            f"# Rules\n{RULES_SENTINEL}\n"
        )
    return root


def _make_instance(root: Path, pin: str | None = None) -> Path:
    (root / "work" / "feat").mkdir(parents=True)
    (root / "work" / "feat" / "spec.md").write_text(SPEC)
    (root / "work" / "feat" / "tasks.md").write_text(TASKS)
    (root / "justfile").write_text(JUSTFILE)
    (root / ".lab").mkdir()
    (root / ".lab" / "lab.toml").write_text(
        f'schema_version = 1\nkit_version = "{pin or kit.kit_version()}"\nprofile = "squad"\n'
    )
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@lab")
    _git(root, "config", "user.name", "t")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    return root


def _run(kit_dir: Path, *flags: str, cwd: Path | None = None, env_extra=None):
    env = {
        **os.environ,
        "LAB_ROOT": str(kit_dir),
        "LAB_NO_NOTIFY": "1",
        "LAB_TASK_TIMEOUT": "60",
        "LAB_APPROVAL_SECRET": "s",
        "PATH": f"{kit_dir / 'bin'}:{os.environ['PATH']}",
        **(env_extra or {}),
    }
    env.pop("LAB_PROJECT_ROOT", None)
    env.pop("LAB_RUNNER", None)
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(ORCH), "work/feat", *flags],
        cwd=cwd or kit_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _argv_log(kit_dir: Path) -> str:
    p = kit_dir / ".shim" / "argv.log"
    return p.read_text() if p.exists() else ""


@pytest.fixture()
def world(tmp_path):
    k = _make_kit(tmp_path / "kit")
    i = _make_instance(tmp_path / "inst")
    return k, i


def test_eval_2_ex5_argv_carries_kit_settings_plugin_and_rules(world):
    k, i = world
    assert not (i / ".claude").exists() and not (i / "CLAUDE.md").exists()
    r = _run(k, "--project", str(i))
    assert r.returncode == 0, r.stdout + r.stderr
    log = _argv_log(k)
    assert f"--settings {k}/lab/engine/run_settings.json" in log
    assert f"--plugin-dir {k}/lab/plugin" in log
    assert "--append-system-prompt" in log and RULES_SENTINEL in log
    assert "--bare" not in log
    # kit paths come from the KIT root, never from the instance (I-2)
    assert str(i / "lab") not in log


def test_eval_2_ex5_pin_mismatch_names_both_versions(tmp_path):
    k = _make_kit(tmp_path / "kit")
    i = _make_instance(tmp_path / "inst", pin="0.0.0-other")
    r = _run(k, "--project", str(i))
    assert r.returncode == 1
    out = r.stdout + r.stderr
    assert f"plugin {kit.kit_version()} ≠ pinned kit 0.0.0-other" in out
    assert _argv_log(k) == ""  # no agent was launched


def test_eval_2_pin_mismatch_also_refuses_dry_run(tmp_path):
    k = _make_kit(tmp_path / "kit")
    i = _make_instance(tmp_path / "inst", pin="0.0.0-other")
    r = _run(k, "--project", str(i), "--dry-run")
    assert r.returncode == 1
    assert "≠ pinned kit" in r.stdout + r.stderr


def test_eval_2_lab_toml_missing_refuses(world):
    k, i = world
    (i / ".lab" / "lab.toml").unlink()
    r = _run(k, "--project", str(i))
    assert r.returncode == 1
    assert "lab.toml" in r.stdout + r.stderr


def test_eval_2_plugin_dir_missing_refuses(tmp_path):
    k = _make_kit(tmp_path / "kit", plugin=False)
    i = _make_instance(tmp_path / "inst")
    r = _run(k, "--project", str(i))
    assert r.returncode == 1
    assert "lab/plugin" in r.stdout + r.stderr
    assert _argv_log(k) == ""


def test_eval_2_plugin_dir_missing_refuses_in_kit_mode(tmp_path):
    k = _make_kit(tmp_path / "kit", plugin=False)
    (k / "work" / "feat").mkdir(parents=True)
    (k / "work" / "feat" / "spec.md").write_text(SPEC)
    (k / "work" / "feat" / "tasks.md").write_text(TASKS)
    (k / "justfile").write_text(JUSTFILE)
    r = _run(k)
    assert r.returncode == 1
    assert "lab/plugin" in r.stdout + r.stderr


def test_eval_2_cli_too_old_refuses(world):
    k, i = world
    r = _run(k, "--project", str(i), env_extra={"SHIM_CLAUDE_VERSION": "2.1.294"})
    assert r.returncode == 1
    out = r.stdout + r.stderr
    assert "2.1.294" in out and "2.1.295" in out
    assert _argv_log(k) == ""


def test_eval_2_cli_min_version_accepted(world):
    k, i = world
    r = _run(k, "--project", str(i), env_extra={"SHIM_CLAUDE_VERSION": "2.1.295"})
    assert r.returncode == 0, r.stdout + r.stderr


def test_eval_2_sandbox_with_project_refuses(world):
    k, i = world
    r = _run(k, "--project", str(i), env_extra={"LAB_RUNNER": "sandbox"})
    assert r.returncode == 1
    assert (
        "sandbox + external instance not supported before iteration 2"
        in r.stdout + r.stderr
    )


def test_eval_2_kit_mode_uses_relative_paths(tmp_path):
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
    r = _run(k)
    assert r.returncode == 0, r.stdout + r.stderr
    log = _argv_log(k)
    assert "--plugin-dir lab/plugin " in log
    assert "--settings lab/engine/run_settings.json " in log
    assert RULES_SENTINEL in log
    assert str(k / "lab") not in log  # no absolute kit path in kit mode


def test_eval_2_kit_mode_does_not_need_a_lab_toml(tmp_path):
    k = _make_kit(tmp_path / "kit")
    (k / "work" / "feat").mkdir(parents=True)
    (k / "work" / "feat" / "spec.md").write_text(SPEC)
    (k / "work" / "feat" / "tasks.md").write_text(TASKS)
    (k / "justfile").write_text(JUSTFILE)
    r = _run(k, "--dry-run")
    assert r.returncode == 0, r.stdout + r.stderr


def test_eval_2_validate_skips_preflight(tmp_path):
    """--validate (pre-commit, CI) must pass without a claude CLI, plugin or pin."""
    k = _make_kit(tmp_path / "kit", plugin=False)
    (k / "bin" / "claude").unlink()
    i = _make_instance(tmp_path / "inst", pin="0.0.0-other")
    r = _run(
        k,
        "--project",
        str(i),
        "--validate",
        env_extra={"PATH": "/usr/bin:/bin"},
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_eval_2_agent_file_resolution_prefers_plugin(tmp_path):
    k = _make_kit(tmp_path / "kit")
    code = (
        "import orchestrate as o; "
        "print(o.agent_file('implementer')); print(o.agent_file('reviewer'))"
    )
    env = {**os.environ, "LAB_ROOT": str(k), "PYTHONPATH": str(ENGINE)}
    env.pop("LAB_PROJECT_ROOT", None)

    def paths():
        r = subprocess.run(
            [sys.executable, "-c", code], env=env, capture_output=True, text=True
        )
        assert r.returncode == 0, r.stderr
        return r.stdout.split()

    assert paths() == [
        f"{k}/.claude/agents/implementer.md",
        f"{k}/.claude/agents/reviewer.md",
    ]
    (k / "lab" / "plugin" / "agents").mkdir()
    (k / "lab" / "plugin" / "agents" / "implementer.md").write_text("x")
    assert paths() == [
        f"{k}/lab/plugin/agents/implementer.md",
        f"{k}/.claude/agents/reviewer.md",
    ]


def test_eval_2_claude_argv_unchanged_without_options_and_never_bare():
    import runner

    base = dict(
        model=None,
        resume=None,
        allowed_tools=["Read"],
        max_turns=10,
        permission_mode="acceptEdits",
    )
    plain = runner.claude_argv("p", **base)
    assert not {"--plugin-dir", "--settings", "--append-system-prompt"} & set(plain)
    full = runner.claude_argv(
        "p",
        plugin_dir="lab/plugin",
        settings="lab/engine/run_settings.json",
        append_system_prompt="RULES",
        **base,
    )
    assert full[: len(plain)] == plain
    assert full[len(plain) :] == [
        "--plugin-dir",
        "lab/plugin",
        "--settings",
        "lab/engine/run_settings.json",
        "--append-system-prompt",
        "RULES",
    ]
    assert "--bare" not in full
