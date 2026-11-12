"""`lab` CLI — entry point of the fde-kit package (design ADR-1, §5).

Subcommands: ``version``, ``init`` (lab_init.py), ``run`` and ``validate`` (pure relays to
orchestrate.py, every argument passed through).

The engine uses flat imports (``from registry import …``): this shim puts its own directory
on ``sys.path`` first, so it works both as ``python lab/engine/cli.py`` and as the installed
``lab.engine.cli:main`` entry point (pattern of eval_models.py, I-14).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kit import kit_version  # noqa: E402

USAGE = (
    "usage: lab {version | init <project> --profile <solo|squad|regulated> [--dry-run]"
    " | run <feature> [args…] | validate <feature> [args…]}"
)


def _orchestrate():
    import orchestrate

    return orchestrate


def _relay(args: list[str]) -> int:
    orch = _orchestrate()
    sys.argv = ["orchestrate.py", *args]
    return orch.main()


def _init(args: list[str]) -> int:
    import argparse

    import lab_init

    ap = argparse.ArgumentParser(prog="lab init", add_help=True)
    ap.add_argument("project")
    ap.add_argument("--profile", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args(args)
    return lab_init.run(Path(ns.project), ns.profile, dry_run=ns.dry_run)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(USAGE, file=sys.stderr if not args else sys.stdout)
        return 2 if not args else 0
    cmd, rest = args[0], args[1:]
    if cmd == "version":
        print(kit_version())
        return 0
    if cmd == "init":
        return _init(rest)
    if cmd == "run":
        return _relay(rest)
    if cmd == "validate":
        return _relay([*rest, "--validate"])
    print(f"lab: unknown command {cmd!r}\n{USAGE}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
