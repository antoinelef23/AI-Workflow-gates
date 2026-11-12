"""T3 — EVAL-2: plugin scaffold, guard + session hooks, run settings
(spec BHV-2, BHV-2b, INV-1, EX-5; design ADR-1..4, §5). No live session."""

from __future__ import annotations

import json
import os
import subprocess
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "lab" / "plugin"
HOOKS = PLUGIN / "hooks"

pytestmark = pytest.mark.eval


def _guard(file_path: str, cwd: Path) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": file_path}})
    return subprocess.run(
        ["bash", str(HOOKS / "guard_paths.sh")],
        input=payload,
        capture_output=True,
        text=True,
        cwd=cwd,
        env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(PLUGIN)},
    )


def test_eval_2_guard_denies_approvals(tmp_path):
    assert _guard(".approvals/CP-1", tmp_path).returncode == 2
    assert _guard(str(tmp_path / "work/f/.approvals/CP-1"), tmp_path).returncode == 2


def test_eval_2_guard_denies_runs(tmp_path):
    assert _guard(".runs/state.json", tmp_path).returncode == 2
    assert _guard(str(tmp_path / "work/f/.runs/state.json"), tmp_path).returncode == 2


def test_eval_2_guard_allows_ordinary_path(tmp_path):
    assert _guard("src/app.py", tmp_path).returncode == 0
    assert _guard(str(tmp_path / "work/f/spec.md"), tmp_path).returncode == 0
    assert _guard("docs/approvals-notes.md", tmp_path).returncode == 0


def test_eval_2_hooks_json_declares_existing_scripts():
    hooks = json.loads((HOOKS / "hooks.json").read_text())["hooks"]
    # T15 (Owner lane) wired the moved scripts; T11 asserts their entries in detail.
    assert set(hooks) == {
        "PreToolUse",
        "SessionStart",
        "PostToolUse",
        "Stop",
        "SubagentStop",
    }
    pre = hooks["PreToolUse"][0]
    assert pre["matcher"] == "Edit|Write|MultiEdit|NotebookEdit"
    assert pre["hooks"][0]["onFailure"] == "block"
    marker = '"${CLAUDE_PLUGIN_ROOT}"/hooks/'
    for entry in (e for evs in hooks.values() for e in evs):
        for h in entry["hooks"]:
            cmd = h["command"]
            assert marker in cmd
            script = cmd.split(marker)[1].strip('" ')
            assert (HOOKS / script).is_file()


def test_eval_2_session_start_prints_hard_rules_without_instance_files(tmp_path):
    assert not (tmp_path / ".claude").exists() and not (tmp_path / "CLAUDE.md").exists()
    r = subprocess.run(
        ["bash", str(HOOKS / "session_start.sh")],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(PLUGIN)},
    )
    assert r.returncode == 0
    assert "## Hard rules" in r.stdout
    assert "Eval gate" in r.stdout
    assert r.stdout.strip() == (PLUGIN / "rules" / "hard-rules.md").read_text().strip()


def test_eval_2_rules_file_has_the_three_sections():
    text = (PLUGIN / "rules" / "hard-rules.md").read_text()
    for heading in ("## The 3 artifacts", "## Hard rules", "## Vocabulary"):
        assert heading in text
    assert "## Conventions" not in text


def test_eval_2_run_settings_exactly_two_denies_no_hooks():
    s = json.loads((REPO / "lab" / "engine" / "run_settings.json").read_text())
    assert s == {
        "permissions": {"deny": ["Edit(**/.approvals/**)", "Edit(**/.runs/**)"]}
    }
    assert "hooks" not in s


def test_eval_2_version_coherence():
    kit = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["version"]
    plugin = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    assert plugin["name"] == "fde-kit"
    entries = [p for p in market["plugins"] if p["name"] == "fde-kit"]
    assert len(entries) == 1 and len(market["plugins"]) == 1
    assert entries[0]["source"] == "./lab/plugin"
    assert plugin["version"] == kit
    assert entries[0].get("version", kit) == kit


def test_eval_2_hooks_json_stop_subagentstop_posttooluse_entries():
    """T11 — ADR-4: the moved scripts are wired through ${CLAUDE_PLUGIN_ROOT}."""
    hooks = json.loads((HOOKS / "hooks.json").read_text())["hooks"]
    marker = '"${CLAUDE_PLUGIN_ROOT}"/hooks/'

    def commands(event):
        return [h["command"] for e in hooks[event] for h in e["hooks"]]

    assert commands("Stop") == [f"bash {marker}eval_gate.sh"]
    assert commands("SubagentStop") == [f"bash {marker}eval_gate.sh"]
    assert commands("PostToolUse") == [f"bash {marker}post_edit.sh"]
    assert hooks["PostToolUse"][0]["matcher"] == "Edit|Write|MultiEdit"
