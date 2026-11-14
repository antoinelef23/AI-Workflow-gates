"""`lab next` — deduce the current phase, run its exit gate, say who decides (spec BHV-4;
design ADR-17, I-26, I-29, I-31, I-32).

The current phase is the first whose exit gate is not green:

    spec → design → plan → build → review → merge

`compute` is pure: it reads the three frontmatters, the run state (git + `state.json`,
ADR-18) and the effective policy, and writes nothing. When the next step is an agent step it
only *names* the `lab run` arguments (`Step.launch`); the CLI relays them to the existing
engine — never a second engine. The goldfish test (BHV-8) is displayed at the spec phase,
not launched (`lab goldfish` arrives in T33, which wires the launch — OQ-13).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import designlint  # noqa: E402
import kit  # noqa: E402
import planlint  # noqa: E402
import policy as policy_mod  # noqa: E402
import runstate  # noqa: E402
import speclint  # noqa: E402
from lab_init import LabTomlError, read_lab_toml  # noqa: E402
from plan import parse_tasks_md  # noqa: E402
from registry import load_registry  # noqa: E402

PHASES = ("spec", "design", "plan", "build", "review", "merge")


class NextError(Exception):
    """The feature cannot be read (rc 1)."""


@dataclass
class Step:
    phase: str
    gate_ok: bool
    gate: str
    decider: str
    what: str
    command: str
    findings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    launch: list[str] | None = (
        None  # `lab run` arguments when the next step is an agent step
    )


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        raise NextError(f"{path} not found or unreadable") from None


def _gate(findings: list[str], what: str) -> str:
    if not findings:
        return f"green — {what}"
    return f"red — {what} ({len(findings)} finding{'s' if len(findings) != 1 else ''})"


def _spec(feature: str, text: str) -> Step | None:
    findings = speclint.lint(text)
    if not findings:
        return None
    return Step(
        phase="spec",
        gate_ok=False,
        gate=_gate(findings, "spec-lint"),
        findings=findings,
        decider="Métier",
        what="amend the spec until spec-lint is green (workshop decision), then validate it",
        command=f"lab spec-lint {feature}",
        notes=[
            f"measure (billed, not launched by `lab next`): lab goldfish {feature}",
        ],
    )


def _design(feature: str, text: str) -> Step | None:
    findings = designlint.lint(text)
    status = speclint.frontmatter(text).get("status", "")
    if status != "validated":
        findings.append(
            f"frontmatter status is {status or 'missing'!r}, expected 'validated'"
        )
    if not findings:
        return None
    return Step(
        phase="design",
        gate_ok=False,
        gate=_gate(findings, "design-lint + status validated"),
        findings=findings,
        decider="FDE",
        what="anchor every ADR on a reference pattern (or declare it deliberate), then validate the design",
        command=f"lab design-lint {feature}",
    )


def _effective_policy(project: Path) -> tuple[dict | None, str | None]:
    try:
        return policy_mod.effective_policy(read_lab_toml(project)), None
    except (LabTomlError, policy_mod.PolicyError) as e:
        return None, str(e)


def _plan(
    feature: str, fdir: Path, project: Path, state: runstate.RunState
) -> Step | None:
    fm, nodes = parse_tasks_md(fdir / "tasks.md")
    pol, pol_err = _effective_policy(project)
    errors, warnings = planlint.validate(
        fdir,
        fm,
        nodes,
        load_registry(kit.kit_root()),
        project=project,
        done={k for k, v in state.tasks.items() if v == "done"},
        policy=pol,
    )
    findings = list(errors)
    if pol_err:
        findings.append(f"effective policy unavailable: {pol_err}")
    notes = [f"warning: {w}" for w in warnings]
    if findings:
        return Step(
            phase="plan",
            gate_ok=False,
            gate=_gate(findings, "plan-lint with the effective policy"),
            findings=findings,
            notes=notes,
            decider="Owner",
            what="fix the plan until plan-lint is green, then approve it",
            command=f"lab validate {feature}",
        )
    if fm.get("status") != "approved":
        return Step(
            phase="plan",
            gate_ok=False,
            gate="red — plan-lint green, tasks.md not approved",
            notes=notes,
            decider="Owner",
            what=f"review the plan and approve it: tasks.md status is {fm.get('status') or 'missing'!r}, expected 'approved'",
            command=f"set `status: approved` in {feature}/tasks.md (Owner), then lab next {feature}",
        )
    return None


def _checkpoint_commands(feature: str, project: Path, cp: str) -> str:
    eng = kit.kit_root() / "lab" / "engine"
    env = f"LAB_PROJECT_ROOT={project} "
    return f'{env}{eng}/approve.sh {cp} {feature}  |  {env}{eng}/reject.sh {cp} {feature} "<reason>"'


def compute(feature: str, project: Path) -> Step:
    """Current phase of `<project>/<feature>`, its gate result, who decides, what, and the command."""
    project = Path(project)
    fdir = (project / feature).resolve()
    if not fdir.is_dir():
        raise NextError(f"feature {feature} not found under {project}")
    spec_text = _read(fdir / "spec.md")
    design_text = _read(fdir / "design.md")
    _read(fdir / "tasks.md")

    step = _spec(feature, spec_text) or _design(feature, design_text)
    if step:
        return step
    state = runstate.load(fdir, project)
    step = _plan(feature, fdir, project, state)
    if step:
        return step

    _, nodes = parse_tasks_md(fdir / "tasks.md")
    tasks = [n for n in nodes if not n.is_checkpoint]
    todo = [n.id for n in tasks if not state.is_done(n.id)]
    if todo:
        return Step(
            phase="build",
            gate_ok=False,
            gate=f"pending — {len(tasks) - len(todo)}/{len(tasks)} tasks done",
            decider="automatique",
            what=f"run the orchestrator: remaining {', '.join(todo)} (verify + evals + anti-empty-gate)",
            command=f"lab run {feature} --project {project}",
            launch=[feature, "--project", str(project)],
        )
    pending_cps = [n.id for n in nodes if n.is_checkpoint and not state.is_done(n.id)]
    if pending_cps:
        cp = pending_cps[0]
        return Step(
            phase="review",
            gate_ok=False,
            gate=f"pending — checkpoint {cp} not signed",
            decider="Owner",
            what=f"review {cp} and sign it (or reject it with a reason): checkpoints left {', '.join(pending_cps)}",
            command=_checkpoint_commands(feature, project, cp),
            notes=[
                f"if no run is waiting for {cp}, `lab run {feature} --project {project}` presents its review panel first"
            ],
        )
    return Step(
        phase="merge",
        gate_ok=True,
        gate="green — all tasks done, all checkpoints signed",
        decider="Owner",
        what="merge is always a human decision (INV-5): the Owner merges, no key can make it automatic",
        command="Owner: merge the branch (PR review + merge)",
    )


def render(step: Step) -> list[str]:
    lines = [f"phase: {step.phase}", f"gate: {step.gate}"]
    lines += [f"  - {f}" for f in step.findings]
    lines += [
        f"decider: {step.decider}",
        f"what: {step.what}",
        f"command: {step.command}",
    ]
    lines += [f"note: {n}" for n in step.notes]
    return lines
