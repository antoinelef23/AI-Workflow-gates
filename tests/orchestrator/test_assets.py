"""Raw client inputs live in work/<feature>/assets/ and are gitignored by default
(issue #26): sensitive data, the template stays generic, only the derived triplet is
committed. The brand guard already excludes assets/ (see test_brand_guard)."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _ignored(rel: str) -> bool:
    # git check-ignore -q: exit 0 if the path is ignored, 1 if not (path need not exist).
    return subprocess.run(["git", "check-ignore", "-q", rel], cwd=REPO).returncode == 0


def test_assets_are_gitignored_flat_and_nested():
    assert _ignored("work/somefeat/assets/transcript.md")
    assert _ignored("work/agent/booking/assets/slides.pptx")  # domain-nested too


def test_the_triplet_itself_stays_tracked():
    assert not _ignored("work/somefeat/spec.md")
    assert not _ignored("work/somefeat/design.md")
    assert not _ignored("work/agent/booking/tasks.md")
