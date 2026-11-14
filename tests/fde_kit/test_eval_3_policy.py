"""T16 — EVAL-3 (part): policy as data (spec BHV-3, 3a..3c, INV-2, INV-3, EX-1; design ADR-13)."""

from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ENGINE = REPO / "lab" / "engine"
CLI = ENGINE / "cli.py"
sys.path.insert(0, str(ENGINE))

import policy  # noqa: E402

pytestmark = pytest.mark.eval

# BHV-3 table, as written in the spec: key -> (kind, strict, solo, squad, regulated)
BHV3 = {
    "auto_checkpoints_allowed": ("safety", "false", True, True, False),
    "min_reviewers": ("safety", "up", 1, 1, 2),
    "max_tasks_between_checkpoints": ("safety", "down", 8, 5, 3),
    "sandbox_required": ("safety", "true", False, False, True),
    "allow_force": ("safety", "false", True, True, False),
    "max_task_attempts": ("free", None, 3, 3, 3),
    "max_parallel": ("free", None, 3, 3, 2),
    "max_cp_rejects": ("free", None, 2, 2, 2),
    "budget_usd": ("free", None, 0, 0, 0),
    "goldfish_min_score": ("safety", "up", None, None, None),
}


def _lab(
    profile: str, overrides: dict | None = None, routes: dict | None = None
) -> dict:
    d: dict = {"schema_version": 1, "kit_version": "x", "profile": profile}
    if overrides is not None or routes is not None:
        d["overrides"] = dict(overrides or {})
        if routes is not None:
            d["overrides"]["routes"] = routes
    return d


def test_eval_3_ex1_looser_than_floor_refused():
    with pytest.raises(policy.PolicyError) as e:
        policy.effective_policy(_lab("regulated", {"min_reviewers": 1}))
    assert str(e.value) == "min_reviewers=1 is looser than floor 'regulated' (2)"


def test_eval_3_ex1_stricter_and_free_accepted():
    eff = policy.effective_policy(
        _lab("regulated", {"min_reviewers": 3, "max_parallel": 4})
    )
    assert eff["min_reviewers"] == (3, "override")
    assert eff["max_parallel"] == (4, "override (free key)")
    assert eff["sandbox_required"] == (True, "floor")


def test_eval_3_equal_to_floor_accepted():
    eff = policy.effective_policy(_lab("regulated", {"min_reviewers": 2}))
    assert eff["min_reviewers"][0] == 2


@pytest.mark.parametrize(
    "key,bad",
    [
        ("auto_checkpoints_allowed", True),
        ("min_reviewers", 1),
        ("max_tasks_between_checkpoints", 4),
        ("sandbox_required", False),
        ("allow_force", True),
    ],
)
def test_eval_3_every_safety_key_monotone_on_regulated(key, bad):
    with pytest.raises(
        policy.PolicyError, match=f"{key}=.* is looser than floor 'regulated'"
    ):
        policy.effective_policy(_lab("regulated", {key: bad}))


def test_eval_3_profile_table_equals_bhv3():
    data = tomllib.loads((ENGINE / "policy_profiles.toml").read_text(encoding="utf-8"))
    assert data.pop("schema_version") == 1
    assert set(data) == set(BHV3)
    for key, (kind, strict, *vals) in BHV3.items():
        spec = data[key]
        assert spec["kind"] == kind, key
        assert spec.get("strict") == strict, key
        for name, v in zip(("solo", "squad", "regulated"), vals):
            assert spec.get(name) == v, (key, name)
        assert set(spec) <= {"kind", "strict", "solo", "squad", "regulated"}


@pytest.mark.parametrize("profile", ["solo", "squad", "regulated"])
def test_eval_3_floor_values_per_profile(profile):
    idx = {"solo": 2, "squad": 3, "regulated": 4}[profile]
    eff = policy.effective_policy(_lab(profile))
    assert set(eff) == set(BHV3)
    for key, row in BHV3.items():
        assert eff[key] == (row[idx], "floor"), key


def test_eval_3_goldfish_undeclared_accepts_any_override():
    assert policy.effective_policy(_lab("regulated"))["goldfish_min_score"] == (
        None,
        "floor",
    )
    eff = policy.effective_policy(_lab("regulated", {"goldfish_min_score": 0.8}))
    assert eff["goldfish_min_score"] == (0.8, "override")


def test_eval_3_unknown_key_rejected():
    with pytest.raises(policy.PolicyError, match="min_reviwers"):
        policy.effective_policy(_lab("squad", {"min_reviwers": 2}))
    with pytest.raises(policy.PolicyError, match="R9"):
        policy.effective_policy(_lab("squad", routes={"R9": "human"}))


def test_eval_3_route_r3_auto_refused_r6_human_accepted():
    for r in ("R2", "R3", "R4", "R5"):
        with pytest.raises(policy.PolicyError, match=f"{r}=auto"):
            policy.effective_policy(_lab("solo", routes={r: "auto"}))
    eff = policy.effective_policy(_lab("solo", routes={"R6": "human"}))
    assert eff["routes.R6"] == ("human", "override")
    with pytest.raises(policy.PolicyError):
        policy.effective_policy(_lab("solo", routes={"R1": "maybe"}))


def test_eval_3_no_key_concerns_the_merge():
    assert not [k for k in BHV3 if "merge" in k]
    with pytest.raises(policy.PolicyError):
        policy.effective_policy(_lab("squad", {"merge_auto": True}))


def _cli(project: Path) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "LAB_ROOT"}
    return subprocess.run(
        [sys.executable, str(CLI), "policy", "--project", str(project)],
        capture_output=True,
        text=True,
        env=env,
    )


def _write(project: Path, body: str) -> None:
    (project / ".lab").mkdir(parents=True)
    (project / ".lab" / "lab.toml").write_text(
        'schema_version = 1\nkit_version = "0.1.0"\n' + body, encoding="utf-8"
    )


def test_eval_3_cli_lists_keys_with_origin(tmp_path):
    _write(
        tmp_path,
        'profile = "regulated"\n[overrides]\nmin_reviewers = 3\nmax_parallel = 4\n'
        '[overrides.routes]\nR6 = "human"\n',
    )
    p = _cli(tmp_path)
    assert p.returncode == 0, p.stderr
    out = p.stdout
    assert "min_reviewers = 3  (override)" in out
    assert "max_parallel = 4  (override (free key))" in out
    assert "sandbox_required = true  (floor)" in out
    assert "goldfish_min_score = undeclared  (floor)" in out
    assert "routes.R6 = human" in out and "applied from iteration 3" not in out


def test_eval_3_cli_rc1_on_policy_error(tmp_path):
    _write(tmp_path, 'profile = "regulated"\n[overrides]\nmin_reviewers = 1\n')
    p = _cli(tmp_path)
    assert p.returncode == 1
    assert "min_reviewers=1 is looser than floor 'regulated' (2)" in p.stderr


# --- CP-6 delta (spec 0.7.0): equal-to-floor accepted, BHV-3d free-key bounds ---

YES_NO_STRICT = {
    "auto_checkpoints_allowed": False,
    "sandbox_required": True,
    "allow_force": False,
}


@pytest.mark.parametrize("profile", ["solo", "squad"])
@pytest.mark.parametrize("key", sorted(YES_NO_STRICT))
def test_eval_3_yes_no_safety_key_equal_to_floor_accepted(profile, key):
    floor = policy.effective_policy(_lab(profile))[key][0]
    eff = policy.effective_policy(_lab(profile, {key: floor}))
    assert eff[key] == (floor, "override")


@pytest.mark.parametrize("profile", ["solo", "squad"])
@pytest.mark.parametrize("key", sorted(YES_NO_STRICT))
def test_eval_3_yes_no_safety_key_strict_value_accepted(profile, key):
    strict = YES_NO_STRICT[key]
    assert policy.effective_policy(_lab(profile, {key: strict}))[key][0] is strict


@pytest.mark.parametrize("key", sorted(YES_NO_STRICT))
def test_eval_3_yes_no_safety_key_equal_to_regulated_floor_accepted(key):
    strict = YES_NO_STRICT[key]  # regulated floor is the strict value
    assert policy.effective_policy(_lab("regulated", {key: strict}))[key][0] is strict


@pytest.mark.parametrize("key", ["max_task_attempts", "max_parallel", "max_cp_rejects"])
@pytest.mark.parametrize("bad", [0, -1])
def test_eval_3_bhv3d_int_bounds_refused(key, bad):
    with pytest.raises(policy.PolicyError) as e:
        policy.effective_policy(_lab("solo", {key: bad}))
    msg = str(e.value)
    assert key in msg and f"={bad}" in msg and ">= 1" in msg


@pytest.mark.parametrize("key", ["max_task_attempts", "max_parallel", "max_cp_rejects"])
def test_eval_3_bhv3d_int_bound_accepted_and_non_integer_refused(key):
    assert policy.effective_policy(_lab("solo", {key: 1}))[key] == (
        1,
        "override (free key)",
    )
    with pytest.raises(policy.PolicyError, match=key):
        policy.effective_policy(_lab("solo", {key: 1.5}))


def test_eval_3_bhv3d_budget_bounds():
    for bad in (-1, -0.5):
        with pytest.raises(policy.PolicyError) as e:
            policy.effective_policy(_lab("solo", {"budget_usd": bad}))
        assert "budget_usd" in str(e.value) and f"={bad}" in str(e.value)
        assert ">= 0" in str(e.value)
    eff = policy.effective_policy(_lab("solo", {"budget_usd": 0}))
    assert eff["budget_usd"] == (0, "override (free key)")
    assert (
        policy.effective_policy(_lab("solo", {"budget_usd": 12.5}))["budget_usd"][0]
        == 12.5
    )


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_eval_3_bhv3d_budget_must_be_finite(bad):
    with pytest.raises(policy.PolicyError) as e:
        policy.effective_policy(_lab("solo", {"budget_usd": bad}))
    assert "budget_usd" in str(e.value) and "finite" in str(e.value)
