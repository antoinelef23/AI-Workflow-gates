"""EVAL-4 — `gate` is non-mutating (BHV-4, INV-4, ADR-5)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


@pytest.mark.eval
def test_eval_4_gate_depends_on_lint_check():
    if not shutil.which("just"):
        pytest.skip("just not installed")
    r = _run(
        ["just", "--justfile", "justfile", "--dump", "--dump-format", "json"], ROOT
    )
    assert r.returncode == 0, r.stderr
    gate = json.loads(r.stdout)["recipes"]["gate"]
    deps = [d["recipe"] for d in gate["dependencies"]]
    assert "lint-check" in deps
    assert "lint" not in deps


@pytest.mark.eval
def test_eval_4_eval_models_comment_is_positional():
    for line in (ROOT / "justfile").read_text().splitlines():
        if line.startswith("#") and "just eval-models" in line:
            after = line.split("just eval-models", 1)[1].split("|")[0]
            assert "=" not in after, line


@pytest.mark.eval
def test_eval_4_seeded_drift_fails_and_leaves_tree_unchanged(tmp_path):
    if not (shutil.which("just") and shutil.which("uv")):
        pytest.skip("just/uv not installed")
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "pyproject.toml").write_text(
        '[project]\nname = "tiny"\nversion = "0"\nrequires-python = ">=3.12"\n'
    )
    (proj / "mod.py").write_text("x   =   1\n")  # format drift
    # tiny justfile reusing the kit's real lint / lint-check recipes
    jf = (ROOT / "justfile").read_text()
    start = jf.index("# Dev lint (mutating)")
    end = jf.index("test:\n")
    (proj / "justfile").write_text(jf[start:end] + "gate: lint-check\n    @echo ok\n")
    _run(["uv", "lock"], proj)  # uv.lock tracked: running uv must not dirty the tree
    _run(["git", "init", "-q"], proj)
    _run(["git", "add", "-A"], proj)
    _run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "seed"],
        proj,
    )
    content = (proj / "mod.py").read_text()

    r = _run(["just", "gate"], proj)
    assert r.returncode != 0, r.stdout + r.stderr
    assert _run(["git", "status", "--porcelain"], proj).stdout == ""
    assert (proj / "mod.py").read_text() == content
