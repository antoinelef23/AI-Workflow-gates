"""The kit is an instance of itself (ADR-16): its own `.lab/lab.toml` (not an eval)."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "lab" / "engine"))
import kit  # noqa: E402

PROFILES = {"solo", "squad", "regulated"}


def test_kit_lab_toml_is_tracked():
    # Tracked, or about to be (untracked but NOT git-ignored: the commit that
    # introduces it is made after verify) — never ignored.
    r = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            ".lab/lab.toml",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert ".lab/lab.toml" in r.stdout.split(), (
        "the kit's .lab/lab.toml must be tracked"
    )


def test_kit_lab_toml_pins_the_kit_version_and_a_known_profile():
    data = tomllib.loads((REPO / ".lab" / "lab.toml").read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["kit_version"] == kit.kit_version()
    assert data["profile"] in PROFILES
