#!/usr/bin/env python3
"""Trajectory guard — output evals check WHAT a task produced; this guard checks
HOW it got there (work/sdlc-rework BHV-2, whitepaper: trajectory evaluation).
Two mechanical FAIL conditions, from the two trajectory sources the lab persists
(ADR-1: journal + git history, never session transcripts):

  BHV-2a  a `task_done` with no prior successful `task_attempt` — a forged or
          corrupt journal must never read as a healthy run;
  BHV-2b  an `[auto]` task commit touching files outside the node's
          `files_touched` ∪ the feature dir — scope drift that slipped past
          scoped_commit (same paths_overlap semantics).

Retry-loop smell (≥3 attempts, or a task_failed) is a WARN, rc 0 (BHV-2c).
Read-only (INV-1); no journal ⇒ nothing to check, rc 0 (INV-4).

Usage:  python3 lab/engine/trajectory_guard.py work/my-feature [--root REPO]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from journal_io import read_events
from plan import parse_tasks_md, paths_overlap

RETRY_SMELL = 3  # attempts from which a task smells like an expensive prompting loop


def check_journal(events: list[dict]) -> tuple[list[str], list[str]]:
    """BHV-2a (fails) + BHV-2c (warns) from the journal alone."""
    fails: list[str] = []
    warns: list[str] = []
    ok_attempts: set[str] = set()
    attempt_count: dict[str, int] = {}
    for ev in events:
        tid = str(ev.get("id", ""))
        kind = ev.get("event")
        if kind == "task_attempt":
            attempt_count[tid] = attempt_count.get(tid, 0) + 1
            if ev.get("ok"):
                ok_attempts.add(tid)
        elif kind == "task_done":
            if tid not in ok_attempts:
                fails.append(
                    f"BHV-2a: {tid} is `task_done` with no prior successful "
                    f"`task_attempt` — journal forged or corrupt"
                )
        elif kind == "task_failed":
            warns.append(f"BHV-2c: {tid} ended `task_failed` (escalated to Owner)")
    for tid, n in attempt_count.items():
        if n >= RETRY_SMELL:
            warns.append(
                f"BHV-2c: {tid} took {n} attempts — retry-loop smell (expensive prompting loop)"
            )
    return fails, warns


def _git(root: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )
    return p.stdout


def check_commits(root: Path, feature: Path) -> tuple[list[str], list[str]]:
    """BHV-2b: every `[auto]` task commit stays inside its node's declared scope."""
    fails: list[str] = []
    warns: list[str] = []
    tasks_md = feature / "tasks.md"
    if not tasks_md.is_file():
        return fails, [f"no tasks.md in {feature} — commit-scope check skipped"]
    _, nodes = parse_tasks_md(tasks_md)
    by_id = {n.id: n for n in nodes}
    feat_rel = (
        str(feature.relative_to(root)) if feature.is_relative_to(root) else str(feature)
    )

    # The orchestrator's commit subject is canonical: `feat(<feature>): T<n> <title> [...]`
    subject_re = re.compile(rf"^\w+\({re.escape(feature.name)}\):\s+(T\d+)\b")
    log = _git(root, "log", "--format=%H%x09%s")
    for line in log.splitlines():
        sha, _, subject = line.partition("\t")
        m = subject_re.match(subject)
        if not m:
            continue
        node = by_id.get(m.group(1))
        if node is None:
            warns.append(
                f"commit {sha[:8]} references {m.group(1)} absent from tasks.md"
            )
            continue
        touched = _git(root, "show", "--name-only", "--format=", sha).split()
        allowed = [*node.files, feat_rel]
        for f in touched:
            if not any(paths_overlap(f, d) for d in allowed):
                fails.append(
                    f"BHV-2b: commit {sha[:8]} ({node.id}) touched `{f}` outside "
                    f"files_touched ∪ {feat_rel}/ — scope drift"
                )
    return fails, warns


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Trajectory checks for one feature run")
    ap.add_argument("feature", help="feature dir, e.g. work/my-feature")
    ap.add_argument(
        "--root", type=Path, default=None, help="repo root override (tests)"
    )
    args = ap.parse_args(argv)

    root = args.root or Path(__file__).resolve().parents[2]
    feature = Path(args.feature)
    if not feature.is_absolute():
        feature = root / feature

    events = read_events(feature)
    if not events:
        print(f"[trajectory] no journal in {feature.name} — nothing to check")
        return 0

    fails, warns = check_journal(events)
    f2, w2 = check_commits(root, feature)
    fails += f2
    warns += w2

    for w in warns:
        print(f"⚠️  {w}")
    for f in fails:
        print(f"⛔ {f}")
    if fails:
        print(f"[trajectory] {feature.name}: {len(fails)} violation(s)")
        return 1
    print(f"[trajectory] {feature.name}: OK ({len(warns)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
