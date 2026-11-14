"""Guard: live files name only the models of the registry (Owner decision 2026-11-13).

The registry (`lab/models/registry.toml`) is the source of truth. Any Claude model id written
in a live file (code, config, tests, docs, agents) must be one of its `[[model]]` ids, so an
older generation cannot linger after it is removed. Dated history is exempt: scorecards,
feature folders under `work/` (specs, plans, run logs, review reports), `progress.md` and the
session history moved out of it, `docs/history/`.
"""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_ID = re.compile(r"\bclaude-(?:opus|sonnet|haiku|fable)-\d+(?:-\d+)*\b")
HISTORY = ("lab/models/scorecards/", "work/", "progress.md", "docs/history/")


def _registry_ids() -> set[str]:
    data = tomllib.loads(
        (ROOT / "lab/models/registry.toml").read_text(encoding="utf-8")
    )
    return {m["id"] for m in data.get("model", [])}


def _live_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    return [f for f in out if not f.startswith(HISTORY) and not f.endswith(".lock")]


def unknown_model_ids(root: Path, files: list[str], known: set[str]) -> list[str]:
    hits = []
    for rel in files:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            hits += [
                f"{rel}:{n}: {mid}"
                for mid in MODEL_ID.findall(line)
                if mid not in known
            ]
    return hits


def test_registry_holds_only_the_claude_5_generation():
    ids = _registry_ids()
    assert ids, "empty registry"
    generation = {i: int(i.split("-")[2]) for i in ids}
    old = sorted(i for i, major in generation.items() if major < 5)
    assert not old, f"older-generation models still in the registry: {old}"


def test_live_files_name_only_registry_models():
    hits = unknown_model_ids(ROOT, _live_files(), _registry_ids())
    assert not hits, "model ids not in the registry:\n" + "\n".join(hits)


def test_guard_catches_a_leftover(tmp_path):
    old = (
        "claude-opus-" + "4-8"
    )  # assembled at run time: this file must pass its own guard
    (tmp_path / "doc.md").write_text(
        f"use {old} here\nand claude-opus-5-5 there\n", encoding="utf-8"
    )
    hits = unknown_model_ids(tmp_path, ["doc.md"], {"claude-opus-5-5"})
    assert hits == [f"doc.md:1: {old}"]
