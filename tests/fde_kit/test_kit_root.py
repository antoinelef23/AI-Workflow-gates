"""T1 — kit root + kit version + `lab` CLI (design ADR-5, ADR-1; spec INV-7)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
from importlib import metadata
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ENGINE = REPO / "lab" / "engine"
sys.path.insert(0, str(ENGINE))

import kit  # noqa: E402


def _fake_kit(tmp: Path, marker: bool = True) -> Path:
    """tmp/lab/engine/kit.py layout: parents[2] of the file is tmp."""
    (tmp / "lab" / "engine").mkdir(parents=True)
    if marker:
        (tmp / "lab" / "models").mkdir(parents=True)
        (tmp / "lab" / "models" / "registry.toml").write_text("")
    return tmp / "lab" / "engine" / "kit.py"


def _pyproject_version() -> str:
    return tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["version"]


def _env_without_lab_root() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k != "LAB_ROOT"}


# ---- root resolution -------------------------------------------------------


def test_lab_root_env_wins_without_marker(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_ROOT", str(tmp_path))
    assert kit.kit_root() == tmp_path


def test_marker_resolution_from_file_location(tmp_path, monkeypatch):
    monkeypatch.delenv("LAB_ROOT", raising=False)
    fake = _fake_kit(tmp_path)
    assert kit.kit_root(here=fake) == tmp_path.resolve()


def test_missing_marker_is_rc1_with_explicit_message(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("LAB_ROOT", raising=False)
    fake = _fake_kit(tmp_path, marker=False)
    with pytest.raises(SystemExit) as e:
        kit.kit_root(here=fake)
    assert e.value.code == 1
    err = capsys.readouterr().err
    assert "lab/models/registry.toml" in err and "LAB_ROOT" in err


def test_live_root_is_the_checkout(monkeypatch):
    monkeypatch.delenv("LAB_ROOT", raising=False)
    assert kit.kit_root() == REPO


def test_no_pyproject_walk_up(tmp_path, monkeypatch):
    # ADR-5: a pyproject.toml higher up must NOT be picked (site-packages case)
    monkeypatch.delenv("LAB_ROOT", raising=False)
    (tmp_path / "pyproject.toml").write_text("")
    deep = tmp_path / "a" / "b"
    (deep / "lab" / "engine").mkdir(parents=True)
    with pytest.raises(SystemExit):
        kit.kit_root(here=deep / "lab" / "engine" / "kit.py")


def test_live_modules_resolve_root_through_kit():
    r = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, 'lab/engine'); "
            "import orchestrate, eval_models, kit; "
            "assert orchestrate.ROOT == eval_models.ROOT == kit.kit_root(); "
            "print(orchestrate.ROOT)",
        ],
        capture_output=True,
        text=True,
        cwd=REPO,
        env=_env_without_lab_root(),
    )
    assert r.returncode == 0, r.stderr
    assert Path(r.stdout.strip()) == REPO


# ---- version ---------------------------------------------------------------


def test_version_matches_pyproject():
    assert kit.kit_version() == _pyproject_version()


def test_version_falls_back_to_pyproject_in_checkout(monkeypatch):
    def boom(_name):
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(kit.metadata, "version", boom)
    monkeypatch.delenv("LAB_ROOT", raising=False)
    assert kit.kit_version() == _pyproject_version()


def test_version_without_any_source_is_rc1(tmp_path, monkeypatch):
    def boom(_name):
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(kit.metadata, "version", boom)
    monkeypatch.setenv("LAB_ROOT", str(tmp_path))
    with pytest.raises(SystemExit) as e:
        kit.kit_version()
    assert e.value.code == 1


# ---- CLI -------------------------------------------------------------------


def _run_cli(*args):
    return subprocess.run(
        [sys.executable, str(ENGINE / "cli.py"), *args],
        capture_output=True,
        text=True,
        env=_env_without_lab_root(),
        cwd=REPO,
    )


def test_cli_version():
    r = _run_cli("version")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == _pyproject_version()


def test_cli_run_and_validate_relay_every_argument(monkeypatch):
    import cli

    calls: list[list[str]] = []

    class FakeOrch:
        @staticmethod
        def main() -> int:
            calls.append(list(sys.argv[1:]))
            return 7

    monkeypatch.setattr(cli, "_orchestrate", lambda: FakeOrch)
    assert cli.main(["run", "work/f", "--project", "p", "--dry-run"]) == 7
    assert calls[-1] == ["work/f", "--project", "p", "--dry-run"]
    assert cli.main(["validate", "work/f", "--project", "p"]) == 7
    assert calls[-1] == ["work/f", "--project", "p", "--validate"]


def test_cli_validate_real_orchestrator_on_kit_feature():
    r = _run_cli("validate", "work/fde-kit")
    assert r.returncode == 0, r.stdout + r.stderr


def test_cli_unknown_subcommand_is_nonzero():
    assert _run_cli("nope").returncode != 0


# ---- shell scripts work from an installed (non-git) kit --------------------


def _installed_kit(tmp: Path) -> Path:
    site = tmp / "site-packages"
    shutil.copytree(
        ENGINE, site / "lab" / "engine", ignore=shutil.ignore_patterns("__pycache__")
    )
    (site / "lab" / "models").mkdir(parents=True)
    shutil.copy(REPO / "lab/models/registry.toml", site / "lab/models/registry.toml")
    return site


def test_approve_and_reject_scripts_work_without_git(tmp_path):
    site = _installed_kit(tmp_path)
    feat = tmp_path / "proj" / "work" / "f"
    feat.mkdir(parents=True)
    env = _env_without_lab_root()
    env["GIT_CEILING_DIRECTORIES"] = str(tmp_path)
    r = subprocess.run(
        ["bash", str(site / "lab/engine/approve.sh"), "CP-1", str(feat)],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert list((feat / ".approvals").glob("CP-1*"))
    r = subprocess.run(
        ["bash", str(site / "lab/engine/reject.sh"), "CP-2", str(feat), "why"],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert (feat / ".approvals" / "CP-2.rejected").exists()


def test_scripts_fail_with_message_when_root_unresolvable(tmp_path):
    bad = tmp_path / "lab" / "engine"
    shutil.copytree(ENGINE, bad, ignore=shutil.ignore_patterns("__pycache__"))
    for script in ("approve.sh", "reject.sh"):
        r = subprocess.run(
            ["bash", str(bad / script), "CP-1", str(tmp_path / "f"), "why"],
            capture_output=True,
            text=True,
            env=_env_without_lab_root(),
        )
        assert r.returncode != 0
        assert "registry.toml" in r.stderr


# ---- packaging -------------------------------------------------------------


def test_pyproject_packaging():
    p = tomllib.loads((REPO / "pyproject.toml").read_text())
    assert p["project"]["name"] == "fde-kit"
    assert "devis" not in p["project"]["description"].lower()
    assert p["project"]["version"] == "0.1.0"
    assert p["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == ["lab"]
    assert p["project"]["scripts"]["lab"].startswith("lab.engine.cli")
    assert p["tool"]["pytest"]["ini_options"]["pythonpath"] == ["src"]
