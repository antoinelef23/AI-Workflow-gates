#!/usr/bin/env python3
"""The plan model — Node, tasks.md parsing, and DAG helpers. Pure, no orchestrator
state. Shared by the orchestrator engine and plan-lint."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# Spec ID tokens (INV/BHV/EX/EVAL/NG-…) referenced by tasks' `implements`.
SPEC_ID = re.compile(r"\b(?:INV|BHV|EX|EVAL|NG)-[A-Za-z0-9]+\b")


@dataclass
class Node:
    id: str
    title: str
    is_checkpoint: bool
    depends_on: list[str] = field(default_factory=list)
    prompt: str = ""
    implements: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    verify: str = ""
    done_when: str = ""
    mode: str = "blocking"  # checkpoints: blocking | auto
    status: str = "pending"  # pending | running | done | failed | blocked | skipped
    rework: str = ""  # Owner comment after a checkpoint rejection (passed to the agent)
    model: str = ""  # task model override (otherwise: registry role default)
    reviewers: int = 1  # size of the reviewer panel (checkpoint) — >=2 = majority vote


def parse_tasks_md(path: Path) -> tuple[dict, list[Node]]:
    text = path.read_text(encoding="utf-8")

    fm = {}
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fm[k.strip()] = v.split("#")[0].strip()

    nodes: list[Node] = []
    sections = re.split(r"\n### ", text)
    for sec in sections[1:]:
        header, _, body = sec.partition("\n")
        hm = re.match(r"(T\d+|CP-\d+)\s*—\s*(.*)", header.strip())
        if not hm:
            continue
        nid, title = hm.group(1), hm.group(2).strip()
        is_cp = nid.startswith("CP")

        deps: list[str] = []
        dm = re.search(r"\*\*depends_on\s*:?\*\*\s*\[([^\]]*)\]", body)
        if dm:
            deps = [d.strip() for d in dm.group(1).split(",") if d.strip()]
        if is_cp:
            tm = re.search(
                r"\*\*trigger\s*:?\*\*[^\n]*?(?:quand|when)\s+\[?([T\d\s,]+?)\]?\s+(?:(?:sont|are)\s+)?done",
                body,
            )
            if tm:
                deps = [d.strip() for d in tm.group(1).split(",") if d.strip()]

        pm = re.search(r"\*\*prompt\s*:?\*\*\s*\n?((?:\s*>.*\n?)+)", body)
        prompt = ""
        if pm:
            prompt = "\n".join(
                line.strip().lstrip("> ") for line in pm.group(1).splitlines()
            ).strip()
        if not prompt:
            pm = re.search(r"\*\*prompt\s*:?\*\*\s*([^\n]+)", body)
            if pm:
                prompt = pm.group(1).strip()

        node = Node(nid, title, is_cp, deps, prompt)

        im = re.search(r"\*\*implements\s*:?\*\*\s*\[([^\]]*)\]", body)
        if im:
            node.implements = [t.strip() for t in im.group(1).split(",") if t.strip()]
        fmm = re.search(r"\*\*files_touched\s*:?\*\*\s*([^\n]+)", body)
        if fmm:
            node.files = re.findall(r"`([^`]+)`", fmm.group(1))
        vm = re.search(r"\*\*verify\s*:?\*\*\s*`([^`]+)`", body)
        if vm:
            node.verify = vm.group(1).strip()
        dw = re.search(r"\*\*done_when\s*:?\*\*\s*([^\n]+)", body)
        if dw:
            node.done_when = dw.group(1).strip()
        mm = re.search(r"\*\*mode\s*:?\*\*\s*(auto|blocking)", body)
        if mm:
            node.mode = mm.group(1)
        mom = re.search(r"\*\*model\s*:?\*\*\s*`?([\w.\-]+)`?", body)
        if mom:
            node.model = mom.group(1)
        rm = re.search(r"\*\*reviewers\s*:?\*\*\s*(\d+)", body)
        if rm:
            node.reviewers = max(1, int(rm.group(1)))

        nodes.append(node)

    # Each task implicitly depends on every checkpoint defined before it
    last_cp: str | None = None
    for n in nodes:
        if n.is_checkpoint:
            last_cp = n.id
        elif last_cp and last_cp not in n.depends_on and not n.depends_on:
            n.depends_on.append(last_cp)
    return fm, nodes


def ancestors(nodes: list[Node]) -> dict[str, set[str]]:
    """Transitive depends_on closure per node (memoized; cuts cycles)."""
    by_id = {n.id: n for n in nodes}
    memo: dict[str, set[str]] = {}

    def walk(nid: str, stack: tuple[str, ...] = ()) -> set[str]:
        if nid in memo:
            return memo[nid]
        if nid in stack:  # cycle — flagged by validate(), we cut here
            return set()
        acc: set[str] = set()
        for d in by_id.get(nid, Node(nid, "", False)).depends_on:
            acc.add(d)
            acc |= walk(d, (*stack, nid))
        memo[nid] = acc
        return acc

    return {n.id: walk(n.id) for n in nodes}


def paths_overlap(a: str, b: str) -> bool:
    a, b = a.strip().rstrip("/"), b.strip().rstrip("/")
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def skip_dependents(failed: Node, nodes: list[Node]) -> None:
    """Containment: only the (transitive) dependents of a failure are neutralized."""
    queue = [failed.id]
    while queue:
        cur = queue.pop()
        for n in nodes:
            if n.status == "pending" and cur in n.depends_on:
                n.status = "skipped"
                print(f"⏭  {n.id} skipped (depends on {cur})", flush=True)
                queue.append(n.id)
