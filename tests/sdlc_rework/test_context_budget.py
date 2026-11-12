"""Context budget (spec BHV-3) — soft gate: measures always, fails only once
[context] max_static_tokens is declared in the registry."""

from __future__ import annotations

import pytest

import context_budget

REGISTRY = """schema_version = 1

[[model]]
id = "m1"
label = "M1"
family = "test"
tier = "fast"
roles = ["planner"]
context_profile = "{profile}"

{context}
[roles]
planner = "m1"
"""


def make_root(
    tmp_path, *, profile="base", context="", claude_chars=400, with_claude=True
):
    if with_claude:
        (tmp_path / "CLAUDE.md").write_text("x" * claude_chars, encoding="utf-8")
    rules = tmp_path / "lab" / "plugin" / "rules"
    rules.mkdir(parents=True)
    (rules / "hard-rules.md").write_text("r" * 400, encoding="utf-8")
    agents = tmp_path / "lab" / "plugin" / "agents"
    agents.mkdir(parents=True)
    (agents / "planner.md").write_text("y" * 400, encoding="utf-8")
    models = tmp_path / "lab" / "models"
    (models / "profiles").mkdir(parents=True)
    (models / "profiles" / "verbose.md").write_text("z" * 400, encoding="utf-8")
    (models / "registry.toml").write_text(
        REGISTRY.format(profile=profile, context=context), encoding="utf-8"
    )
    return tmp_path


# ------------------------------------------------------------------ evals


@pytest.mark.eval
def test_no_declared_budget_measures_only(tmp_path, capsys):
    root = make_root(tmp_path)
    assert context_budget.main(["--root", str(root)]) == 0
    assert "measuring only" in capsys.readouterr().out


@pytest.mark.eval
def test_declared_budget_exceeded_fails(tmp_path, capsys):
    root = make_root(tmp_path, context="[context]\nmax_static_tokens = 10\n")
    assert context_budget.main(["--root", str(root)]) == 1
    assert "exceeded" in capsys.readouterr().out


@pytest.mark.eval
def test_declared_budget_respected_passes(tmp_path):
    root = make_root(tmp_path, context="[context]\nmax_static_tokens = 10000\n")
    assert context_budget.main(["--root", str(root)]) == 0


# ------------------------------------------------------------------ unit


def test_base_profile_not_counted_verbose_is(tmp_path):
    # base: rules(100) + CLAUDE.md(100) + planner.md(100) = 300
    root = make_root(tmp_path)
    rows, _ = context_budget.measure(root)
    assert rows["planner"]["tokens"] == 300

    (tmp_path / "v").mkdir()
    root2 = make_root(tmp_path / "v", profile="verbose")
    rows2, _ = context_budget.measure(root2)
    assert rows2["planner"]["tokens"] == 400  # + verbose.md(100)


def test_rules_file_counted_and_claude_md_optional(tmp_path):
    # instance-like root: the rules file replaces CLAUDE.md in the static payload
    root = make_root(tmp_path, with_claude=False)  # rules(100) + planner.md(100)
    rows, _ = context_budget.measure(root)
    assert rows["planner"]["tokens"] == 200
    assert "CLAUDE.md" not in rows["planner"]["files"]
    assert "lab/plugin/rules/hard-rules.md" in rows["planner"]["files"]


def test_real_repo_measures_every_role():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    rows, _ = context_budget.measure(root)
    # every production role of the registry gets a measured, positive payload
    assert set(rows) == {"planner", "implementer", "reviewer", "eval-runner"}
    assert all(r["tokens"] > 0 for r in rows.values())
