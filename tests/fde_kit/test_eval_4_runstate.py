"""EVAL-4 (BHV-4, ADR-18) — run state: git names the delivered tasks, state.json v2 the rest."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "lab" / "engine"))

import runstate  # noqa: E402

pytestmark = pytest.mark.eval


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "work" / "feat").mkdir(parents=True)
    _git(
        tmp_path, "commit", "-q", "--allow-empty", "-m", "feat(feat): T1 first [BHV-1]"
    )
    return tmp_path


def _feature(proj: Path) -> Path:
    return proj / "work" / "feat"


def _state_file(proj: Path) -> Path:
    return _feature(proj) / ".runs" / "state.json"


def _write(proj: Path, text: str) -> None:
    p = _state_file(proj)
    p.parent.mkdir(exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_eval_4_runstate_old_flat_format_read(proj: Path) -> None:
    _write(proj, json.dumps({"T2": "running", "CP-1": "done"}))
    st = runstate.load(_feature(proj), proj)
    assert st.tasks["T2"] == "running"
    assert st.tasks["CP-1"] == "done"
    assert st.is_done("T1")  # from git
    assert not st.is_done("T2")
    assert st.is_done("CP-1")


def test_eval_4_runstate_v2_round_trip(proj: Path) -> None:
    st = runstate.RunState(
        tasks={"T2": "running"},
        reopened=["T1"],
        rejections={"CP-1": 2},
        routes={"T2": {"R2": 1}},
    )
    runstate.save(_state_file(proj), st)
    raw = json.loads(_state_file(proj).read_text(encoding="utf-8"))
    assert raw["schema_version"] == 2
    again = runstate.load(_feature(proj), proj)
    assert again.tasks["T2"] == "running"
    assert again.reopened == ["T1"]
    assert again.rejections == {"CP-1": 2}
    assert again.routes == {"T2": {"R2": 1}}


def test_eval_4_runstate_truncated_file_falls_back_to_git(proj: Path) -> None:
    _write(proj, '{"schema_version": 2, "tasks": {"T2": "do')
    st = runstate.load(_feature(proj), proj)
    assert st.is_done("T1")
    assert not st.is_done("T2")  # not "everything pending": git still speaks


def test_eval_4_runstate_missing_file_uses_git(proj: Path) -> None:
    assert runstate.load(_feature(proj), proj).is_done("T1")


def test_eval_4_runstate_committed_but_reopened_is_not_done(proj: Path) -> None:
    _write(proj, json.dumps({"schema_version": 2, "tasks": {}, "reopened": ["T1"]}))
    st = runstate.load(_feature(proj), proj)
    assert not st.is_done("T1")


def test_eval_4_runstate_state_done_without_commit(proj: Path) -> None:
    _write(proj, json.dumps({"schema_version": 2, "tasks": {"T9": "done"}}))
    assert runstate.load(_feature(proj), proj).is_done("T9")


def test_eval_4_runstate_counters_preserved_across_load_save(proj: Path) -> None:
    _write(
        proj,
        json.dumps(
            {
                "schema_version": 2,
                "tasks": {},
                "reopened": [],
                "rejections": {"CP-2": 1},
                "routes": {"T3": {"R4": 1}},
            }
        ),
    )
    st = runstate.load(_feature(proj), proj)
    runstate.save(_state_file(proj), st)
    again = runstate.load(_feature(proj), proj)
    assert again.rejections == {"CP-2": 1}
    assert again.routes == {"T3": {"R4": 1}}
