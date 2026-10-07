"""Trajectory guard (spec BHV-2, EX-2) — journal integrity + commit scope,
exercised against a real temp git repo (git history is a trajectory source)."""

from __future__ import annotations

import json
import subprocess

import pytest

import trajectory_guard

TASKS_MD = """---
type: tasks
feature: feat
status: approved
---

# Tasks — test

### T1 — implement x
- **agent :** implementer · **depends_on :** —
- **implements :** [BHV-1]
- **files_touched :** `src/x.py`, `tests/t.py`
- **prompt :** do it
- **done_when :** tests green
- **verify :** `pytest -q`
"""


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    feat = tmp_path / "work" / "feat"
    feat.mkdir(parents=True)
    (feat / "tasks.md").write_text(TASKS_MD, encoding="utf-8")
    return tmp_path


def commit(root, files: dict[str, str], subject: str):
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", subject], cwd=root, check=True)


def journal(root, lines):
    runs = root / "work" / "feat" / ".runs"
    runs.mkdir(exist_ok=True)
    (runs / "journal.jsonl").write_text(
        "\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8"
    )


OK_ATTEMPT = {"event": "task_attempt", "id": "T1", "attempt": 1, "ok": True}
DONE = {"event": "task_done", "id": "T1", "attempts": 1}


# ------------------------------------------------------------------ evals


@pytest.mark.eval
def test_clean_run_passes(repo):
    commit(repo, {"src/x.py": "x = 1\n"}, "feat(feat): T1 implement x [BHV-1]")
    journal(repo, [OK_ATTEMPT, DONE])
    assert trajectory_guard.main(["work/feat", "--root", str(repo)]) == 0


@pytest.mark.eval
def test_ex2_done_without_attempt_fails(repo, capsys):
    journal(repo, [DONE])  # EX-2: forged journal
    assert trajectory_guard.main(["work/feat", "--root", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "T1" in out and "BHV-2a" in out


@pytest.mark.eval
def test_out_of_scope_commit_fails(repo, capsys):
    commit(repo, {"src/other.py": "y = 2\n"}, "feat(feat): T1 implement x [BHV-1]")
    journal(repo, [OK_ATTEMPT, DONE])
    assert trajectory_guard.main(["work/feat", "--root", str(repo)]) == 1
    assert "BHV-2b" in capsys.readouterr().out


@pytest.mark.eval
def test_retry_loop_is_warn_not_fail(repo, capsys):
    attempts = [dict(OK_ATTEMPT, attempt=i) for i in (1, 2, 3)]
    journal(repo, [*attempts, dict(DONE, attempts=3)])
    assert trajectory_guard.main(["work/feat", "--root", str(repo)]) == 0  # BHV-2c
    assert "retry-loop" in capsys.readouterr().out


@pytest.mark.eval
def test_no_journal_is_not_a_failure(repo, capsys):
    assert trajectory_guard.main(["work/feat", "--root", str(repo)]) == 0  # INV-4
    assert "nothing to check" in capsys.readouterr().out


# ------------------------------------------------------------------ unit


def test_feature_dir_itself_is_in_scope(repo):
    # tasks.md/spec.md edits land in every scoped commit by design
    commit(
        repo,
        {"src/x.py": "x = 1\n", "work/feat/spec.md": "amended\n"},
        "feat(feat): T1 implement x [BHV-1]",
    )
    journal(repo, [OK_ATTEMPT, DONE])
    assert trajectory_guard.main(["work/feat", "--root", str(repo)]) == 0


def test_task_failed_is_warn(repo, capsys):
    journal(repo, [OK_ATTEMPT, {"event": "task_failed", "id": "T1"}])
    assert trajectory_guard.main(["work/feat", "--root", str(repo)]) == 0
    assert "task_failed" in capsys.readouterr().out


def test_unknown_commit_node_is_warn(repo, capsys):
    commit(repo, {"src/x.py": "x = 1\n"}, "feat(feat): T9 ghost task [auto]")
    journal(repo, [OK_ATTEMPT, DONE])
    assert trajectory_guard.main(["work/feat", "--root", str(repo)]) == 0
    assert "T9" in capsys.readouterr().out
