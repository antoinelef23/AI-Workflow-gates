"""Owner lane + capability lint — a task is planned for the executor that CAN do it.

Found live in the fde-kit run (2026-11-12): T6 needed `git mv`, T7/T9 `just`, T11
wrote `.claude/` and the plugin's agents/skills/hooks — paths Claude Code treats
as sensitive, which a headless agent cannot write. Each one blocked the run.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from .conftest import REPO, approve, run_orch

sys.path.insert(0, str(REPO / "lab" / "engine"))
from plan import parse_tasks_md  # noqa: E402
from planlint import protected_paths, validate  # noqa: E402

FM = "---\ntype: tasks\nfeature: feat\nstatus: approved\n---\n\n# Tasks — feat\n"


class _NoRegistry:
    models: dict = {}


def _lint(sb: Path, body: str, done: set[str] | None = None):
    (sb / "work" / "feat" / "tasks.md").write_text(FM + body)
    fm, nodes = parse_tasks_md(sb / "work" / "feat" / "tasks.md")
    return validate(
        sb / "work" / "feat", fm, nodes, _NoRegistry(), project=sb, done=done
    )


def _task(nid: str, files: str, extra: str = "", verify: str = "true") -> str:
    v = f"- **verify :** `{verify}`\n" if verify else ""
    return (
        f"\n### {nid} — Task {nid}\n- **depends_on :** —\n- **implements :** [doc]\n"
        f"- **files_touched :** {files}\n- **done_when :** ok\n{v}{extra}"
    )


# ------------------------------------------------------------------ capability lint


def test_protected_paths_include_dot_claude_and_tracked_plugin_dirs(
    sandbox: Path,
) -> None:
    # The sandbox fixture tracks lab/plugin/.claude-plugin/plugin.json.
    roots = protected_paths(sandbox)
    assert ".claude" in roots
    assert {"lab/plugin/agents", "lab/plugin/hooks", "lab/plugin/skills"} <= set(roots)
    assert "lab/plugin/rules" not in roots  # rules file is plain content


def test_agent_task_on_protected_path_is_an_error(sandbox: Path) -> None:
    errors, _ = _lint(sandbox, _task("T1", "`.claude/agents`, `src/x.py`"))
    assert any("T1" in e and "protected paths" in e for e in errors), errors


def test_owner_task_on_protected_path_is_fine_but_needs_a_verify(sandbox: Path) -> None:
    ok, _ = _lint(sandbox, _task("T1", "`lab/plugin/hooks`", "- **agent:** owner\n"))
    assert not [e for e in ok if "T1" in e], ok
    errors, _ = _lint(
        sandbox, _task("T1", "`lab/plugin/hooks`", "- **agent:** owner\n", verify="")
    )
    assert any("Owner-lane task without verify" in e for e in errors), errors


def test_done_tasks_are_not_relinted(sandbox: Path) -> None:
    errors, _ = _lint(sandbox, _task("T1", "`.claude`"), done={"T1"})
    assert not [e for e in errors if "protected" in e], errors


def test_prompt_asking_for_an_ungranted_tool_warns_unless_negated(
    sandbox: Path,
) -> None:
    ask = "- **prompt:**\n  > Move the files with `git mv`, then run `just gate`.\n"
    _, warnings = _lint(sandbox, _task("T1", "`a.txt`", ask))
    assert any("git mv" in w and "just" in w for w in warnings), warnings
    cure = (
        "- **prompt:**\n  > Do not try to run `just`; add the recipe `just report`.\n"
    )
    _, warnings = _lint(sandbox, _task("T1", "`a.txt`", cure))
    assert not [w for w in warnings if "allowlist" in w], warnings


# ---------------------------------------------------------------------- Owner lane


def _owner_plan(sb: Path, verify: str = "test -f owner.txt") -> None:
    (sb / "work" / "feat" / "tasks.md").write_text(
        FM + _task("T1", "`owner.txt`", "- **agent:** owner\n", verify=verify)
    )


def test_owner_task_is_never_dispatched_to_an_agent_and_commits_on_green(
    sandbox: Path,
) -> None:
    _owner_plan(sandbox)
    (sandbox / "owner.txt").write_text("done by hand\n")  # the Owner's work
    approve(sandbox, "T1")
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    argv = sandbox / ".shim" / "argv.log"
    assert not argv.exists() or "task T1" not in argv.read_text()  # no agent call
    msg = subprocess.run(
        ["git", "log", "-1", "--format=%B"], cwd=sandbox, capture_output=True, text=True
    ).stdout
    assert "Run: owner" in msg
    shown = subprocess.run(
        ["git", "show", "--name-only", "--format=", "HEAD"],
        cwd=sandbox,
        capture_output=True,
        text=True,
    ).stdout
    assert "owner.txt" in shown
    events = [
        json.loads(ln)["event"]
        for ln in (sandbox / "work" / "feat" / ".runs" / "journal.jsonl")
        .read_text()
        .splitlines()
    ]
    assert events.index("owner_signed") < events.index("task_done")  # guard BHV-2a


def test_owner_task_signed_but_red_is_failed(sandbox: Path) -> None:
    _owner_plan(sandbox)  # owner.txt never created → verify red
    approve(sandbox, "T1")
    r = run_orch(sandbox)
    assert r.returncode == 1, r.stdout + r.stderr
    state = json.loads(
        (sandbox / "work" / "feat" / ".runs" / "state.json").read_text()
    )["tasks"]
    assert state["T1"] == "failed"


def test_owner_task_rejected_is_blocked(sandbox: Path) -> None:
    _owner_plan(sandbox)
    d = sandbox / "work" / "feat" / ".approvals"
    d.mkdir(parents=True, exist_ok=True)
    (d / "T1.rejected").write_text("reason=cannot do it today\n")
    r = run_orch(sandbox)
    assert r.returncode == 1, r.stdout + r.stderr
    state = json.loads(
        (sandbox / "work" / "feat" / ".runs" / "state.json").read_text()
    )["tasks"]
    assert state["T1"] == "blocked"


def test_owner_task_dry_run_says_owner(sandbox: Path) -> None:
    _owner_plan(sandbox)
    r = run_orch(sandbox, "--dry-run")
    assert "OWNER TASK T1" in r.stdout, r.stdout


def test_task_with_a_commit_is_done_for_the_lint_without_any_run_state(
    sandbox: Path,
) -> None:
    # CI has no .runs/state.json (gitignored): "done" must come from git history.
    subprocess.run(
        ["git", "commit", "-q", "--allow-empty", "-m", "feat(feat): T1 Task T1 [auto]"],
        cwd=sandbox,
        check=True,
    )
    errors, _ = _lint(sandbox, _task("T1", "`.claude`"))  # no `done=` passed
    assert not [e for e in errors if "protected" in e], errors
    errors, _ = _lint(sandbox, _task("T2", "`.claude`"))  # T2 has no commit
    assert any("T2" in e and "protected" in e for e in errors), errors
