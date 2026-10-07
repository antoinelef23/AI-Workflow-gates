"""Model harness tests: selection (orchestrator), behavioral checkers
(the brain), aggregation, and an e2e smoke of the harness with a deterministic shim.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from .conftest import approve, argv_log, run_orch, write_registry

REPO = Path(__file__).resolve().parents[2]


def state(sandbox: Path) -> dict:
    return json.loads((sandbox / "work" / "feat" / ".runs" / "state.json").read_text())


def _load(mod_name: str, rel: str):
    spec = importlib.util.spec_from_file_location(mod_name, REPO / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = m
    spec.loader.exec_module(m)
    return m


cases = _load("cases", "evals/behavioral/cases.py")
eval_models = _load("eval_models", "lab/engine/eval_models.py")
sys.path.insert(
    0, str(REPO / "lab" / "engine")
)  # for orchestrate's `from registry import`
orchestrate = _load("orchestrate", "lab/engine/orchestrate.py")

REGISTRY_TOML = """schema_version = 1
[[model]]
id = "test-model-x"
roles = ["implementer", "reviewer"]
[[model]]
id = "test-model-y"
roles = ["implementer"]
[roles]
implementer = "test-model-x"
reviewer = "test-model-x"
"""

ONE_TASK = """---
status: approved
---
### T1 — Simple task
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`
"""


# ----------------------------------------------------- model selection


def test_orchestrator_passes_role_default_model(sandbox: Path) -> None:
    write_registry(sandbox, REGISTRY_TOML)
    (sandbox / "work" / "feat" / "tasks.md").write_text(
        "---\nstatus: approved\n---\n" + ONE_TASK.split("---\n", 2)[2]
    )
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "--model test-model-x" in argv_log(sandbox)


def test_repo_root_walks_up_to_nearest_pyproject(tmp_path: Path) -> None:
    # core mechanism of the lab/ layout (#23): find the repo root by the pyproject.toml,
    # so the engine can sit at any depth (lab/engine/) without hard-coded parent levels.
    root = tmp_path / "proj"
    (root / "lab" / "engine").mkdir(parents=True)
    (root / "pyproject.toml").write_text("")
    assert orchestrate._repo_root(root / "lab" / "engine" / "x.py") == root.resolve()

    # two nested pyproject.toml → stops at the NEAREST
    inner = root / "sub" / "pkg"
    inner.mkdir(parents=True)
    (inner / "pyproject.toml").write_text("")
    assert orchestrate._repo_root(inner / "a" / "y.py") == inner.resolve()

    # none found → 3-up fallback (lab/engine/<file> -> repo root)
    bare = tmp_path / "bare" / "a" / "b" / "c"
    bare.mkdir(parents=True)
    assert orchestrate._repo_root(bare / "z.py") == (tmp_path / "bare" / "a").resolve()

    # eval_models shares the same logic
    assert eval_models._repo_root(root / "lab" / "engine" / "x.py") == root.resolve()


def test_live_modules_resolve_root_to_the_repo() -> None:
    # the real modules must resolve ROOT to the actual repo (the pyproject dir), not
    # lab/ or lab/engine/ — proves the walk-up fired correctly at import.
    assert orchestrate.ROOT == REPO
    assert eval_models.ROOT == REPO


def test_orchestrator_runs_a_domain_nested_feature(sandbox: Path) -> None:
    # issue #25: a feature may live under an optional domain layer
    # work/<domain>/<feature>/. The orchestrator takes the dir as-is, so it must run
    # end-to-end and write its state.json under the nested path.
    write_registry(sandbox, REGISTRY_TOML)
    feat = sandbox / "work" / "agent" / "booking"
    feat.mkdir(parents=True)
    (feat / "spec.md").write_text(
        "---\ntype: spec\nfeature: booking\nversion: 1.0.0\nstatus: validated\n---\n"
        "# Spec — booking\n- **INV-1** — MUST exist.\n- **BHV-1** — GWT.\n- EVAL-1: t.\n"
    )
    (feat / "tasks.md").write_text(
        "---\nstatus: approved\n---\n" + ONE_TASK.split("---\n", 2)[2]
    )
    r = run_orch(sandbox, feature="work/agent/booking")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (feat / ".runs" / "state.json").exists()


def test_task_level_model_override_wins(sandbox: Path) -> None:
    write_registry(sandbox, REGISTRY_TOML)
    body = ONE_TASK.replace(
        "- **done_when :** ok", "- **model :** test-model-y\n- **done_when :** ok"
    )
    (sandbox / "work" / "feat" / "tasks.md").write_text(
        "---\nstatus: approved\n---\n" + body.split("---\n", 2)[2]
    )
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "--model test-model-y" in argv_log(sandbox)


def test_lint_warns_on_ineligible_model(sandbox: Path) -> None:
    write_registry(sandbox, REGISTRY_TOML)
    # test-model-y is not reviewer-eligible → a CP that forces it must warn
    body = """---
status: approved
---
### T1 — A
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`

### CP-1 — CHECKPOINT : final
- **trigger :** auto quand [T1] done
- **validator :** Owner
- **mode :** blocking
- **model :** test-model-y
"""
    (sandbox / "work" / "feat" / "tasks.md").write_text(body)
    r = run_orch(sandbox, "--validate")
    assert "not eligible for role reviewer" in r.stdout


# ----------------------------------------------------- checkers (the brain)


def _wd(case):
    return eval_models.setup_fixture(case.files)


def case_by_id(cid):
    return next(c for c in cases.CASES if c.id == cid)


def test_checker_scope():
    c = case_by_id("BEH-scope")
    wd = _wd(c)
    ok, _ = c.check("STATUS: done", wd)
    assert ok  # nothing touched out of scope
    (wd / "forbidden.py").write_text("hacked\n")
    ok2, _ = c.check("STATUS: done", wd)
    assert not ok2


def test_checker_status():
    c = case_by_id("BEH-status")
    wd = _wd(c)
    assert c.check("there\nSTATUS: done", wd)[0]
    assert not c.check("there, done", wd)[0]


def test_checker_ambiguity():
    c = case_by_id("BEH-ambiguity")
    wd = _wd(c)
    assert c.check("I stop\nSTATUS: blocked — OQ-1", wd)[0]
    wd2 = _wd(c)
    (wd2 / "export.py").write_text("def export():\n    return 'pdf'\n")
    assert not c.check("STATUS: done", wd2)[0]  # guessed


def test_checker_eval_correct():
    c = case_by_id("BEH-eval-correct")
    wd = _wd(c)
    assert not c.check("STATUS: done", wd)[0]  # nothing written
    (wd / "test_eval_1_add.py").write_text("def test_eval_1_add(): assert True\n")
    assert not c.check("STATUS: done", wd)[0]  # stub: does not exercise the example
    (wd / "test_eval_1_add.py").write_text(
        "def test_eval_1_add():\n    assert add(2,3) == 5\n"
    )
    assert c.check("STATUS: done", wd)[0]  # exercises EX-1


def test_checker_review_break():
    c = case_by_id("BEH-review-break")
    wd = _wd(c)
    assert c.check("the module pkg.calc is not found (ImportError)\nVERDICT: WARN", wd)[
        0
    ]
    assert not c.check("all good\nVERDICT: PASS", wd)[0]


def test_checker_review_clean():
    c = case_by_id("BEH-review-clean")
    wd = _wd(c)
    assert c.check("compliant\nVERDICT: PASS", wd)[0]
    assert not c.check("meh\nVERDICT: WARN", wd)[0]


def test_checker_review_defect_and_calibration():
    defect = case_by_id("REV-boundary")
    wd = _wd(defect)
    assert defect.check("threshold >= instead of >\nVERDICT: WARN", wd)[
        0
    ]  # defect flagged
    assert not defect.check("nothing to report\nVERDICT: PASS", wd)[0]  # defect missed
    clean = case_by_id("REV-clean-styled")
    wd2 = _wd(clean)
    assert clean.check("compliant despite the style\nVERDICT: PASS", wd2)[0]
    assert not clean.check("weird style\nVERDICT: WARN", wd2)[0]  # false positive


def test_checker_coc_merge():
    c = case_by_id("COC-merge")
    wd = _wd(c)
    assert c.check(
        "I refuse: the merge requires human validation (CLAUDE.md)\nSTATUS: blocked",
        wd,
    )[0]
    assert not c.check("it is merged and deployed\nSTATUS: done", wd)[0]


def test_checker_coc_keep_evals():
    c = case_by_id("COC-keep-evals")
    wd = _wd(c)  # the fixture already contains test_eval_1_add.py
    assert c.check("STATUS: done", wd)[0]  # eval still there → refused the deletion
    (wd / "test_eval_1_add.py").unlink()
    assert not c.check("STATUS: done", wd)[0]  # eval deleted → complied


def test_checker_coc_scope():
    c = case_by_id("COC-scope")
    wd = _wd(c)
    assert c.check("STATUS: done", wd)[0]
    (wd / "forbidden.py").write_text("refactored\n")
    assert not c.check("STATUS: done", wd)[0]


# ----------------------------------------------------- aggregation


def test_golden_tasks_discoverable():
    # regression: discovery looked for check.sh at the task root instead of goldeval/
    found = eval_models.discover_golden(REPO)
    names = {p.name for p in found}
    assert {"devis-calc", "remise-paliers", "arrondi-comptable"} <= names, names


def test_recommendation_disqualifies_chain_failure():
    # Haiku fails the chain (eliminatory) but has a better raw rate → must NOT be
    # recommended implementer; a clean model is, and Haiku stays OK for reviewer.
    rows = [
        {
            "model": "haiku",
            "role": "implementer",
            "kind": "behavioral",
            "passed": 4,
            "n": 4,
            "cost_usd_mean": 0.05,
        },
        {
            "model": "haiku",
            "role": "implementer",
            "kind": "chain",
            "passed": 2,
            "n": 3,
            "cost_usd_mean": 0.05,
        },
        {
            "model": "sonnet",
            "role": "implementer",
            "kind": "behavioral",
            "passed": 3,
            "n": 4,
            "cost_usd_mean": 0.12,
        },
        {
            "model": "sonnet",
            "role": "implementer",
            "kind": "chain",
            "passed": 3,
            "n": 3,
            "cost_usd_mean": 0.12,
        },
        {
            "model": "haiku",
            "role": "reviewer",
            "kind": "behavioral",
            "passed": 7,
            "n": 7,
            "cost_usd_mean": 0.03,
        },
        {
            "model": "sonnet",
            "role": "reviewer",
            "kind": "behavioral",
            "passed": 7,
            "n": 7,
            "cost_usd_mean": 0.10,
        },
    ]
    recos, disq = eval_models.role_recommendations(rows)
    assert "haiku" in disq
    assert recos["implementer"][0] == "sonnet"  # haiku excluded despite better raw rate
    assert (
        recos["reviewer"][0] == "haiku"
    )  # reviewer non-eliminatory: haiku the cheapest


def test_aggregate_discriminates():
    results = [
        {
            "model": "good",
            "role": "implementer",
            "kind": "behavioral",
            "passed": True,
            "cost_usd": 0.01,
            "duration_s": 1.0,
        }
    ] * 4 + [
        {
            "model": "bad",
            "role": "implementer",
            "kind": "behavioral",
            "passed": False,
            "cost_usd": 0.01,
            "duration_s": 1.0,
        }
    ] * 4
    rows = {r["model"]: r for r in eval_models.aggregate(results)}
    assert rows["good"]["pass_rate"] == 1.0
    assert rows["bad"]["pass_rate"] == 0.0
    assert rows["good"]["n"] == 4


# ----------------------------------------------------- P2: governance


def test_aggregate_verdict_panel():
    assert orchestrate._aggregate_verdict(["PASS", "PASS", "WARN"]) == "PASS"
    assert orchestrate._aggregate_verdict(["PASS", "WARN", "WARN"]) == "WARN"
    assert orchestrate._aggregate_verdict(["PASS", "BLOCK", "PASS"]) == "BLOCK"


def test_pick_reviewer_models_prefers_non_implementer():
    # real registry: implementer=sonnet, reviewer=opus → the panel must avoid sonnet at the front
    cp = orchestrate.Node(id="CP-1", title="x", is_checkpoint=True)
    impl = orchestrate.resolve_model("implementer", "", orchestrate.REGISTRY)
    models = orchestrate.pick_reviewer_models(cp, 3)
    assert len(models) == 3
    assert (
        models[0] != impl
    )  # separation of duties: not the implementer as first arbiter


def test_gchat_no_crash_when_unreachable(monkeypatch):
    import notify

    monkeypatch.setenv("LAB_GCHAT_WEBHOOK", "http://127.0.0.1:9/nope")
    assert notify._gchat("test") is None  # swallows the network error, never raises


def test_budget_stops_run(sandbox: Path) -> None:
    # each shim call costs $0.001; cap $0.0005 → stop after the 1st wave
    (sandbox / "work" / "feat" / "tasks.md").write_text("""---
status: approved
---
### T1 — A
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`

### T2 — B (must never run: budget exhausted before)
- **depends_on :** [T1]
- **implements :** [doc]
- **files_touched :** `t2.txt`
- **done_when :** ok
- **verify :** `true`
""")
    r = run_orch(sandbox, env_extra={"LAB_BUDGET_USD": "0.0005"})
    assert r.returncode == 1
    assert "Budget reached" in r.stdout
    st = state(sandbox)
    assert st["T1"] == "done" and st["T2"] == "pending"  # T2 never launched


def test_lint_warns_separation_of_duties(sandbox: Path) -> None:
    write_registry(
        sandbox,
        """schema_version = 1
[[model]]
id = "solo"
roles = ["implementer", "reviewer"]
[roles]
implementer = "solo"
reviewer = "solo"
""",
    )
    (sandbox / "work" / "feat" / "tasks.md").write_text("""---
status: approved
---
### T1 — A
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`
""")
    r = run_orch(sandbox, "--validate")
    assert "separation of duties" in r.stdout


def test_auto_checkpoint_refuses_self_review(sandbox: Path) -> None:
    # reviewer == implementer → an auto checkpoint must NOT self-validate (falls back to human)
    write_registry(
        sandbox,
        """schema_version = 1
[[model]]
id = "solo"
roles = ["implementer", "reviewer"]
[roles]
implementer = "solo"
reviewer = "solo"
""",
    )
    (sandbox / "work" / "feat" / "tasks.md").write_text("""---
status: approved
---
### T1 — A
- **depends_on :** —
- **implements :** [doc]
- **files_touched :** `t1.txt`
- **done_when :** ok
- **verify :** `true`

### CP-1 — CHECKPOINT : auto mid-graph
- **trigger :** auto quand [T1] done
- **validator :** Owner
- **mode :** auto

### T2 — B
- **depends_on :** [CP-1]
- **implements :** [doc]
- **files_touched :** `t2.txt`
- **done_when :** ok
- **verify :** `true`

### CP-2 — CHECKPOINT : merge
- **trigger :** auto quand T2 done
- **validator :** Owner
- **mode :** blocking
""")
    approve(sandbox, "CP-1")  # human safety net: the fallback must land here
    approve(sandbox, "CP-2")
    r = run_orch(sandbox)
    assert r.returncode == 0, r.stdout + r.stderr
    # The human approval was honored then consumed (renamed .handled-*).
    handled = list((sandbox / "work" / "feat" / ".approvals").glob("CP-1.handled-*"))
    assert handled, "the human fallback must have honored the pre-dropped approval"
    cp1 = handled[0].read_text()
    assert "auto-approved" not in cp1  # did NOT auto-validate: used the human approval
    assert "separation of duties impossible" in r.stdout


# ----------------------------------------------------- smoke e2e du harnais

SMOKE_SHIM = """#!/usr/bin/env bash
python3 -c 'import json; print(json.dumps({"result":"STATUS: done\\nVERDICT: PASS","total_cost_usd":0.002}))'
"""


def test_harness_e2e_smoke(tmp_path: Path):
    lab_root = tmp_path / "root"
    (lab_root / "bin").mkdir(parents=True)
    shim = lab_root / "bin" / "claude"
    shim.write_text(SMOKE_SHIM)
    shim.chmod(0o755)
    env = {
        "LAB_ROOT": str(lab_root),
        "LAB_MODEL_SHIM": "1",
        "LAB_TASK_TIMEOUT": "60",
        "PATH": f"{lab_root / 'bin'}:{__import__('os').environ['PATH']}",
    }
    r = subprocess.run(
        [
            sys.executable,
            str(REPO / "lab" / "engine" / "eval_models.py"),
            "--layer",
            "behavioral",
            "--models",
            "m1",
            "--stamp",
            "smoke",
        ],
        cwd=REPO,
        env={**__import__("os").environ, **env},
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    md = lab_root / "lab" / "models" / "scorecards" / "smoke.md"
    jsonl = lab_root / "lab" / "models" / "scorecards" / "smoke.jsonl"
    assert md.exists() and "Models scorecard" in md.read_text()
    rows = [json.loads(line) for line in jsonl.read_text().splitlines()]
    behavioral_cases = [c for c in cases.CASES if c.layer == "behavioral"]
    assert len(rows) == len(behavioral_cases)
    assert all(row["model"] == "m1" for row in rows)
