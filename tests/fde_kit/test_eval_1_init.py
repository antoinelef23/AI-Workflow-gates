"""T2 — EVAL-1: `lab init` (spec BHV-1, 1b..1e, INV-7, INV-8, EX-4; design ADR-7, ADR-8)."""

from __future__ import annotations

import json
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

import kit  # noqa: E402

pytestmark = pytest.mark.eval

EX4_FILES = {
    ".lab/lab.toml",
    "justfile",
    "work/README.md",
    "work/_templates/spec.template.md",
    "work/_templates/design.template.md",
    "work/_templates/tasks.template.md",
}


def _env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k != "LAB_ROOT"}


def _git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "inst"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    return repo


def _init(repo: Path | str, *args: str, cwd: Path | None = None):
    return subprocess.run(
        [sys.executable, str(CLI), "init", str(repo), *args],
        cwd=cwd or (repo if isinstance(repo, Path) else None),
        capture_output=True,
        text=True,
        env=_env(),
    )


def _tree(repo: Path) -> dict[str, bytes]:
    return {
        p.relative_to(repo).as_posix(): p.read_bytes()
        for p in repo.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(repo).parts
    }


def _recipes(justfile: Path) -> dict:
    out = subprocess.run(
        ["just", "--justfile", str(justfile), "--dump", "--dump-format", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)["recipes"]


def _just(repo: Path, recipe: str):
    return subprocess.run(
        [
            "just",
            "--justfile",
            str(repo / "justfile"),
            "--working-directory",
            str(repo),
            recipe,
        ],
        capture_output=True,
        text=True,
    )


# ---- EX-4 ------------------------------------------------------------------


def test_eval_1_ex4_exact_file_set(tmp_path):
    repo = _git_repo(tmp_path)
    r = subprocess.run(
        [sys.executable, str(CLI), "init", ".", "--profile", "squad"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=_env(),
    )
    assert r.returncode == 0, r.stderr
    tree = _tree(repo)
    assert set(tree) == EX4_FILES
    # one line per file, announced
    for f in EX4_FILES:
        assert any(
            line.startswith("create") and f in line for line in r.stdout.splitlines()
        ), f
    cfg = tomllib.loads(tree[".lab/lab.toml"].decode())
    assert cfg == {
        "schema_version": 1,
        "kit_version": kit.kit_version(),
        "profile": "squad",
    }


def test_eval_1_never_creates_agent_tooling(tmp_path):
    repo = _git_repo(tmp_path)
    assert _init(repo, "--profile", "regulated").returncode == 0
    for forbidden in (".claude", "CLAUDE.md", "AGENTS.md", ".github"):
        assert not (repo / forbidden).exists(), forbidden
    names = {Path(f).name for f in _tree(repo)}
    # templates must not look like a feature triplet (pre-commit / ci_checks / plan-lint)
    assert not names & {"spec.md", "design.md", "tasks.md"}


def test_eval_1_idempotent_second_run(tmp_path):
    repo = _git_repo(tmp_path)
    assert _init(repo, "--profile", "squad").returncode == 0
    before = _tree(repo)
    r = _init(repo, "--profile", "squad")
    assert r.returncode == 0
    assert "0 changement" in r.stdout
    assert not any(line.startswith("create") for line in r.stdout.splitlines())
    assert _tree(repo) == before


def test_eval_1_dry_run_writes_nothing(tmp_path):
    repo = _git_repo(tmp_path)
    r = _init(repo, "--profile", "squad", "--dry-run")
    assert r.returncode == 0
    assert _tree(repo) == {}
    assert not (repo / ".lab").exists() and not (repo / "work").exists()
    for f in EX4_FILES:
        assert f in r.stdout, f
    # after the real run, the dry-run reports nothing left to do
    assert _init(repo, "--profile", "squad").returncode == 0
    r2 = _init(repo, "--profile", "squad", "--dry-run")
    assert "0 changement" in r2.stdout


def test_eval_1_never_overwrites_existing_file(tmp_path):
    repo = _git_repo(tmp_path)
    (repo / ".lab").mkdir()
    custom = b'schema_version = 1\nkit_version = "9.9.9"\nprofile = "solo"\n'
    (repo / ".lab" / "lab.toml").write_bytes(custom)
    (repo / "work").mkdir()
    (repo / "work" / "README.md").write_bytes(b"mine\n")
    r = _init(repo, "--profile", "squad")
    assert r.returncode == 0, r.stderr
    assert (repo / ".lab" / "lab.toml").read_bytes() == custom
    assert (repo / "work" / "README.md").read_bytes() == b"mine\n"
    assert any(
        line.startswith("skip") and "lab.toml" in line for line in r.stdout.splitlines()
    )


# ---- --profile (OQ-11) ------------------------------------------------------


@pytest.mark.parametrize("extra", [[], ["--profile", "enterprise"]])
def test_eval_1_profile_required_and_validated(tmp_path, extra):
    repo = _git_repo(tmp_path)
    r = _init(repo, *extra)
    assert r.returncode == 1
    for p in ("solo", "squad", "regulated"):
        assert p in r.stderr
    assert _tree(repo) == {}


# ---- BHV-1b: non-Python instance fails closed ------------------------------


def test_eval_1_non_python_recipes_fail_closed(tmp_path):
    repo = _git_repo(tmp_path)
    assert _init(repo, "--profile", "squad").returncode == 0
    assert set(_recipes(repo / "justfile")) >= {"evals", "evals-collect"}
    for recipe in ("evals", "evals-collect"):
        r = _just(repo, recipe)
        assert r.returncode == 1, recipe
        assert "no evals configured" in r.stderr
        assert "`evals`" in r.stderr and "`evals-collect`" in r.stderr


def test_eval_1_python_instance_gets_pytest_recipes(tmp_path):
    repo = _git_repo(tmp_path)
    (repo / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "0"\n')
    assert _init(repo, "--profile", "solo").returncode == 0
    text = (repo / "justfile").read_text()
    assert "uv run pytest -q -m eval" in text
    assert "-eq 5" in text and "no eval collected" in text
    assert "--collect-only" in text
    assert "no evals configured" not in text
    assert set(_recipes(repo / "justfile")) >= {"evals", "evals-collect"}


# ---- BHV-1e: existing recipes preserved -------------------------------------


def test_eval_1_existing_evals_recipe_preserved(tmp_path):
    repo = _git_repo(tmp_path)
    original = b"default:\n    echo hi\n\nevals:\n    echo custom-evals\n"
    (repo / "justfile").write_bytes(original)
    r = _init(repo, "--profile", "squad")
    assert r.returncode == 0, r.stderr
    after = (repo / "justfile").read_bytes()
    assert after.startswith(original)  # existing bytes untouched, addition at the end
    recipes = _recipes(repo / "justfile")
    assert set(recipes) == {"default", "evals", "evals-collect"}
    assert after.count(b"\nevals:") == 1
    out = _just(repo, "evals")
    assert out.returncode == 0 and "custom-evals" in out.stdout
    assert _just(repo, "evals-collect").returncode == 1  # fail-closed model appended
    # second run: nothing left to do
    again = _init(repo, "--profile", "squad")
    assert "0 changement" in again.stdout
    assert (repo / "justfile").read_bytes() == after


def test_eval_1_both_recipes_present_justfile_untouched(tmp_path):
    repo = _git_repo(tmp_path)
    original = b"evals:\n    echo a\nevals-collect:\n    echo b"  # no trailing newline
    (repo / "justfile").write_bytes(original)
    assert _init(repo, "--profile", "squad").returncode == 0
    assert (repo / "justfile").read_bytes() == original


def test_eval_1_append_to_file_without_trailing_newline(tmp_path):
    repo = _git_repo(tmp_path)
    original = b"evals:\n    echo a"
    (repo / "justfile").write_bytes(original)
    assert _init(repo, "--profile", "squad").returncode == 0
    assert (repo / "justfile").read_bytes().startswith(original)
    assert set(_recipes(repo / "justfile")) == {"evals", "evals-collect"}


# ---- ADR-8: unparsable justfile left untouched ------------------------------


def test_eval_1_unparsable_justfile_left_untouched(tmp_path):
    repo = _git_repo(tmp_path)
    broken = b"this is {{ not a justfile\n    ???\n"
    (repo / "justfile").write_bytes(broken)
    r = _init(repo, "--profile", "squad")
    assert r.returncode == 1
    assert (repo / "justfile").read_bytes() == broken
    # nothing else written either: the plan is computed (and fails) before any write
    assert not (repo / ".lab").exists() and not (repo / "work").exists()
    r = _init(repo, "--profile", "squad", "--dry-run")
    assert r.returncode == 1


def test_eval_1_justfile_restored_when_reread_fails(tmp_path, monkeypatch):
    import lab_init

    repo = _git_repo(tmp_path)
    original = b"evals:\n    echo a\n"
    (repo / "justfile").write_bytes(original)
    real = lab_init.just_recipes
    calls = []

    def flaky(path):
        calls.append(path)
        if len(calls) >= 2:  # the re-read after the append
            raise lab_init.InitError("simulated parse failure")
        return real(path)

    monkeypatch.setattr(lab_init, "just_recipes", flaky)
    rc = lab_init.run(repo, "squad", dry_run=False)
    assert rc == 1
    assert (repo / "justfile").read_bytes() == original


# ---- reader of .lab/lab.toml (reused by T4's pre-flight) ---------------------


def test_eval_1_lab_toml_reader(tmp_path):
    import lab_init

    repo = _git_repo(tmp_path)
    with pytest.raises(lab_init.LabTomlError, match="lab.toml"):
        lab_init.read_lab_toml(repo)  # missing file: explicit error, not silent-empty
    (repo / ".lab").mkdir()
    toml = repo / ".lab" / "lab.toml"
    toml.write_text('schema_version = 2\nkit_version = "0.1.0"\nprofile = "squad"\n')
    with pytest.raises(lab_init.LabTomlError, match="schema_version"):
        lab_init.read_lab_toml(repo)
    toml.write_text('schema_version = 1\nkit_version = "0.1.0"\nprofile = "nope"\n')
    with pytest.raises(lab_init.LabTomlError, match="profile"):
        lab_init.read_lab_toml(repo)
    toml.write_text("not = [valid")
    with pytest.raises(lab_init.LabTomlError):
        lab_init.read_lab_toml(repo)
    toml.write_text('schema_version = 1\nkit_version = "0.1.0"\nprofile = "squad"\n')
    assert lab_init.read_lab_toml(repo) == {
        "schema_version": 1,
        "kit_version": "0.1.0",
        "profile": "squad",
    }
