"""Orchestrator regression suite — replays the 2026-06-10 simulation campaign
(devis-pose / export-devis) in seconds, with the claude shim.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .conftest import REPO, approve, run_orch

FM = """---
type: tasks
feature: feat
status: approved
---

# Tasks — feat
"""


def write_tasks(sandbox: Path, body: str) -> None:
    (sandbox / "work" / "feat" / "tasks.md").write_text(FM + body)


def state(sandbox: Path) -> dict:
    return json.loads((sandbox / "work" / "feat" / ".runs" / "state.json").read_text())


def journal_events(sandbox: Path) -> list[dict]:
    p = sandbox / "work" / "feat" / ".runs" / "journal.jsonl"
    return [json.loads(line) for line in p.read_text().splitlines()]


# ---------------------------------------------------------------- plan-lint


def test_lint_catches_all_error_classes(sandbox: Path) -> None:
    write_tasks(
        sandbox,
        """
### T1 — A
- **depends_on :** [T9]
- **implements :** [BHV-99]
- **files_touched :** `src/core/`
- **done_when :** ok
- **verify :** `true`

### T2 — B (overlap with T1)
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `src/core/sub/`
- **done_when :** ok
- **verify :** `true`

### T3 — C without done_when or files

### CP-1 — CHECKPOINT : final merge
- **trigger :** auto quand [T1, T2, T3] done
- **validator :** Owner
- **mode :** auto
""",
    )
    r = run_orch(sandbox, "--validate")
    assert r.returncode == 1
    for needle in [
        "depends_on [T9] does not exist",
        "[BHV-99] not found",
        "T3: done_when missing",
        "T3: files_touched missing",
        "files_touched overlap",
        "cannot be mode auto",
    ]:
        assert needle in r.stdout, f"lint should flag: {needle}\n{r.stdout}"


def test_lint_catches_cycle(sandbox: Path) -> None:
    write_tasks(
        sandbox,
        """
### T1 — A
- **depends_on :** [T2]
- **files_touched :** `a/`
- **done_when :** ok
- **verify :** `true`

### T2 — B
- **depends_on :** [T1]
- **files_touched :** `b/`
- **done_when :** ok
- **verify :** `true`
""",
    )
    r = run_orch(sandbox, "--validate")
    assert r.returncode == 1
    assert "dependency cycle" in r.stdout


def test_dry_run_wave_order(sandbox: Path) -> None:
    write_tasks(
        sandbox,
        """
### T1 — Base
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`

### T2 — Follow-up
- **depends_on :** [T1]
- **implements :** [doc]
- **files_touched :** `t2.txt`
- **done_when :** ok
- **verify :** `true`
""",
    )
    r = run_orch(sandbox, "--dry-run")
    assert r.returncode == 0
    assert r.stdout.index("Parallel wave: T1") < r.stdout.index("Parallel wave: T2")


# ---------------------------------------------------------------- execution


def test_happy_run_with_auto_checkpoint(sandbox: Path) -> None:
    (sandbox / ".shim" / "T1.sh").write_text(
        'echo "data" > t1.txt\necho "STATUS: done"\n'
    )
    write_tasks(
        sandbox,
        """
### T1 — Produces a file
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** file present
- **verify :** `test -f t1.txt`

### CP-1 — CHECKPOINT : mechanical check
- **trigger :** auto quand [T1] done
- **validator :** Owner
- **mode :** auto

### T2 — Final step
- **depends_on :** [CP-1]
- **implements :** [doc]
- **files_touched :** `t2.txt`
- **done_when :** ok
- **verify :** `true`

### CP-2 — CHECKPOINT : merge
- **trigger :** auto quand T2 done
- **validator :** Owner
- **mode :** blocking
""",
    )
    approve(sandbox, "CP-2")  # pre-approved: the test must not wait for a human
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    assert state(sandbox) == {
        "T1": "done",
        "CP-1": "done",
        "T2": "done",
        "CP-2": "done",
    }
    # CP-1 auto-validated without a human, on the strength of the reviewer shim (PASS) + evals stub
    auto = (sandbox / "work" / "feat" / ".approvals" / "CP-1").read_text()
    assert "auto-approved" in auto
    # journal: attempts, done, reviews, aggregated cost
    kinds = [e["event"] for e in journal_events(sandbox)]
    assert kinds.count("task_done") == 2 and "review" in kinds and "run_end" in kinds
    # traceable scoped commit
    import subprocess

    log = subprocess.run(
        ["git", "log", "--oneline"], cwd=sandbox, capture_output=True, text=True
    ).stdout
    assert "T1 Produces a file" in log and "[auto]" in log


def test_blocked_containment_and_resume(sandbox: Path) -> None:
    # T1 counts its runs (proof of no replay on resume); T2 blocks on OQ-1
    (sandbox / ".shim" / "T1.sh").write_text(
        'echo x >> .shim/t1_count\necho "STATUS: done"\n'
    )
    (sandbox / ".shim" / "T2.sh").write_text('echo "STATUS: blocked — OQ-1 open"\n')
    write_tasks(
        sandbox,
        """
### T1 — Independent branch
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`

### T2 — Blocked by OQ-1
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t2.txt`
- **done_when :** ok
- **verify :** `true`

### T3 — Depends on T2
- **depends_on :** [T2]
- **implements :** [doc]
- **files_touched :** `t3.txt`
- **done_when :** ok
- **verify :** `true`

### CP-1 — CHECKPOINT : final
- **trigger :** auto quand [T1, T3] done
- **validator :** Owner
- **mode :** blocking
""",
    )
    approve(sandbox, "CP-1")
    r = run_orch(sandbox)
    assert r.returncode == 1
    assert state(sandbox) == {
        "T1": "done",
        "T2": "blocked",
        "T3": "skipped",
        "CP-1": "skipped",
    }
    assert any(e["event"] == "task_blocked" for e in journal_events(sandbox))

    # Resume: the Owner "resolves the OQ" (T2 scenario goes to done) — T1 does not replay
    (sandbox / ".shim" / "T2.sh").write_text('echo "STATUS: done"\n')
    r2 = run_orch(sandbox)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert state(sandbox) == {"T1": "done", "T2": "done", "T3": "done", "CP-1": "done"}
    assert (sandbox / ".shim" / "t1_count").read_text().count("x") == 1


def test_eval_gate_retry_recovers(sandbox: Path) -> None:
    # Evals red on the 1st pass; the T1 scenario "fixes" them on the 2nd attempt
    (sandbox / ".evals_fail").write_text("")
    (sandbox / ".shim" / "T1.sh").write_text(
        "echo x >> .shim/count\n"
        '[ "$(grep -c x .shim/count)" -ge 2 ] && rm -f .evals_fail\n'
        'echo "STATUS: done"\n'
    )
    write_tasks(
        sandbox,
        """
### T1 — Fixes its evals
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`
""",
    )
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    done = [e for e in journal_events(sandbox) if e["event"] == "task_done"]
    assert done and done[0]["attempts"] == 2


def test_checkpoint_reject_reopens_tasks(sandbox: Path) -> None:
    # The pre-dropped rejection is consumed first: T1 reopened with the Owner
    # comment, then the checkpoint re-presents itself and finds the approval.
    (sandbox / ".shim" / "T1.sh").write_text(
        'echo x >> .shim/t1_count\necho "STATUS: done"\n'
    )
    write_tasks(
        sandbox,
        """
### T1 — To redo once
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`

### CP-1 — CHECKPOINT : final
- **trigger :** auto quand [T1] done
- **validator :** Owner
- **mode :** blocking
""",
    )
    d = sandbox / "work" / "feat" / ".approvals"
    d.mkdir(parents=True)
    (d / "CP-1.rejected").write_text("reason=the output is not acceptable\ntasks=T1\n")
    approve(sandbox, "CP-1")  # signed token (the rejection is consumed first)
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    assert state(sandbox) == {"T1": "done", "CP-1": "done"}
    assert (sandbox / ".shim" / "t1_count").read_text().count(
        "x"
    ) == 2  # 1st run + rework
    events = journal_events(sandbox)
    assert any(e["event"] == "checkpoint_rejected" for e in events)
    assert "REJECTED" in (sandbox / "work" / "feat" / "tasks.md").read_text()


def test_eval_coverage_per_id(sandbox: Path) -> None:
    # EVAL-1 implemented but only an eval_2 is collected → incomplete coverage → failed
    collected = sandbox / "collected.txt"
    collected.write_text("tests/x.py::test_eval_2_other\n")
    write_tasks(
        sandbox,
        """
### T1 — Claims to cover EVAL-1
- **depends_on :** —
- **implements :** [EVAL-1]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`
""",
    )
    env = {"LAB_EVALS_COLLECTED_FILE": str(collected)}
    r = run_orch(sandbox, env_extra=env)
    assert r.returncode == 1
    assert state(sandbox)["T1"] == "failed"

    # Same plan, the expected eval exists → done
    collected.write_text("tests/x.py::test_eval_1_nominal\n")
    (sandbox / "work" / "feat" / ".runs" / "state.json").unlink()
    r2 = run_orch(sandbox, env_extra=env)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert state(sandbox)["T1"] == "done"


def test_lint_warns_on_spec_version_drift(sandbox: Path) -> None:
    spec = sandbox / "work" / "feat" / "spec.md"
    spec.write_text(spec.read_text().replace("version: 1.0.0", "version: 2.0.0"))
    write_tasks(
        sandbox,
        """
### T1 — A
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`
""",
    )
    tasks = sandbox / "work" / "feat" / "tasks.md"
    tasks.write_text(
        tasks.read_text().replace(
            "status: approved",
            "status: approved\nspec: ./spec.md          # version : 1.0.0",
        )
    )
    r = run_orch(sandbox, "--validate")
    assert r.returncode == 0  # warning, not error
    assert "documentation drift" in r.stdout and "v1.0.0" in r.stdout


def test_anti_gate_vide(sandbox: Path) -> None:
    # T1 implements a real ID but no eval exists (no pyproject) → failed
    write_tasks(
        sandbox,
        """
### T1 — Claims to implement INV-1 without an eval
- **depends_on :** —
- **implements :** [INV-1]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`
""",
    )
    r = run_orch(sandbox)
    assert r.returncode == 1
    assert state(sandbox)["T1"] == "failed"
    assert "FAIL" in (sandbox / "work" / "feat" / "tasks.md").read_text()


def test_anti_gate_vide_for_source_edit_without_implements(sandbox: Path) -> None:
    # finding M6: a task that touches source code (src/*.py) without implements must
    # still require evals — otherwise `just evals` green by absence lets it through.
    write_tasks(
        sandbox,
        """
### T1 — Edits source code without declaring an ID
- **depends_on :** —
- **implements :** []
- **files_touched :** `src/core.py`
- **done_when :** ok
- **verify :** `true`
""",
    )
    r = run_orch(sandbox)
    assert r.returncode == 1
    assert state(sandbox)["T1"] == "failed"


def test_eval_id_matching_rejects_substring_collisions(sandbox: Path) -> None:
    # finding M7: eval_1 must NOT match eval_10, nor a path eval_2_helpers.py.
    collected = sandbox / "collected.txt"
    collected.write_text(
        "tests/eval_1.py::test_eval_10_other\ntests/eval_2_helpers.py::test_something\n"
    )
    write_tasks(
        sandbox,
        """
### T1 — Implements EVAL-1, evals named EVAL-10 / misleading path
- **depends_on :** —
- **implements :** [EVAL-1]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`
""",
    )
    env = {"LAB_EVALS_COLLECTED_FILE": str(collected)}
    r = run_orch(sandbox, env_extra=env)
    assert r.returncode == 1
    assert state(sandbox)["T1"] == "failed"

    # correct node-id → covered → done
    collected.write_text("tests/test_eval_1_examples.py::test_eval_1_nominal\n")
    (sandbox / "work" / "feat" / ".runs" / "state.json").unlink()
    r2 = run_orch(sandbox, env_extra=env)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert state(sandbox)["T1"] == "done"


# ----------------------------------------- JS (Vitest/Playwright) eval-gate path


def test_evals_collect_recipe_used_when_present(sandbox: Path) -> None:
    # The engine delegates collection to a project `evals-collect` recipe when it
    # exists; a JS-shaped node-id (front/…::test_eval_1_…) satisfies eval_covers
    # with NO engine change. Proves the language-agnostic collection seam.
    (sandbox / "justfile").write_text(
        "evals:\n"
        "    #!/usr/bin/env bash\n"
        '    echo "[stub] evals ok"\n'
        "\n"
        "evals-collect:\n"
        '    @echo "front/eval_1.test.ts::test_eval_1_nominal"\n'
    )
    write_tasks(
        sandbox,
        """
### T1 — JS feature implementing EVAL-1
- **depends_on :** —
- **implements :** [EVAL-1]
- **files_touched :** `front/Button.tsx`
- **done_when :** ok
- **verify :** `true`
""",
    )
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    assert state(sandbox)["T1"] == "done"


def test_evals_collect_fallback_when_recipe_absent(sandbox: Path) -> None:
    # No `evals-collect` recipe (default stub) + no pyproject → the probe fails
    # closed and collection falls back to the (empty) pytest path, so a task
    # implementing a real ID with no eval is still caught. Back-compat preserved.
    write_tasks(
        sandbox,
        """
### T1 — Implements INV-1 with no eval and no evals-collect recipe
- **depends_on :** —
- **implements :** [INV-1]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`
""",
    )
    r = run_orch(sandbox)
    assert r.returncode == 1
    assert state(sandbox)["T1"] == "failed"


def test_js_source_touches_gate(sandbox: Path) -> None:
    # finding M6 extended to JS: a task touching a front/*.tsx source file WITHOUT
    # an implements must still require an eval (the touches_source hole is closed).
    write_tasks(
        sandbox,
        """
### T1 — Edits a JS/TS source file without declaring an ID
- **depends_on :** —
- **implements :** []
- **files_touched :** `front/Button.tsx`
- **done_when :** ok
- **verify :** `true`
""",
    )
    r = run_orch(sandbox)
    assert r.returncode == 1
    assert state(sandbox)["T1"] == "failed"


def test_js_eval_coverage_via_seam(sandbox: Path) -> None:
    # eval_covers is unchanged and format-agnostic: a JS node-id satisfies EVAL-1
    # coverage, and the eval_1/eval_10 collision guard still holds for JS ids.
    collected = sandbox / "collected.txt"
    collected.write_text("front/x.test.ts::test_eval_10_other\n")
    write_tasks(
        sandbox,
        """
### T1 — Implements EVAL-1, only a JS eval_10 collected
- **depends_on :** —
- **implements :** [EVAL-1]
- **files_touched :** `front/x.test.ts`
- **done_when :** ok
- **verify :** `true`
""",
    )
    env = {"LAB_EVALS_COLLECTED_FILE": str(collected)}
    r = run_orch(sandbox, env_extra=env)
    assert r.returncode == 1
    assert state(sandbox)["T1"] == "failed"

    collected.write_text("front/x.test.ts::test_eval_1_nominal\n")
    (sandbox / "work" / "feat" / ".runs" / "state.json").unlink()
    r2 = run_orch(sandbox, env_extra=env)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert state(sandbox)["T1"] == "done"


def test_corrupt_state_json_does_not_crash_resume(sandbox: Path) -> None:
    # finding L9: a truncated state.json (kill mid-write) does not crash the resume.
    (sandbox / ".shim" / "T1.sh").write_text(
        'echo x >> .shim/count\necho "STATUS: done"\n'
    )
    write_tasks(
        sandbox,
        """
### T1 — A
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`
""",
    )
    r = run_orch(sandbox)
    assert r.returncode == 0
    # Corrupt state.json
    (sandbox / "work" / "feat" / ".runs" / "state.json").write_text(
        '{"T1": "done", "cor'
    )
    r2 = run_orch(sandbox)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert "unreadable" in r2.stderr  # tolerant resume flagged
    assert state(sandbox)["T1"] == "done"


def test_concurrent_orchestrate_fails_fast(sandbox: Path) -> None:
    # finding H6: two concurrent runs on the same feature → the 2nd fails fast.
    sys.path.insert(0, str(REPO / "lab" / "engine"))
    import orchestrate

    write_tasks(
        sandbox,
        """
### T1 — A
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`
""",
    )
    feat = (sandbox / "work" / "feat").resolve()
    orchestrate.acquire_orchestrator_lock(feat)  # this process holds the lock
    try:
        r = run_orch(sandbox)  # sub-process: must fail fast
        assert r.returncode == 1
        assert "orchestrator lock" in r.stderr
    finally:
        if orchestrate._ORCH_LOCK_FD is not None:
            os.close(orchestrate._ORCH_LOCK_FD)
            orchestrate._ORCH_LOCK_FD = None
