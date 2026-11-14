"""T26 — EVAL-4 (part): `lab next` deduces the phase from the triplet statuses and the run
state, evaluates its exit gate, and says who decides, what, and the exact command
(spec BHV-4; design ADR-17, I-26, I-29, I-31, I-32). Six fixture triplets, one per phase.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ENGINE = REPO / "lab" / "engine"
sys.path.insert(0, str(ENGINE))

import cli  # noqa: E402
import kit  # noqa: E402
import next_step  # noqa: E402
import runstate  # noqa: E402

pytestmark = pytest.mark.eval

FIXTURES = Path(__file__).parent / "fixtures" / "next"
FEATURE = "work/feat"


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _project(tmp_path: Path, phase: str, done: dict[str, str] | None = None) -> Path:
    """Copy the fixture of `phase` into a fresh git project with a `squad` lab.toml."""
    proj = tmp_path / "proj"
    shutil.copytree(FIXTURES / phase, proj)
    (proj / ".lab").mkdir()
    (proj / ".lab" / "lab.toml").write_text(
        f'schema_version = 1\nkit_version = "{kit.kit_version()}"\nprofile = "squad"\n'
    )
    _git(proj, "init", "-q")
    if done:
        runstate.save(
            proj / FEATURE / ".runs" / "state.json", runstate.RunState(tasks=done)
        )
    return proj


def _tree(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }


CASES = {
    # phase → (state of the run, expected decider, command fragment)
    "spec": (None, "Métier", "lab spec-lint"),
    "design": (None, "FDE", "lab design-lint"),
    "plan": (None, "Owner", "status: approved"),
    "build": ({"T1": "done"}, "automatique", "lab run"),
    "review": ({"T1": "done", "T2": "done"}, "Owner", "approve.sh"),
    "merge": ({"T1": "done", "T2": "done", "CP-1": "done"}, "Owner", "merge"),
}


@pytest.mark.parametrize("phase", list(CASES))
def test_eval_4_next_phase_and_action(tmp_path: Path, phase: str) -> None:
    state, decider, fragment = CASES[phase]
    proj = _project(tmp_path, phase, state)
    step = next_step.compute(FEATURE, proj)
    assert step.phase == phase
    assert step.decider == decider
    assert fragment in step.command
    assert step.what


def test_eval_4_next_spec_gate_red_names_findings(tmp_path: Path) -> None:
    step = next_step.compute(FEATURE, _project(tmp_path, "spec"))
    assert step.gate_ok is False
    assert any("status" in f for f in step.findings)
    # OQ-13 / T33: the goldfish test is displayed here, never launched by T26
    assert any("lab goldfish work/feat" in n for n in step.notes)
    assert step.launch is None


def test_eval_4_next_design_gate_red_names_the_adr(tmp_path: Path) -> None:
    step = next_step.compute(FEATURE, _project(tmp_path, "design"))
    assert step.gate_ok is False
    assert any("ADR-1" in f for f in step.findings)


def test_eval_4_next_plan_lint_green_waits_for_owner_approval(tmp_path: Path) -> None:
    step = next_step.compute(FEATURE, _project(tmp_path, "plan"))
    assert step.phase == "plan"
    assert step.findings == []  # plan-lint green, only the signature is missing
    assert "approved" in step.what


def test_eval_4_next_plan_lint_red_is_reported(tmp_path: Path) -> None:
    proj = _project(tmp_path, "plan")
    tasks = proj / FEATURE / "tasks.md"
    tasks.write_text(
        tasks.read_text().replace("**depends_on:** [T1]", "**depends_on:** [T9]")
    )
    step = next_step.compute(FEATURE, proj)
    assert step.phase == "plan"
    assert step.gate_ok is False
    assert any("T9" in f for f in step.findings)


def test_eval_4_next_plan_applies_the_effective_policy(tmp_path: Path) -> None:
    """`regulated` forbids `mode: auto` checkpoints — the plan gate must know the profile."""
    proj = _project(tmp_path, "plan")
    (proj / ".lab" / "lab.toml").write_text(
        f'schema_version = 1\nkit_version = "{kit.kit_version()}"\nprofile = "regulated"\n'
    )
    tasks = proj / FEATURE / "tasks.md"
    tasks.write_text(tasks.read_text().replace("**mode:** blocking", "**mode:** auto"))
    step = next_step.compute(FEATURE, proj)
    assert step.gate_ok is False
    assert any("auto" in f for f in step.findings)


def test_eval_4_next_build_delegates_to_lab_run(tmp_path: Path) -> None:
    proj = _project(tmp_path, "build", {"T1": "done"})
    step = next_step.compute(FEATURE, proj)
    assert step.launch == [FEATURE, "--project", str(proj)]
    assert step.command == f"lab run {FEATURE} --project {proj}"


def test_eval_4_next_build_uses_git_for_done_tasks(tmp_path: Path) -> None:
    """No state.json at all: the canonical commit subjects name the delivered tasks."""
    proj = _project(tmp_path, "build")
    _git(proj, "config", "user.email", "t@t")
    _git(proj, "config", "user.name", "t")
    for t in ("T1", "T2"):
        _git(proj, "commit", "-q", "--allow-empty", "-m", f"feat(feat): {t} done")
    step = next_step.compute(FEATURE, proj)
    assert step.phase == "review"


def test_eval_4_next_review_names_the_pending_checkpoint(tmp_path: Path) -> None:
    proj = _project(tmp_path, "review", {"T1": "done", "T2": "done"})
    step = next_step.compute(FEATURE, proj)
    assert "CP-1" in step.command
    assert "reject.sh" in step.command
    assert step.launch is None


def test_eval_4_next_merge_is_always_the_owner(tmp_path: Path) -> None:
    proj = _project(tmp_path, "merge", {"T1": "done", "T2": "done", "CP-1": "done"})
    step = next_step.compute(FEATURE, proj)
    assert step.decider == "Owner"
    assert step.launch is None


@pytest.mark.parametrize("phase", list(CASES))
def test_eval_4_next_is_idempotent_and_writes_nothing(
    tmp_path: Path, phase: str, capsys: pytest.CaptureFixture[str]
) -> None:
    state = CASES[phase][0]
    proj = _project(tmp_path, phase, state)
    before = _tree(proj)
    args = ["next", FEATURE, "--project", str(proj), "--dry-run"]
    assert cli.main(args) == 0
    first = capsys.readouterr().out
    assert cli.main(args) == 0
    second = capsys.readouterr().out
    assert first == second
    assert first.strip()
    assert _tree(proj) == before


def test_eval_4_next_output_says_phase_gate_who_what_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    proj = _project(tmp_path, "design")
    assert cli.main(["next", FEATURE, "--project", str(proj)]) == 0
    out = capsys.readouterr().out
    for label in ("phase:", "gate:", "decider:", "what:", "command:"):
        assert label in out
    assert "design" in out and "FDE" in out


def test_eval_4_next_launch_goes_through_lab_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Agent step ⇒ the existing `lab run` relay, same arguments, no second engine."""
    proj = _project(tmp_path, "build", {"T1": "done"})
    seen: list[list[str]] = []
    monkeypatch.setattr(cli, "_relay", lambda a: seen.append(list(a)) or 0)
    assert cli.main(["next", FEATURE, "--project", str(proj)]) == 0
    assert seen == [[FEATURE, "--project", str(proj)]]


def test_eval_4_next_dry_run_never_launches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proj = _project(tmp_path, "build", {"T1": "done"})
    monkeypatch.setattr(cli, "_relay", lambda a: pytest.fail("launched"))
    assert cli.main(["next", FEATURE, "--project", str(proj), "--dry-run"]) == 0


def test_eval_4_next_spec_phase_never_launches_a_billed_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proj = _project(tmp_path, "spec")
    monkeypatch.setattr(cli, "_relay", lambda a: pytest.fail("launched"))
    assert cli.main(["next", FEATURE, "--project", str(proj)]) == 0


def test_eval_4_next_missing_feature_is_rc1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["next", "work/nope", "--project", str(tmp_path)]) == 1
    assert "work/nope" in capsys.readouterr().err
