"""T18 — EVAL-3 (part): the engine and its pre-flight read the effective policy
(spec BHV-3; design ADR-14, ADR-16, I-20, I-22, I-23). Shim `claude`, no live session."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from orchestrator.conftest import approve, run_orch, sandbox  # noqa: F401  (sandbox = fixture)

pytestmark = pytest.mark.eval

FM = """---
type: tasks
feature: feat
status: approved
---

# Tasks — feat
"""


def _task(n: int, deps: str = "—") -> str:
    return f"""
### T{n} — Task {n}
- **depends_on :** {deps}
- **implements :** [doc]
- **files_touched :** `t{n}.txt`
- **done_when :** ok
- **verify :** `true`
"""


def _commit(sb: Path, msg: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=sb, check=True)
    subprocess.run(["git", "commit", "-qm", msg], cwd=sb, check=True)


def _plan(sb: Path, *tasks: str) -> None:
    (sb / "work" / "feat" / "tasks.md").write_text(FM + "".join(tasks))
    _commit(sb, "plan")


def _lab_toml(sb: Path, profile: str = "squad", overrides: str = "") -> None:
    import kit

    (sb / ".lab" / "lab.toml").write_text(
        f'schema_version = 1\nkit_version = "{kit.kit_version()}"\n'
        f'profile = "{profile}"\n{overrides}'
    )
    _commit(sb, "lab.toml")


def _events(sb: Path) -> list[dict]:
    p = sb / "work" / "feat" / ".runs" / "journal.jsonl"
    return [json.loads(line) for line in p.read_text().splitlines()]


def _argv(sb: Path) -> str:
    p = sb / ".shim" / "argv.log"
    return p.read_text() if p.exists() else ""


# ---------------------------------------------------------------- pre-flight


def test_eval_3_missing_lab_toml_refused_naming_lab_init(sandbox: Path) -> None:  # noqa: F811
    _plan(sandbox, _task(1))
    (sandbox / ".lab" / "lab.toml").unlink()
    for flags in ((), ("--dry-run",)):
        r = run_orch(sandbox, *flags)
        assert r.returncode == 1, r.stdout + r.stderr
        assert "lab init" in r.stdout + r.stderr and "--profile" in r.stdout + r.stderr
    assert _argv(sandbox) == ""
    # --validate never pre-flights
    assert run_orch(sandbox, "--validate").returncode == 0


def test_eval_3_invalid_policy_refused_with_its_message(sandbox: Path) -> None:  # noqa: F811
    _plan(sandbox, _task(1))
    _lab_toml(sandbox, "regulated", "[overrides]\nmin_reviewers = 1\n")
    r = run_orch(sandbox, env_extra={"LAB_RUNNER": "sandbox"})
    assert r.returncode == 1
    assert "min_reviewers=1 is looser than floor 'regulated' (2)" in r.stdout + r.stderr


def test_eval_3_regulated_requires_sandbox_runner(sandbox: Path) -> None:  # noqa: F811
    _plan(sandbox, _task(1))
    _lab_toml(sandbox, "regulated")
    for flags in ((), ("--dry-run",)):
        r = run_orch(sandbox, *flags)
        assert r.returncode == 1, r.stdout + r.stderr
        assert "sandbox_required" in r.stdout + r.stderr
    assert _argv(sandbox) == ""
    # with the sandbox runner the pre-flight lets a dry-run through
    ok = run_orch(sandbox, "--dry-run", env_extra={"LAB_RUNNER": "sandbox"})
    assert ok.returncode == 0, ok.stdout + ok.stderr


def test_eval_3_regulated_refuses_force(sandbox: Path) -> None:  # noqa: F811
    _plan(sandbox, _task(1))
    _lab_toml(sandbox, "regulated")
    r = run_orch(sandbox, "--force", env_extra={"LAB_RUNNER": "sandbox"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "allow_force" in r.stdout + r.stderr
    assert _argv(sandbox) == ""


def test_eval_3_solo_accepts_force(sandbox: Path) -> None:  # noqa: F811
    _plan(sandbox, _task(1))
    _lab_toml(sandbox, "solo")
    r = run_orch(sandbox, "--force")
    assert r.returncode == 0, r.stdout + r.stderr


def test_eval_3_plan_lint_receives_policy(sandbox: Path) -> None:  # noqa: F811
    # 4 tasks in a chain: fine for squad (5), too many for an override down to 3
    chain = (_task(1), _task(2, "[T1]"), _task(3, "[T2]"), _task(4, "[T3]"))
    _plan(sandbox, *chain)
    _lab_toml(sandbox, "squad", "[overrides]\nmax_tasks_between_checkpoints = 3\n")
    r = run_orch(sandbox, "--dry-run")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "Invalid plan" in r.stdout


# ------------------------------------------------- constants read the policy


def _parallel_log(sb: Path) -> list[str]:
    return [
        line.split()[0] for line in (sb / ".shim" / "par.log").read_text().splitlines()
    ]


def _par_scripts(sb: Path) -> None:
    for i in (1, 2, 3):
        (sb / ".shim" / f"T{i}.sh").write_text(
            "echo s >> .shim/par.log\nsleep 1\necho e >> .shim/par.log\n"
            'echo "STATUS: done"\n'
        )


def test_eval_3_max_parallel_override_serializes_the_wave(sandbox: Path) -> None:  # noqa: F811
    _plan(sandbox, _task(1), _task(2), _task(3))
    _par_scripts(sandbox)
    _lab_toml(sandbox, "squad", "[overrides]\nmax_parallel = 1\n")
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _parallel_log(sandbox) == ["s", "e"] * 3


def test_eval_3_max_parallel_floor_runs_the_wave_in_parallel(sandbox: Path) -> None:  # noqa: F811
    _plan(sandbox, _task(1), _task(2), _task(3))
    _par_scripts(sandbox)
    r = run_orch(sandbox)  # squad floor: max_parallel = 3
    assert r.returncode == 0, r.stdout + r.stderr
    assert _parallel_log(sandbox)[:3] == ["s", "s", "s"]


def test_eval_3_max_task_attempts_override_changes_retries(sandbox: Path) -> None:  # noqa: F811
    _plan(sandbox, _task(1))
    (sandbox / ".evals_fail").write_text("")
    _lab_toml(sandbox, "squad", "[overrides]\nmax_task_attempts = 1\n")
    r = run_orch(sandbox)
    assert r.returncode == 1
    assert "attempt 1/1" in r.stdout and "attempt 2/" not in r.stdout


def test_eval_3_max_task_attempts_floor_is_three(sandbox: Path) -> None:  # noqa: F811
    _plan(sandbox, _task(1))
    (sandbox / ".evals_fail").write_text("")
    r = run_orch(sandbox)
    assert "attempt 3/3" in r.stdout


def test_eval_3_budget_usd_is_the_default_and_env_wins(sandbox: Path) -> None:  # noqa: F811
    _plan(sandbox, _task(1), _task(2, "[T1]"))
    _lab_toml(sandbox, "squad", "[overrides]\nbudget_usd = 0.0005\n")
    r = run_orch(sandbox)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "budget_stop" in [e["event"] for e in _events(sandbox)]
    # LAB_BUDGET_USD still wins when set
    runs = sandbox / "work" / "feat" / ".runs"
    (runs / "journal.jsonl").unlink()
    (runs / "state.json").unlink(missing_ok=True)
    r2 = run_orch(sandbox, env_extra={"LAB_BUDGET_USD": "100"})
    assert r2.returncode == 0, r2.stdout + r2.stderr


# ------------------------------------------------------------- run_start


def test_eval_3_run_start_carries_profile_and_policy(sandbox: Path) -> None:  # noqa: F811
    _plan(sandbox, _task(1))
    _lab_toml(sandbox, "squad", "[overrides]\nmax_parallel = 2\nmin_reviewers = 2\n")
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    start = _events(sandbox)[0]
    assert start["event"] == "run_start"
    assert start["profile"] == "squad"
    pol = start["policy"]
    assert pol["max_parallel"] == {"value": 2, "origin": "override (free key)"}
    assert pol["min_reviewers"] == {"value": 2, "origin": "override"}
    assert pol["allow_force"] == {"value": True, "origin": "floor"}
    assert pol["goldfish_min_score"] == {"value": None, "origin": "floor"}


# ------------------------------------- INV-5 at run time: the merge CP is human


def _auto_cp(n: int, deps: str, title: str) -> str:
    return f"""
### CP-{n} — CHECKPOINT : {title}
- **trigger :** auto quand {deps} done
- **validator :** Owner
- **mode :** auto
"""


@pytest.mark.parametrize("profile", ["solo", "squad"])
def test_eval_3_merge_cp_never_auto_approved_under_force(
    sandbox: Path,  # noqa: F811
    profile: str,
) -> None:
    # sink CP, mode auto, --force skips plan-lint, evals green (stub), reviewer PASS (shim)
    _plan(sandbox, _task(1), _auto_cp(1, "[T1]", "final review"))
    if profile != "squad":  # the fixture's default
        _lab_toml(sandbox, profile)
    approve(sandbox, "CP-1")  # the human approval the run must wait for / honor
    r = run_orch(sandbox, "--force")
    assert r.returncode == 0, r.stdout + r.stderr
    handled = list((sandbox / "work" / "feat" / ".approvals").glob("CP-1.handled-*"))
    assert handled, "the human approval must have been the one honored"
    assert "auto-approved" not in handled[0].read_text()
    assert "never auto-approved" in r.stdout or "never auto-approved" in r.stderr


def test_eval_3_merge_titled_cp_never_auto_approved(sandbox: Path) -> None:  # noqa: F811
    # not a sink (T2 follows) but "merge" in its title: same test as plan-lint
    _plan(
        sandbox,
        _task(1),
        _auto_cp(1, "[T1]", "merge"),
        _task(2, "[CP-1]"),
    )
    _lab_toml(sandbox, "solo")
    approve(sandbox, "CP-1")
    r = run_orch(sandbox, "--force")
    assert r.returncode == 0, r.stdout + r.stderr
    handled = list((sandbox / "work" / "feat" / ".approvals").glob("CP-1.handled-*"))
    assert handled and "auto-approved" not in handled[0].read_text()
