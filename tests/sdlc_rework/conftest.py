"""SDLC-rework test harness (work/sdlc-rework): the new engine modules import
each other flat (`from plan import …`), like the rest of lab/engine — so the
engine dir goes on sys.path, same pattern as tests/orchestrator."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "lab" / "engine"))
