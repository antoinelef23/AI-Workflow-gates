"""Run state (ADR-18, §5): git names the delivered tasks, `state.json` v2 carries the rest.

Pure except for one git read (`planlint.committed_task_ids`). Deliberately does NOT import
`orchestrate` — orchestrate imports this module (T25).
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import planlint

SCHEMA_VERSION = 2


@dataclass
class RunState:
    tasks: dict[str, str] = field(default_factory=dict)
    reopened: list[str] = field(default_factory=list)
    rejections: dict[str, int] = field(default_factory=dict)
    routes: dict[str, dict[str, int]] = field(default_factory=dict)

    def is_done(self, node_id: str) -> bool:
        return self.tasks.get(node_id) == "done"

    def to_json(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "tasks": self.tasks,
            "reopened": self.reopened,
            "rejections": self.rejections,
            "routes": self.routes,
        }


def _read(path: Path) -> RunState:
    """state.json → RunState; missing or unreadable ⇒ empty (git alone speaks)."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return RunState()
    if not isinstance(raw, dict):
        return RunState()
    if "schema_version" not in raw:  # old flat {id: status}
        return RunState(tasks={str(k): str(v) for k, v in raw.items()})
    try:
        return RunState(
            tasks={str(k): str(v) for k, v in dict(raw.get("tasks") or {}).items()},
            reopened=[str(x) for x in (raw.get("reopened") or [])],
            rejections={
                str(k): int(v) for k, v in dict(raw.get("rejections") or {}).items()
            },
            routes={
                str(t): {str(r): int(n) for r, n in dict(m).items()}
                for t, m in dict(raw.get("routes") or {}).items()
            },
        )
    except (TypeError, ValueError):
        return RunState()


def load(feature: Path, project: Path) -> RunState:
    """Effective run state of `feature`: `<feature>/.runs/state.json` merged with git.

    A task is `done` if it has a canonical commit and is not reopened, or if `tasks` says so.
    Checkpoints have no commit: only `tasks` speaks for them."""
    state = _read(feature / ".runs" / "state.json")
    for tid in planlint.committed_task_ids(project, feature):
        if tid not in state.reopened:
            state.tasks[tid] = "done"
    return state


def save(path: Path, state: RunState) -> None:
    """Atomic write (tempfile + os.replace) — no truncation on SIGKILL mid-write."""
    path.parent.mkdir(exist_ok=True, parents=True)
    with tempfile.NamedTemporaryFile(
        mode="w", dir=str(path.parent), delete=False, suffix=".tmp", encoding="utf-8"
    ) as f:
        json.dump(state.to_json(), f, indent=2, ensure_ascii=False)
        tmp = f.name
    try:
        os.replace(tmp, str(path))
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
