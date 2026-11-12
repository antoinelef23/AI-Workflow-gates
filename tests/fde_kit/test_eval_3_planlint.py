"""T19 — EVAL-3 (part): plan-lint applies the plan-time safety keys
(spec BHV-3, INV-5; design ADR-14, I-21). One case per key, `regulated` (error) vs `solo` (accepted)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ENGINE = REPO / "lab" / "engine"
sys.path.insert(0, str(ENGINE))

import policy  # noqa: E402
from plan import Node  # noqa: E402
from planlint import validate  # noqa: E402

pytestmark = pytest.mark.eval


class _NoRegistry:
    models: dict = {}


def _pol(profile: str) -> dict:
    return policy.effective_policy(
        {"schema_version": 1, "kit_version": "x", "profile": profile}
    )


def _task(nid: str, deps: list[str] | None = None, status: str = "pending") -> Node:
    return Node(
        nid,
        f"Task {nid}",
        False,
        list(deps or []),
        prompt="p",
        implements=["EVAL-3"],
        files=[f"src/{nid}.py"],
        verify="true",
        done_when="ok",
        status=status,
    )


def _cp(nid: str, deps: list[str], mode: str = "blocking", reviewers: int = 1) -> Node:
    return Node(
        nid, f"Checkpoint {nid}", True, list(deps), mode=mode, reviewers=reviewers
    )


def _lint(nodes: list[Node], pol: dict | None, done: set[str] | None = None):
    with tempfile.TemporaryDirectory() as d:
        feat = Path(d)
        (feat / "spec.md").write_text("# spec\nEVAL-3\n", encoding="utf-8")
        return validate(feat, {}, nodes, _NoRegistry(), done=done, policy=pol)


def _final_cp_plan(mode: str = "blocking", reviewers: int = 1) -> list[Node]:
    # T1 → CP-1 (intermediate, parametrised) → T2 → CP-2 (final, blocking)
    return [
        _task("T1"),
        _cp("CP-1", ["T1"], mode, reviewers),
        _task("T2", ["CP-1"]),
        _cp("CP-2", ["T2"]),
    ]


# ------------------------------------------------------ auto_checkpoints_allowed


def test_eval_3_auto_checkpoint_regulated_error():
    errors, _ = _lint(_final_cp_plan(mode="auto"), _pol("regulated"))
    assert any("CP-1" in e and "auto" in e for e in errors), errors


def test_eval_3_auto_checkpoint_solo_accepted():
    errors, _ = _lint(_final_cp_plan(mode="auto"), _pol("solo"))
    assert errors == []


# ------------------------------------------------------------------ min_reviewers


def test_eval_3_min_reviewers_regulated_error():
    errors, _ = _lint(_final_cp_plan(reviewers=1), _pol("regulated"))
    assert any("CP-1" in e and "reviewers" in e for e in errors), errors


def test_eval_3_min_reviewers_regulated_two_accepted():
    nodes = [
        _task("T1"),
        _cp("CP-1", ["T1"], reviewers=2),
        _task("T2", ["CP-1"]),
        _cp("CP-2", ["T2"], reviewers=2),
    ]
    errors, _ = _lint(nodes, _pol("regulated"))
    assert errors == []


def test_eval_3_min_reviewers_solo_accepted():
    errors, _ = _lint(_final_cp_plan(reviewers=1), _pol("solo"))
    assert errors == []


# ---------------------------------------------------- max_tasks_between_checkpoints


def _chain(n: int, prefix_dep: list[str] | None = None) -> list[Node]:
    nodes, prev = [], list(prefix_dep or [])
    for i in range(1, n + 1):
        nodes.append(_task(f"T{i}", prev))
        prev = [f"T{i}"]
    return nodes


def _chain_plan(n: int) -> list[Node]:
    return [*_chain(n), _cp("CP-1", [f"T{n}"], reviewers=2)]


def test_eval_3_max_tasks_regulated_error_names_path():
    errors, _ = _lint(_chain_plan(4), _pol("regulated"))  # limit 3
    hit = [e for e in errors if "T1" in e and "T4" in e and "3" in e]
    assert hit, errors


def test_eval_3_max_tasks_regulated_at_limit_accepted():
    errors, _ = _lint(_chain_plan(3), _pol("regulated"))
    assert errors == []


def test_eval_3_max_tasks_solo_accepted():
    errors, _ = _lint(_chain_plan(8), _pol("solo"))  # limit 8
    assert errors == []
    errors, _ = _lint(_chain_plan(9), _pol("solo"))
    assert any("T9" in e for e in errors), errors


def test_eval_3_max_tasks_between_two_checkpoints_error():
    nodes = [
        _task("T1"),
        _cp("CP-1", ["T1"], reviewers=2),
        *[
            _task(f"T{i}", ["CP-1"] if i == 2 else [f"T{i - 1}"]) for i in range(2, 6)
        ],  # T2..T5 = 4 tasks after CP-1
        _cp("CP-2", ["T5"], reviewers=2),
    ]
    errors, _ = _lint(nodes, _pol("regulated"))
    assert any("T2" in e and "T5" in e for e in errors), errors


def test_eval_3_max_tasks_parallel_branches_not_summed():
    # 2 parallel branches of 2 tasks each: longest path = 2 ≤ 3, even if 4 tasks total.
    nodes = [
        _task("T1"),
        _task("T2", ["T1"]),
        _task("T3"),
        _task("T4", ["T3"]),
        _cp("CP-1", ["T2", "T4"], reviewers=2),
    ]
    errors, _ = _lint(nodes, _pol("regulated"))
    assert errors == []


def test_eval_3_done_tasks_not_relinted():
    errors, _ = _lint(_chain_plan(4), _pol("regulated"), done={"T1", "T2"})
    assert errors == []


# ------------------------------------------------------------------------- INV-5


@pytest.mark.parametrize("profile", ["solo", "squad", "regulated"])
def test_eval_3_inv5_final_cp_never_auto(profile: str):
    nodes = [_task("T1"), _cp("CP-1", ["T1"], mode="auto", reviewers=2)]
    errors, _ = _lint(nodes, _pol(profile))
    assert any("final/merge checkpoint cannot be mode auto" in e for e in errors), (
        profile,
        errors,
    )


def test_eval_3_inv5_holds_without_policy_and_with_solo_override():
    nodes = [_task("T1"), _cp("CP-1", ["T1"], mode="auto")]
    errors, _ = _lint(nodes, None)
    assert any("merge" in e for e in errors)
    # Even a policy that allows auto checkpoints and lax everything: still an error.
    lax = _pol("solo")
    errors, _ = _lint(nodes, lax)
    assert any("merge" in e for e in errors)


# ------------------------------------------------------------- policy is None


def test_eval_3_no_policy_unchanged():
    errors, _ = _lint(_final_cp_plan(mode="auto"), None)
    assert errors == []
    errors, _ = _lint(_chain_plan(9), None)
    assert errors == []
