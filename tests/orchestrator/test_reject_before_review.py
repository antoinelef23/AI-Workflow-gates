"""A pending rejection is honored without paying for a review panel; an approval
still regenerates the review first (self-hosting protocol)."""

from __future__ import annotations

from pathlib import Path

from .conftest import approve, run_orch

FM = "---\ntype: tasks\nfeature: feat\nstatus: approved\n---\n\n# Tasks — feat\n"
PLAN = """
### T1 — Task
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`

### CP-1 — CHECKPOINT : merge
- **trigger :** auto when [T1] done
- **validator :** Owner
- **mode :** blocking
"""


def _review_calls(sb: Path) -> int:
    log = sb / ".shim" / "argv.log"
    return log.read_text().count("reviewer agent") if log.exists() else 0


def test_pending_rejection_skips_the_review_panel(sandbox: Path) -> None:
    (sandbox / "work" / "feat" / "tasks.md").write_text(FM + PLAN)
    d = sandbox / "work" / "feat" / ".approvals"
    d.mkdir(parents=True)
    (d / "CP-1.rejected").write_text("reason=not good\ntasks=T1\n")
    approve(sandbox, "CP-1")  # the re-presented CP is then approved
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    # one review only: the re-presentation after T1's rework, none for the rejection
    assert _review_calls(sandbox) == 1, r.stdout


def test_approval_still_regenerates_the_review(sandbox: Path) -> None:
    (sandbox / "work" / "feat" / "tasks.md").write_text(FM + PLAN)
    approve(sandbox, "CP-1")
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _review_calls(sandbox) == 1
