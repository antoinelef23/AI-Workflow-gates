"""Lab model registry — loader for lab/models/registry.toml.

Data-driven source of truth: adding a model = one [[model]] entry, no code.
Imported by lab/engine/orchestrate.py (production assignment) and lab/engine/eval_models.py
(evaluation campaign). See lab/models/EVOLUTION.md for the re-evaluation loop.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path


@dataclass
class Model:
    id: str
    label: str = ""
    family: str = "claude"
    tier: str = ""
    released: str = ""
    roles: list[str] = field(default_factory=list)
    context_profile: str = "base"


@dataclass
class Registry:
    models: list[Model] = field(default_factory=list)
    role_defaults: dict[str, str] = field(default_factory=dict)
    root: Path | None = None

    def by_id(self, mid: str) -> Model | None:
        return next((m for m in self.models if m.id == mid), None)

    def eligible(self, role: str) -> list[Model]:
        return [m for m in self.models if role in m.roles]

    def role_default(self, role: str) -> str | None:
        return self.role_defaults.get(role)

    def profile_text(self, model_id: str | None) -> str:
        """Extra context injected for this model (empty for 'base')."""
        m = self.by_id(model_id) if model_id else None
        if not m or m.context_profile in ("", "base") or not self.root:
            return ""
        p = self.root / "lab" / "models" / "profiles" / f"{m.context_profile}.md"
        return ("\n\n" + p.read_text(encoding="utf-8")) if p.exists() else ""


def load_registry(root: Path | str) -> Registry:
    """Load the registry; returns an empty registry if the file is missing
    (test sandbox, repo without lab/models/ → the orchestrator falls back to the CLI default)."""
    root = Path(root)
    path = root / "lab" / "models" / "registry.toml"
    if not path.exists():
        return Registry(root=root)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    keys = {f.name for f in fields(Model)}
    models = [
        Model(**{k: v for k, v in entry.items() if k in keys})
        for entry in data.get("model", [])
    ]
    return Registry(models=models, role_defaults=dict(data.get("roles", {})), root=root)


def resolve_model(role: str, task_model: str | None, registry: Registry) -> str | None:
    """Precedence: task override (`**model :**`) > role default (registry) > None (CLI default)."""
    return task_model or registry.role_default(role)
