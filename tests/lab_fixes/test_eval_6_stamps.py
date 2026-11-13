"""EVAL-6 — campaign scorecards get dated stamps, never `latest` (BHV-6, INV-5)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SHIM = """#!/usr/bin/env bash
python3 -c 'import json; print(json.dumps({"result":"STATUS: done\\nVERDICT: PASS","total_cost_usd":0.002}))'
"""


@pytest.fixture
def campaign(tmp_path: Path, monkeypatch):
    """Load eval_models against a temp LAB_ROOT with the model shim; inject the date."""
    root = tmp_path / "root"
    (root / "bin").mkdir(parents=True)
    shim = root / "bin" / "claude"
    shim.write_text(SHIM)
    shim.chmod(0o755)
    monkeypatch.setenv("LAB_ROOT", str(root))
    monkeypatch.setenv("LAB_MODEL_SHIM", "1")
    monkeypatch.setenv("LAB_TASK_TIMEOUT", "60")
    monkeypatch.setenv("PATH", f"{root / 'bin'}:{os.environ['PATH']}")
    monkeypatch.syspath_prepend(str(REPO / "lab" / "engine"))
    spec = importlib.util.spec_from_file_location(
        "eval_models_stamps", REPO / "lab" / "engine" / "eval_models.py"
    )
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "eval_models_stamps", mod)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "_today", lambda: "2026-11-13")
    out = root / "lab" / "models" / "scorecards"

    def run(*extra: str) -> int:
        monkeypatch.setattr(sys, "argv", ["eval_models.py", "--models", "m1", *extra])
        return mod.main()

    return run, out


def names(out: Path) -> list[str]:
    return sorted(p.name for p in out.iterdir())


@pytest.mark.eval
def test_eval_6_two_layers_same_day(campaign) -> None:
    run, out = campaign
    assert run("--layer", "behavioral") == 0
    assert run("--layer", "chain") == 0
    assert names(out) == [
        "2026-11-13-behavioral.jsonl",
        "2026-11-13-behavioral.md",
        "2026-11-13-chain.jsonl",
        "2026-11-13-chain.md",
    ]


@pytest.mark.eval
def test_eval_6_same_layer_twice_suffixes(campaign) -> None:
    run, out = campaign
    assert run("--layer", "chain") == 0
    assert run("--layer", "chain") == 0
    assert run("--layer", "chain") == 0
    got = names(out)
    for s in ("2026-11-13-chain", "2026-11-13-chain-2", "2026-11-13-chain-3"):
        assert f"{s}.md" in got and f"{s}.jsonl" in got
    assert not any("latest" in n for n in got)


@pytest.mark.eval
def test_eval_6_explicit_stamp_honored(campaign) -> None:
    run, out = campaign
    assert run("--layer", "chain", "--stamp", "mine") == 0
    assert run("--layer", "chain", "--stamp", "mine") == 0  # given as-is
    assert names(out) == ["mine.jsonl", "mine.md"]
