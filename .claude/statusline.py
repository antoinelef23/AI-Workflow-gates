#!/usr/bin/env python3
"""Claude Code status line — surfaces the orchestrator run state.

Claude Code pipes a JSON blob about the session on stdin and renders the first
line we print as the status line. We show the model plus, when an orchestrator
run exists, the live state of the most-recently-touched feature read from
`work/<feature>/.runs/state.json` (a flat {node_id: status} map written by
lab/engine/orchestrate.py): which node is running, progress, and any blocker.

Pure stdlib, read-only, never raises (a status line must not break the session).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# state.json status -> glyph
GLYPH = {
    "running": "▶",
    "done": "✓",
    "failed": "✗",
    "blocked": "⏸",
    "skipped": "⏭",
    "pending": "·",
}
# What to surface first if several nodes are in these states (most urgent wins).
URGENT = ("failed", "blocked", "running")


def _project_dir(data: dict) -> Path:
    ws = data.get("workspace") or {}
    for cand in (
        os.environ.get("CLAUDE_PROJECT_DIR"),
        ws.get("project_dir"),
        ws.get("current_dir"),
        data.get("cwd"),
        os.getcwd(),
    ):
        if cand and Path(cand).is_dir():
            return Path(cand)
    return Path.cwd()


def _latest_run(proj: Path) -> tuple[str, dict] | None:
    # Recursive: handles work/<feature>/ and work/<domain>/<feature>/ alike.
    states = list(proj.glob("work/**/.runs/state.json"))
    if not states:
        return None
    newest = max(states, key=lambda p: p.stat().st_mtime)
    try:
        obj = json.loads(newest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(obj, dict) or not obj:
        return None
    # work/<…>/<feature>/.runs/state.json -> the path under work/ (e.g. "agent/booking")
    feat_dir = newest.parent.parent
    try:
        feature = str(feat_dir.relative_to(proj / "work"))
    except ValueError:
        feature = feat_dir.name
    return feature, obj


def _run_segment(feature: str, st: dict) -> str:
    total = len(st)
    done = sum(1 for v in st.values() if v == "done")
    # urgent node to surface (first failed, then blocked, then running)
    spotlight = ""
    for status in URGENT:
        hit = [nid for nid, v in st.items() if v == status]
        if hit:
            spotlight = f"{GLYPH[status]} {hit[0]} {status}"
            break
    if not spotlight:
        # no running/failed/blocked node: just progress (or completion)
        detail = "✓ all done" if done == total else f"{done}/{total} done"
    else:
        # a node is in the spotlight: append progress unless everything's finished
        detail = spotlight if done == total else f"{spotlight} · {done}/{total}"
    return f"🔬 {feature} · {detail}"


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (ValueError, OSError):
        data = {}

    model = ((data.get("model") or {}).get("display_name")) or "Claude"
    segments = [model]

    run = _latest_run(_project_dir(data))
    if run:
        segments.append(_run_segment(*run))

    print("  ".join(segments))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # a status line must never break the session
        print("Claude")
