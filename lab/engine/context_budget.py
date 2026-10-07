#!/usr/bin/env python3
"""Context budget — measures the STATIC context payload per role: the files every
agent call pays for on every turn (CLAUDE.md + role `.md` + non-base context
profile). The static/dynamic boundary is a versioned design decision
(docs/explanation/static-vs-dynamic-context.md); this tool makes its cost visible
so the "add a rule every time the agent misbehaves" ratchet has a counterweight.

Token count is chars/4 (ADR-2: relative budget, no tokenizer dependency).
Soft gate (ADR-4): always measures; FAILS only once the Owner declares
`[context] max_static_tokens` in lab/models/registry.toml.

Usage:  python3 lab/engine/context_budget.py [--root REPO]
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path


def approx_tokens(text: str) -> int:
    return (len(text) + 3) // 4


def static_files(root: Path, role: str, profile: str) -> list[Path]:
    """The files injected on EVERY call for a role. `base` profile = no injection
    (lab/models/profiles/base.md documents itself as doc-only)."""
    files = [root / "CLAUDE.md", root / ".claude" / "agents" / f"{role}.md"]
    if profile and profile != "base":
        files.append(root / "lab" / "models" / "profiles" / f"{profile}.md")
    return [f for f in files if f.is_file()]


def measure(root: Path) -> tuple[dict[str, dict], int | None]:
    reg = tomllib.loads((root / "lab" / "models" / "registry.toml").read_text("utf-8"))
    profiles = {m["id"]: m.get("context_profile", "base") for m in reg.get("model", [])}
    budget = reg.get("context", {}).get("max_static_tokens")

    rows: dict[str, dict] = {}
    for role, model_id in sorted(reg.get("roles", {}).items()):
        files = static_files(root, role, profiles.get(model_id, "base"))
        tokens = sum(approx_tokens(f.read_text("utf-8")) for f in files)
        rows[role] = {
            "model": model_id,
            "files": [str(f.relative_to(root)) for f in files],
            "tokens": tokens,
        }
    return rows, budget


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Static-context payload per role")
    ap.add_argument(
        "--root", type=Path, default=None, help="repo root override (tests)"
    )
    args = ap.parse_args(argv)
    root = args.root or Path(__file__).resolve().parents[2]

    rows, budget = measure(root)
    over: list[str] = []
    for role, r in rows.items():
        mark = ""
        if budget and r["tokens"] > budget:
            mark = f"  ⛔ > {budget}"
            over.append(role)
        print(f"{role:<12} {r['model']:<28} ~{r['tokens']:>6} tokens{mark}")
        for f in r["files"]:
            print(f"{'':<12}   · {f}")
    if budget is None:
        print(
            "[context] no max_static_tokens declared in registry [context] — measuring only"
        )
        return 0
    if over:
        print(f"[context] budget {budget} exceeded by: {', '.join(over)}")
        return 1
    print(f"[context] all roles within budget ({budget})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
