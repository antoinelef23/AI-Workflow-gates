"""EVAL-5 — the budget message names where the cap comes from (BHV-5; EX-3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.orchestrator.conftest import run_orch

pytest_plugins = ["tests.orchestrator.conftest"]

PLAN = """---
status: approved
---
### T1 — A
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`

### T2 — B (never runs: the budget is spent before)
- **depends_on :** [T1]
- **implements :** [doc]
- **files_touched :** `t2.txt`
- **done_when :** ok
- **verify :** `true`
"""


def _setup(sb: Path, overrides: str) -> None:
    (sb / "work" / "feat" / "tasks.md").write_text(PLAN)
    lab_toml = sb / ".lab" / "lab.toml"
    lab_toml.write_text(lab_toml.read_text() + overrides)
    shim = sb / "bin" / "claude"  # every agent call now costs $5.12
    shim.write_text(shim.read_text().replace("0.001", "5.12"))


@pytest.mark.eval
def test_eval_5_message_names_the_policy_override(
    sandbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LAB_BUDGET_USD", raising=False)
    _setup(sandbox, "\n[overrides]\nbudget_usd = 5\n")
    r = run_orch(sandbox)
    assert r.returncode == 1, r.stdout + r.stderr
    assert (
        "⛔ Budget reached: $5.12 ≥ $5.00 (budget_usd, override) — stopping before the next wave."
        in r.stdout
    )


@pytest.mark.eval
def test_eval_5_message_names_the_env_var_when_set(sandbox: Path) -> None:
    _setup(sandbox, "\n[overrides]\nbudget_usd = 50\n")
    r = run_orch(sandbox, env_extra={"LAB_BUDGET_USD": "5"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert (
        "⛔ Budget reached: $5.12 ≥ $5.00 (LAB_BUDGET_USD) — stopping before the next wave."
        in r.stdout
    )
