"""EVAL-8 — the kit packages only the engine; the demos live under examples/ (INV-9).

Spec §7 EVAL-8, design ADR-9, tasks T9. Deterministic, no network (the wheel is built
offline from the uv cache). Tracked-ness is asserted on `git ls-files`, never on the
filesystem: untracked `__pycache__` may linger after the move.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "lab" / "engine"))

import brand_guard  # noqa: E402
import kit  # noqa: E402

EXAMPLES = ("devis", "booking")
pytestmark = pytest.mark.eval


def _tracked() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    )
    return out.stdout.splitlines()


def _kit_version() -> str:
    return tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["version"]


def _recipe_deps(recipe: str) -> list[str]:
    """Dependencies of a justfile recipe (the `recipe: a b c` header line)."""
    text = (REPO / "justfile").read_text(encoding="utf-8")
    m = re.search(rf"^{re.escape(recipe)}\s*([^:\n]*):([^\n]*)$", text, re.MULTILINE)
    assert m, f"recipe {recipe!r} not found in the kit justfile"
    return m.group(2).split()


def test_eval_8_wheel_contains_only_the_engine(tmp_path: Path):
    uv = shutil.which("uv")
    assert uv, "uv is required to build the wheel"
    r = subprocess.run(
        [uv, "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    wheels = list(tmp_path.glob("*.whl"))
    assert len(wheels) == 1, wheels
    names = zipfile.ZipFile(wheels[0]).namelist()
    payload = [n for n in names if ".dist-info/" not in n]
    assert payload, "empty wheel"
    assert all(n.startswith("lab/") for n in payload), [
        n for n in payload if not n.startswith("lab/")
    ]
    assert "lab/plugin/.claude-plugin/plugin.json" in names
    assert "lab/models/registry.toml" in names
    # I-18: no demo module in the wheel
    for n in payload:
        parts = n.split("/")
        assert not {"devis", "booking"} & set(parts), n


def test_eval_8_demo_code_is_tracked_under_examples_only():
    tracked = _tracked()
    old_roots = (
        "src/",
        "tests/devis_calc/",
        "tests/devis_cli/",
        "tests/devis_export/",
        "tests/devis_format/",
        "tests/test_smoke.py",
        "tests/booking_core/",
        "tests/booking_evals/",
        "work/devis-pose/",
        "work/export-devis/",
        "work/salle-booking/",
        "docs/export-notes.md",
        "docs/export-usage.md",
    )
    leftovers = [f for f in tracked if f.startswith(old_roots)]
    assert not leftovers, leftovers

    expected = (
        "examples/devis/src/devis/calc.py",
        "examples/devis/work/devis-pose/spec.md",
        "examples/devis/work/devis-pose/tasks.md",
        "examples/devis/work/export-devis/spec.md",
        "examples/devis/tests/devis_calc/test_evals.py",
        "examples/devis/tests/test_smoke.py",
        "examples/booking/src/booking/model.py",
        "examples/booking/work/salle-booking/spec.md",
        "examples/booking/work/salle-booking/design.md",
        "examples/booking/work/salle-booking/tasks.md",
        "examples/booking/tests/booking_evals/test_eval_1_examples.py",
    )
    missing = [f for f in expected if f not in tracked]
    assert not missing, missing


def test_eval_8_kit_work_holds_only_sdlc_rework_and_fde_kit():
    features = {
        f.split("/")[1]
        for f in _tracked()
        if f.startswith("work/") and f.count("/") >= 2
    }
    assert features == {"sdlc-rework", "fde-kit"}, features


@pytest.mark.parametrize("name", EXAMPLES)
def test_eval_8_example_is_a_pinned_standalone_instance(name: str):
    tracked = set(_tracked())
    for f in ("pyproject.toml", "uv.lock", "justfile", ".lab/lab.toml"):
        assert f"examples/{name}/{f}" in tracked, f"examples/{name}/{f} not tracked"
    cfg = tomllib.loads(
        (REPO / "examples" / name / ".lab" / "lab.toml").read_text(encoding="utf-8")
    )
    # INV-7: a kit bump must re-pin the examples explicitly
    assert cfg["kit_version"] == _kit_version() == kit.kit_version()


def test_eval_8_gate_ci_depends_on_examples_gate():
    assert "examples-gate" in _recipe_deps("gate-ci")
    # ADR-9: wired into gate-ci only, not the local gate
    assert "examples-gate" not in _recipe_deps("gate")
    text = (REPO / "justfile").read_text(encoding="utf-8")
    body = text.split("examples-gate:", 1)[1]
    assert "examples/*/" in body
    assert "uv sync --locked" in body
    assert "just evals" in body


def test_eval_8_brand_scope_covers_examples_and_excludes_assets():
    assert brand_guard.in_scope("examples/devis/work/devis-pose/spec.md")
    assert brand_guard.in_scope("examples/booking/src/booking/model.py")
    assert not brand_guard.in_scope("examples/devis/work/f/assets/transcript.md")
    assert not brand_guard.in_scope("work/fde-kit/spec.md")
    assert not brand_guard.in_scope("assets/raw.txt")


def test_eval_8_gitignore_covers_assets_in_nested_work_dirs():
    lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    rules = [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
    assert "**/work/**/assets/" in rules
    assert "work/**/assets/" not in rules


def test_eval_8_transitional_bits_are_gone():
    cfg = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    assert "pythonpath" not in cfg["tool"]["pytest"]["ini_options"]
    golden = (REPO / "tests" / "golden" / "test_oracle_integrity.py").read_text(
        encoding="utf-8"
    )
    assert 'REPO / "src"' not in golden
