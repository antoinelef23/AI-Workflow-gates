#!/usr/bin/env python3
"""Plan-lint — static validation of a feature's tasks.md before it runs.

A plan that doesn't lint doesn't run; that's what lets the Owner approve once and
walk away. Pure: takes the parsed nodes + the model registry, returns
(errors, warnings). No orchestrator state.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from plan import SPEC_ID, Node, ancestors, paths_overlap
from verify import parse_verify


# Tools an agent may need that the default allowlist (runner.DEFAULT_ALLOWED_TOOLS)
# does not grant — prompts that ask for them plan a task the agent cannot do.
_UNGRANTED = {
    "git mv": re.compile(r"\bgit mv\b"),
    "git rm": re.compile(r"\bgit rm\b"),
    # only when asked to RUN it ("add the recipe `just report`" is fine)
    "just": re.compile(
        r"\b(?:run|runs|running|launch|execute|lancer?|exécuter?)\b[^.\n]{0,25}?`?just\b",
        re.I,
    ),
}


_NEGATION = re.compile(r"\b(?:not|never|don't|n't|without|pas|jamais|sans)\b", re.I)


def _asks(rx: re.Pattern, prompt: str) -> bool:
    """A non-negated request: "do not try to run `just`" is the cure, not the ask."""
    return any(
        not _NEGATION.search(prompt[max(0, m.start() - 25) : m.start() + 8])
        for m in rx.finditer(prompt)
    )


def protected_paths(project: Path) -> list[str]:
    """Paths a headless agent (`claude -p`, nobody to answer a permission prompt)
    cannot write: Claude Code treats `.claude/` and a plugin's agents / skills /
    hooks / commands / manifest as sensitive. A plugin root is any tracked
    `<dir>/.claude-plugin/plugin.json`. Found live: fde-kit T11 (2026-11-12)."""
    roots = [".claude"]
    out = subprocess.run(
        ["git", "ls-files", "--", "*.claude-plugin/plugin.json"],
        cwd=project,
        capture_output=True,
        text=True,
    ).stdout
    for manifest in out.splitlines():
        plug = str(Path(manifest).parent.parent)
        pre = "" if plug == "." else plug + "/"
        roots += [f"{pre}{d}" for d in ("agents", "skills", "hooks", "commands")]
        roots.append(f"{pre}.claude-plugin")
    return roots


def _capability_lint(
    nodes: list[Node],
    project: Path,
    done: set[str],
    errors: list[str],
    warnings: list[str],
) -> None:
    """Plan a task only if its executor can perform it (lab-fix item 13: T6 had no
    `git mv`, T7/T9 no `just`, T11 wrote protected paths — each blocked a run)."""
    protected = protected_paths(project)
    for n in nodes:
        if n.is_checkpoint or n.id in done:
            continue
        if n.agent == "owner":
            if not n.verify:
                errors.append(
                    f"{n.id}: Owner-lane task without verify — the engine needs a "
                    "mechanical check to accept the Owner's work"
                )
            continue
        hits = [f for f in n.files if any(paths_overlap(f, p) for p in protected)]
        if hits:
            errors.append(
                f"{n.id}: files_touched {hits} are protected paths a headless agent "
                "cannot write — set `**agent:** owner` for that part, or split the task"
            )
        asks = [t for t, rx in _UNGRANTED.items() if _asks(rx, n.prompt)]
        if asks:
            warnings.append(
                f"{n.id}: the prompt asks for {asks}, outside the agent's allowlist — "
                "state that the orchestrator runs it, or route the step to the Owner lane"
            )


def validate(
    feature: Path,
    fm: dict,
    nodes: list[Node],
    registry,
    project: Path | None = None,
    done: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Plan-lint. Returns (errors, warnings). `project` enables the capability
    lint (agent vs protected paths / tool allowlist); `done` = nodes already done."""
    errors: list[str] = []
    warnings: list[str] = []
    by_id = {n.id: n for n in nodes}

    if not nodes:
        return (["no task recognized — check the format `### T1 — title`"], [])
    seen: set[str] = set()
    for n in nodes:
        if n.id in seen:
            errors.append(f"{n.id}: duplicate ID")
        seen.add(n.id)

    # Graph
    for n in nodes:
        for d in n.depends_on:
            if d not in by_id:
                errors.append(f"{n.id}: depends_on [{d}] does not exist")
    # Cycles (DFS coloring)
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n.id: WHITE for n in nodes}

    def dfs(nid: str) -> bool:
        color[nid] = GREY
        for d in by_id[nid].depends_on:
            if d not in by_id:
                continue
            if color[d] == GREY:
                errors.append(f"dependency cycle via {nid} → {d}")
                return True
            if color[d] == WHITE and dfs(d):
                return True
        color[nid] = BLACK
        return False

    for n in nodes:
        if color[n.id] == WHITE and dfs(n.id):
            break

    # Mandatory task fields
    for n in nodes:
        if n.is_checkpoint:
            continue
        if not n.done_when:
            errors.append(
                f'{n.id}: done_when missing (nothing executable defines "done")'
            )
        if not n.files:
            errors.append(
                f"{n.id}: files_touched missing or without backticks (parallelism unverifiable)"
            )
        if not n.prompt:
            warnings.append(
                f"{n.id}: empty prompt — the implementer will only have the title"
            )
        if not n.verify:
            warnings.append(
                f"{n.id}: no executable verify — done_when will not be checked mechanically"
            )
        else:
            try:
                parse_verify(n.verify)
            except ValueError as e:
                errors.append(f"{n.id}: invalid verify (`{n.verify}`) — {e}")

    # Spec IDs
    spec_path = feature / "spec.md"
    if spec_path.exists():
        spec_text = spec_path.read_text(encoding="utf-8")
        for n in nodes:
            for tok in n.implements:
                for sid in SPEC_ID.findall(tok):
                    if sid not in spec_text:
                        errors.append(
                            f"{n.id}: implements [{sid}] not found in spec.md"
                        )
        # Each EVAL-n declared in the spec must be carried by a task
        claimed = {s for n in nodes for t in n.implements for s in SPEC_ID.findall(t)}
        for ev in sorted(set(re.findall(r"\bEVAL-\w+\b", spec_text))):
            if ev not in claimed:
                warnings.append(
                    f"{ev} declared in spec.md §7 but carried by no task (implements)"
                )
        # finding L4: ID coverage only validates EVAL-*. A plan that implements
        # behaviors/invariants WITHOUT any EVAL-* relies on off-plan tests — we
        # flag it (the hard gate stays on EVAL-*).
        impl_behaviors = {
            s
            for n in nodes
            for t in n.implements
            for s in SPEC_ID.findall(t)
            if s.startswith(("BHV-", "INV-"))
        }
        if impl_behaviors and not any(s.startswith("EVAL-") for s in claimed):
            warnings.append(
                f"behaviors/invariants are implemented ({sorted(impl_behaviors)[:3]}…) "
                "but no task carries an EVAL-*: eval coverage relies on off-plan tests"
            )
        # Documentation drift: the "# version : x.y.z" pointers must track the spec
        sv = re.search(r"^version:\s*([\d.]+)", spec_text, re.M)
        if sv:
            for art in ("tasks.md", "design.md"):
                p = feature / art
                if not p.exists():
                    continue
                m = re.search(
                    r"^spec:.*?version\s*:?\s*([\d.]+)",
                    p.read_text(encoding="utf-8"),
                    re.M,
                )
                if m and m.group(1) != sv.group(1):
                    warnings.append(
                        f"{art} references spec v{m.group(1)} but spec.md is at v{sv.group(1)} — "
                        f"documentation drift, update the pointer after the amendment"
                    )
    else:
        errors.append("spec.md not found next to tasks.md")

    # Parallelism safety: two unordered tasks must not share any path
    anc = ancestors(nodes)
    tasks = [n for n in nodes if not n.is_checkpoint]
    for i, a in enumerate(tasks):
        for b in tasks[i + 1 :]:
            if a.id in anc[b.id] or b.id in anc[a.id]:
                continue  # ordered by the DAG
            clash = [
                (fa, fb) for fa in a.files for fb in b.files if paths_overlap(fa, fb)
            ]
            if clash:
                errors.append(
                    f"{a.id} ∥ {b.id}: runnable in parallel but files_touched overlap "
                    f"({clash[0][0]} ↔ {clash[0][1]}) — add a depends_on or separate the paths"
                )

    # Checkpoints
    cps = [n for n in nodes if n.is_checkpoint]
    if not cps:
        warnings.append(
            "no checkpoint — a plan without a human pause violates CLAUDE.md (hard rules)"
        )
    dependents = {n.id: [m.id for m in nodes if n.id in m.depends_on] for n in nodes}
    for cp in cps:
        if not cp.depends_on:
            warnings.append(
                f'{cp.id}: trigger not parsed — add "trigger : auto when [Tn, Tm] done"'
            )
        is_sink = not dependents[cp.id]
        mentions_merge = "merge" in (cp.title + " ").lower()
        if cp.mode == "auto" and (is_sink or mentions_merge):
            errors.append(
                f"{cp.id}: a final/merge checkpoint cannot be mode auto — the merge is human, always"
            )

    # Separation of duties: one model should not both implement AND arbitrate alone
    if registry.models:
        impl = registry.role_default("implementer")
        rev = registry.role_default("reviewer")
        if impl and impl == rev:
            warnings.append(
                f"separation of duties: reviewer and implementer point to the same model ({impl}) — "
                "an auto checkpoint will not be able to self-validate (will fall back to human). "
                "Assign a distinct reviewer model in lab/models/registry.toml."
            )

    # Models: a task override must name a model eligible for its role
    if registry.models:
        for n in nodes:
            if not n.model:
                continue
            role = "reviewer" if n.is_checkpoint else "implementer"
            m = registry.by_id(n.model)
            if m is None:
                warnings.append(
                    f'{n.id}: model "{n.model}" absent from the registry (lab/models/registry.toml)'
                )
            elif role not in m.roles:
                warnings.append(
                    f'{n.id}: model "{n.model}" not eligible for role {role} (registry: {m.roles})'
                )

    if project is not None:
        _capability_lint(nodes, project, done or set(), errors, warnings)

    return errors, warnings
