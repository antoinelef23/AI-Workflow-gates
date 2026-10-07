#!/usr/bin/env python3
"""Run report — aggregates `.runs/journal.jsonl` across features into the numbers
the whitepaper's quality flywheel needs (work/sdlc-rework BHV-1): first-pass
success rate, mean attempts, cost per role and per model, and verify/eval failure
clusters. Read-only (INV-1): this tool never mutates anything; it makes the
registry arbitration ("changed only on quantified proof") a one-command check.

Usage:
    python3 lab/engine/run_report.py                    # every work/**/ with a journal
    python3 lab/engine/run_report.py work/my-feature    # one feature
    python3 lab/engine/run_report.py --json             # machine-readable
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from journal_io import read_events


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def discover_features(root: Path) -> list[Path]:
    """Every feature dir under work/ that has a journal (handles work/<domain>/<feature>)."""
    work = root / "work"
    if not work.is_dir():
        return []
    return sorted(p.parent.parent for p in work.rglob(".runs/journal.jsonl"))


def summarize(events: list[dict]) -> dict:
    """Fold one feature's journal into report numbers (spec EX-1)."""
    attempts: dict[str, list[dict]] = {}
    done: dict[str, int] = {}
    failed: list[str] = []
    blocked: list[str] = []
    cost_task = cost_review = 0.0
    models: dict[str, dict] = {}
    fail_clusters: dict[str, Counter] = {
        "verify_fail": Counter(),
        "eval_fail": Counter(),
    }

    for ev in events:
        kind = ev.get("event")
        tid = str(ev.get("id", ""))
        if kind == "task_attempt":
            attempts.setdefault(tid, []).append(ev)
            cost_task += ev.get("cost_usd") or 0.0
            m = str(ev.get("model") or "cli-default")
            slot = models.setdefault(m, {"attempts": 0, "cost_usd": 0.0})
            slot["attempts"] += 1
            slot["cost_usd"] += ev.get("cost_usd") or 0.0
        elif kind == "task_done":
            done[tid] = int(ev.get("attempts") or len(attempts.get(tid, [])) or 1)
        elif kind == "task_failed":
            failed.append(tid)
        elif kind == "task_blocked":
            blocked.append(tid)
        elif kind == "review":
            cost_review += ev.get("cost_usd") or 0.0
            m = str(ev.get("model") or "cli-default")
            slot = models.setdefault(m, {"attempts": 0, "cost_usd": 0.0})
            slot["attempts"] += 1
            slot["cost_usd"] += ev.get("cost_usd") or 0.0
        elif kind in fail_clusters:
            fail_clusters[kind][tid] += 1

    n_done = len(done)
    first_pass = sum(1 for a in done.values() if a == 1)
    return {
        "tasks_done": n_done,
        "tasks_failed": len(set(failed)),
        "tasks_blocked": len(set(blocked)),
        "first_pass_rate": round(first_pass / n_done, 4) if n_done else None,
        "mean_attempts": round(sum(done.values()) / n_done, 4) if n_done else None,
        "cost_usd": round(cost_task + cost_review, 4),
        "cost_task_usd": round(cost_task, 4),
        "cost_review_usd": round(cost_review, 4),
        "models": {
            m: {"attempts": s["attempts"], "cost_usd": round(s["cost_usd"], 4)}
            for m, s in sorted(models.items())
        },
        "failures": {k: dict(c.most_common()) for k, c in fail_clusters.items()},
    }


def _merge(totals: dict, s: dict) -> None:
    for k in (
        "tasks_done",
        "tasks_failed",
        "tasks_blocked",
        "cost_usd",
        "cost_task_usd",
        "cost_review_usd",
    ):
        totals[k] = round(totals.get(k, 0) + s[k], 4)
    for m, slot in s["models"].items():
        t = totals.setdefault("models", {}).setdefault(
            m, {"attempts": 0, "cost_usd": 0.0}
        )
        t["attempts"] += slot["attempts"]
        t["cost_usd"] = round(t["cost_usd"] + slot["cost_usd"], 4)


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def render_text(reports: dict[str, dict]) -> str:
    lines = []
    for name, s in reports.items():
        lines.append(f"── {name}")
        lines.append(
            f"   tasks: {s['tasks_done']} done / {s['tasks_failed']} failed / {s['tasks_blocked']} blocked"
            f" · first-pass: {_fmt(s['first_pass_rate'])} · mean attempts: {_fmt(s['mean_attempts'])}"
        )
        lines.append(
            f"   cost: ${s['cost_usd']:.2f} (tasks ${s['cost_task_usd']:.2f} / reviews ${s['cost_review_usd']:.2f})"
        )
        for m, slot in s["models"].items():
            lines.append(
                f"     · {m}: {slot['attempts']} attempt(s), ${slot['cost_usd']:.2f}"
            )
        clusters = {k: v for k, v in s["failures"].items() if v}
        for kind, per_task in clusters.items():
            top = ", ".join(f"{t}×{n}" for t, n in list(per_task.items())[:5])
            lines.append(f"   {kind}: {top}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Aggregate run telemetry across features")
    ap.add_argument(
        "features", nargs="*", help="feature dirs (default: discover under work/)"
    )
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument(
        "--root", type=Path, default=None, help="repo root override (tests)"
    )
    args = ap.parse_args(argv)

    root = args.root or _repo_root()
    feats = [root / f if not Path(f).is_absolute() else Path(f) for f in args.features]
    if not feats:
        feats = discover_features(root)

    reports: dict[str, dict] = {}
    for f in feats:
        events = read_events(f)
        if not events and not args.features:
            continue  # discovery mode: skip empty
        reports[str(f.relative_to(root) if f.is_relative_to(root) else f)] = summarize(
            events
        )

    if not reports:
        print("[report] no journal found — nothing to report (run a feature first)")
        return 0

    out: dict = {"features": reports}
    if len(reports) > 1:
        totals: dict = {"models": {}}
        d = a = 0
        for s in reports.values():
            _merge(totals, s)
            if s["tasks_done"]:
                d += s["tasks_done"]
                a += round(s["mean_attempts"] * s["tasks_done"])
        totals["mean_attempts"] = round(a / d, 4) if d else None
        fp = [s for s in reports.values() if s["first_pass_rate"] is not None]
        totals["first_pass_rate"] = (
            round(sum(s["first_pass_rate"] * s["tasks_done"] for s in fp) / d, 4)
            if d
            else None
        )
        totals["failures"] = {}
        out["global"] = totals

    if args.as_json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(render_text(reports))
        if "global" in out:
            g = dict(out["global"])
            g.setdefault("tasks_failed", 0)
            g.setdefault("tasks_blocked", 0)
            print("── global")
            print(
                f"   tasks: {g['tasks_done']} done / {g['tasks_failed']} failed / {g['tasks_blocked']} blocked"
                f" · first-pass: {_fmt(g['first_pass_rate'])} · mean attempts: {_fmt(g['mean_attempts'])}"
            )
            print(f"   cost: ${g['cost_usd']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
