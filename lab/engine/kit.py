"""Kit root and kit version — the ONE place that resolves them (design ADR-5, I-14).

Root = ``LAB_ROOT`` if set (test seam), else ``parents[2]`` of this file when it holds the
marker ``lab/models/registry.toml`` (true in a checkout and in ``site-packages``), else rc 1.
No walk-up to a ``pyproject.toml``: from ``site-packages`` that would land outside the kit.

Also usable from shell scripts: ``python3 kit.py root`` / ``python3 kit.py version``.
"""

from __future__ import annotations

import os
import sys
import tomllib
from importlib import metadata
from pathlib import Path

MARKER = Path("lab") / "models" / "registry.toml"
DIST_NAME = "fde-kit"


def _die(msg: str) -> "SystemExit":
    print(f"[kit] {msg}", file=sys.stderr)
    return SystemExit(1)


def kit_root(here: Path | None = None, honor_env: bool = True) -> Path:
    """Kit root. ``here`` = location of this file (tests only). ``honor_env=False`` returns
    the location of the kit CODE, ignoring ``LAB_ROOT`` (which may point at test data)."""
    env = os.environ.get("LAB_ROOT") if honor_env else None
    if env:
        return Path(env)
    root = (here or Path(__file__)).resolve().parents[2]
    if (root / MARKER).is_file():
        return root
    raise _die(
        f"cannot locate the kit root: {root} lacks the marker {MARKER.as_posix()} "
        "(broken install?) — set LAB_ROOT to the kit directory"
    )


def kit_version() -> str:
    """Kit version: installed metadata, else ``pyproject.toml`` of a checkout."""
    try:
        return metadata.version(DIST_NAME)
    except metadata.PackageNotFoundError:
        pass
    pyproject = kit_root() / "pyproject.toml"
    try:
        return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"][
            "version"
        ]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        raise _die(
            f"cannot determine the kit version: {DIST_NAME} is not installed and "
            f"{pyproject} has no [project].version"
        ) from None


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "root":
        print(kit_root())
    elif cmd == "version":
        print(kit_version())
    else:
        print("usage: kit.py root|version", file=sys.stderr)
        raise SystemExit(2)
