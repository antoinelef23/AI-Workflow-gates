"""`lab` CLI — entry point of the fde-kit package (design ADR-1, §5).

Subcommands: ``version``, ``run`` and ``validate`` (pure relays to orchestrate.py, every
argument passed through). ``init`` arrives with T2.

The engine uses flat imports (``from registry import …``): this shim puts its own directory
on ``sys.path`` first, so it works both as ``python lab/engine/cli.py`` and as the installed
``lab.engine.cli:main`` entry point (pattern of eval_models.py, I-14).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kit import kit_version  # noqa: E402

USAGE = "usage: lab {version | run <feature> [args…] | validate <feature> [args…]}"


def _orchestrate():
    import orchestrate

    return orchestrate


def _relay(args: list[str]) -> int:
    orch = _orchestrate()
    sys.argv = ["orchestrate.py", *args]
    return orch.main()


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(USAGE, file=sys.stderr if not args else sys.stdout)
        return 2 if not args else 0
    cmd, rest = args[0], args[1:]
    if cmd == "version":
        print(kit_version())
        return 0
    if cmd == "run":
        return _relay(rest)
    if cmd == "validate":
        return _relay([*rest, "--validate"])
    print(f"lab: unknown command {cmd!r}\n{USAGE}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
