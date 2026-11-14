"""EVAL-5 (BHV-5 R3, INV-3, INV-10, EX-3) — the ENGINE writes the OQ of a blocked task."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests.orchestrator.conftest import (  # noqa: F401  (sandbox = fixture)
    run_orch,
    sandbox,
)

import orchestrate  # noqa: E402  (lab/engine is put on sys.path by the conftest)

pytestmark = pytest.mark.eval

FM = "---\ntype: tasks\nfeature: feat\nstatus: approved\n---\n\n# Tasks — feat\n"
PLAN = """
### T2 — Rounding
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t2.txt`
- **done_when :** ok
- **verify :** `true`

### T5 — Downstream task
- **depends_on :** [T2]
- **implements :** [doc]
- **files_touched :** `t5.txt`
- **done_when :** ok
- **verify :** `true`

### CP-1 — CHECKPOINT : merge
- **trigger :** auto when [T5] done
- **validator :** Owner
- **mode :** blocking
- **depends_on :** [T5]
"""


def test_eval_5_r3_engine_writes_the_oq(sandbox: Path) -> None:  # noqa: F811
    feat = sandbox / "work" / "feat"
    (feat / "tasks.md").write_text(FM + PLAN)
    (sandbox / ".shim" / "T2.sh").write_text(
        "echo 'OQ: arrondi TVA par ligne ou par total ?'\n"
        "echo 'STATUS: blocked — OQ: arrondi TVA par ligne ou par total ?'\n"
    )
    subprocess.run(["git", "add", "-A"], cwd=sandbox, check=True)
    subprocess.run(["git", "commit", "-qm", "plan"], cwd=sandbox, check=True)
    spec_before = (feat / "spec.md").read_bytes()

    r = run_orch(sandbox)
    assert r.returncode == 1, r.stdout + r.stderr
    state = json.loads((feat / ".runs" / "state.json").read_text())["tasks"]
    assert state["T2"] == "blocked"
    oq = feat / ".runs" / "T2-OQ.md"
    assert oq.is_file()
    body = oq.read_text()
    assert "arrondi TVA par ligne ou par total ?" in body
    assert "T2" in body and "T5" in body and "CP-1" in body
    assert (feat / "spec.md").read_bytes() == spec_before  # INV-10
    assert (
        "T2 blocked on an open question — Owner amendment expected; "
        "impacted: [T2, T5, CP-1]"
    ) in r.stdout


def test_eval_5_r3_prompt_no_longer_points_at_spec_section_8() -> None:
    node = orchestrate.Node("T1", "x", False)
    prompt = orchestrate._build_base_prompt(node, orchestrate.PROJECT / "work" / "f")
    assert "§8" not in prompt
    assert "STATUS: blocked — OQ:" in prompt
