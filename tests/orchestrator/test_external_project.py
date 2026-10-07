"""Driving the lab against an EXTERNAL project root (--project / LAB_PROJECT_ROOT).

The engine splits two roots:
  - LAB (a.k.a. ROOT): the framework — engine, model registry, agent definitions.
  - PROJECT: where the build lives — work/<feature>, the code, the evals, the git repo.

PROJECT defaults to LAB, so every other test (which sets only LAB_ROOT) sees
LAB == PROJECT and is unaffected. These tests pin the new, decoupled behaviour.

Resolution is checked in a SUBPROCESS on purpose: importlib.reload of the shared
`orchestrate` module would leave its globals (ROOT) mutated and break the tests that
assert `orchestrate.ROOT == REPO`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ORCH = REPO / "lab" / "engine" / "orchestrate.py"
ENGINE = REPO / "lab" / "engine"
sys.path.insert(0, str(ENGINE))


def _resolve_roots(**env_extra: str) -> tuple[str, str]:
    """Import orchestrate in a fresh interpreter under the given env; return (LAB, PROJECT)."""
    code = "import orchestrate as o; print(o.LAB); print(o.PROJECT)"
    env = {**os.environ, **env_extra}
    env["PYTHONPATH"] = str(ENGINE) + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    lab, project = r.stdout.strip().splitlines()[-2:]
    return lab, project


def test_project_defaults_to_lab_when_unset(tmp_path):
    env = dict(LAB_ROOT=str(tmp_path))
    env.pop("LAB_PROJECT_ROOT", None)
    # Ensure no inherited LAB_PROJECT_ROOT leaks in.
    lab, project = _resolve_roots(LAB_ROOT=str(tmp_path), LAB_PROJECT_ROOT="")
    assert lab == str(tmp_path)
    assert project == str(tmp_path)  # back-compat: PROJECT == LAB


def test_project_env_overrides_lab(tmp_path):
    lab = tmp_path / "lab"
    proj = tmp_path / "proj"
    lab.mkdir()
    proj.mkdir()
    got_lab, got_project = _resolve_roots(LAB_ROOT=str(lab), LAB_PROJECT_ROOT=str(proj))
    assert got_lab == str(lab)  # registry / agent defs still resolve against the lab
    assert got_project == str(proj)  # build target moved to the external project


def test_add_dirs_in_claude_argv():
    import runner

    base = dict(
        model=None,
        resume=None,
        allowed_tools=["Read"],
        max_turns=10,
        permission_mode="acceptEdits",
    )
    with_dir = runner.claude_argv("p", add_dirs=["/some/lab"], **base)
    assert "--add-dir" in with_dir
    assert "/some/lab" in with_dir
    # Default: NO --add-dir, so the in-repo path and every shim-based test keep an
    # byte-identical argv.
    without = runner.claude_argv("p", **base)
    assert "--add-dir" not in without


def test_validate_resolves_feature_under_external_project(tmp_path):
    """--project makes the feature path resolve under PROJECT, not the LAB."""
    lab = tmp_path / "lab"
    proj = tmp_path / "proj"
    lab.mkdir()
    (proj / "work" / "feat").mkdir(parents=True)
    # No tasks.md in the project feature: the orchestrator must fail trying to read it
    # FROM THE PROJECT path — proving resolution moved off the lab repo.
    env = {**os.environ, "LAB_ROOT": str(lab), "LAB_NO_NOTIFY": "1"}
    env.pop("LAB_PROJECT_ROOT", None)
    r = subprocess.run(
        [sys.executable, str(ORCH), "work/feat", "--project", str(proj), "--validate"],
        cwd=str(lab),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode != 0
    assert str(proj) in (r.stdout + r.stderr)
