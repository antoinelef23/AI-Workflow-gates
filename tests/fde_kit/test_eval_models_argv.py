"""T13 — ADR-11: the model-eval harness calls agents exactly like a run (spec BHV-2).

Shim only (LAB_MODEL_SHIM=1): no billed call, never `--live`."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# A shim that logs its argv as one JSON line (the rules text is multi-line).
SHIM = """#!/usr/bin/env python3
import json, os, sys
if sys.argv[1:2] == ["--version"]:
    print("2.1.300 (Claude Code)")
    sys.exit(0)
with open(os.environ["ARGV_LOG"], "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
agent_dir = os.path.join(os.getcwd(), ".agent")
with open(os.environ["ARGV_LOG"] + ".cwd", "a") as f:
    found = sorted(os.listdir(agent_dir)) if os.path.isdir(agent_dir) else []
    f.write(json.dumps(found) + "\\n")
print(json.dumps({"result": "STATUS: done\\nVERDICT: PASS", "total_cost_usd": 0.0}))
"""


def _campaign(tmp_path: Path, layer: str) -> list[list[str]]:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    shim = bindir / "claude"
    shim.write_text(SHIM)
    shim.chmod(0o755)
    log = tmp_path / "argv.jsonl"
    env = {
        **os.environ,
        "LAB_ROOT": str(tmp_path / "root"),
        "LAB_MODEL_SHIM": "1",
        "LAB_TASK_TIMEOUT": "60",
        "ARGV_LOG": str(log),
        "PATH": f"{bindir}:{os.environ['PATH']}",
    }
    r = subprocess.run(
        [
            sys.executable,
            str(REPO / "lab" / "engine" / "eval_models.py"),
            "--layer",
            layer,
            "--models",
            "m1",
            "--stamp",
            "t13",
        ],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    cwd_files = [
        json.loads(line) for line in Path(str(log) + ".cwd").read_text().splitlines()
    ]
    for argv, present in zip(calls, cwd_files, strict=True):
        prompt = argv[argv.index("-p") + 1]
        role = "implementer" if ".agent/implementer.md" in prompt else "reviewer"
        assert present == [f"{role}.md"], (role, present)
    return calls


def _assert_run_options(argv: list[str]) -> None:
    rules = (REPO / "lab/plugin/rules/hard-rules.md").read_text(encoding="utf-8")
    plugin = argv[argv.index("--plugin-dir") + 1]
    assert plugin == str(REPO / "lab" / "plugin")
    assert Path(plugin).is_absolute()
    assert argv[argv.index("--settings") + 1] == str(
        REPO / "lab" / "engine" / "run_settings.json"
    )
    assert argv[argv.index("--append-system-prompt") + 1] == rules
    assert argv[argv.index("--model") + 1] == "m1"
    assert "--allowedTools" in argv
    assert "--bare" not in argv
    # The role file is a COPY in the trial cwd: no --add-dir at all, and no path
    # into the kit in the prompt (its Bash tools could read evals/, the answer keys).
    assert "--add-dir" not in argv
    prompt = argv[argv.index("-p") + 1]
    assert ".agent/implementer.md" in prompt or ".agent/reviewer.md" in prompt
    assert str(REPO) not in prompt


def test_behavioral_trial_argv_carries_run_options(tmp_path: Path) -> None:
    calls = _campaign(tmp_path, "behavioral")
    assert calls
    for argv in calls:
        _assert_run_options(argv)


def test_chain_trial_argv_carries_run_options(tmp_path: Path) -> None:
    calls = _campaign(tmp_path, "chain")
    assert calls
    for argv in calls:
        _assert_run_options(argv)


def test_role_prompts_format_with_prompt_only_and_fixture_ships_role_file() -> None:
    # Covers the scorecard layer's prompt too (no golden task under a temp LAB_ROOT).
    sys.path.insert(0, str(REPO / "lab" / "engine"))
    import eval_models

    for role in ("implementer", "reviewer"):
        text = eval_models.ROLE_PROMPT[role].format(prompt="Do {x}.")
        assert f".agent/{role}.md" in text and "Do {x}." in text
        wd = eval_models.setup_fixture({"spec.md": "s\n"}, role=role)
        shipped = (wd / ".agent" / f"{role}.md").read_text(encoding="utf-8")
        assert shipped == (REPO / "lab/plugin/agents" / f"{role}.md").read_text(
            encoding="utf-8"
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=wd, capture_output=True, text=True
        ).stdout
        assert status == ""  # part of the baseline: the git-status checkers stay exact
