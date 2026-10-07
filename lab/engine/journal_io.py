#!/usr/bin/env python3
"""Journal reader — `.runs/journal.jsonl` is the run-telemetry source of truth,
written by orchestrate.journal(). Read-only and tolerant (work/sdlc-rework INV-1,
INV-4): a malformed line is skipped, an absent file yields [] so features that
never ran keep passing every gate. Shared by run_report and trajectory_guard."""

from __future__ import annotations

import json
from pathlib import Path


def journal_path(feature: Path) -> Path:
    return feature / ".runs" / "journal.jsonl"


def read_events(feature: Path) -> list[dict]:
    """All journal events of a feature, in write order. [] if no journal."""
    path = journal_path(feature)
    if not path.is_file():
        return []
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue  # tolerant: telemetry must never brick a tool (INV-4)
        if isinstance(ev, dict):
            events.append(ev)
    return events
