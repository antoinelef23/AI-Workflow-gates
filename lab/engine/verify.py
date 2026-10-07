#!/usr/bin/env python3
"""Verify-command policy (finding H2) — pure, no orchestrator state.

A task's `verify` is a test/build command, never a shell. It is parsed to an argv
list and run WITHOUT a shell; plan-lint rejects anything outside the allowlists or
containing shell metacharacters. This module owns that policy so it is testable on
its own and shared by both the orchestrator and plan-lint.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

# Commands allowed as a task's `verify`. Prevents an agent-generated `verify` of
# the form `pytest; curl|sh`.
VERIFY_ALLOWED = {
    "true",
    "false",
    "test",
    "[",
    "ls",
    "cat",
    "grep",
    "head",
    "tail",
    "make",
    "just",
    "uv",
    "python",
    "python3",
    "pytest",
    "ruff",
}
# Metacharacters that would only make sense via a shell — forbidden in a verify.
_SHELL_META = re.compile(r"[;&|`$><\n]")
# Env prefixes `VAR=val` allowed before a verify (finding H2, env smuggling).
# Allowlist: keys that add NO privilege beyond what the verify already does (it runs
# in-repo agent code: conftest.py, test modules). PYTHONPATH is one of them —
# `PYTHONPATH=src uv run …` is standard usage and grants no more than the
# `Bash(uv:*)/Bash(python3:*)` the agent already has.
# Refused (blocked): keys that hijack OTHER processes/shells/binaries —
# LD_PRELOAD, LD_LIBRARY_PATH, DYLD_*, BASH_ENV, ENV, PYTHONSTARTUP, PYTHONHOME, PATH —
# which would be a real escalation (RCE without a shell, outside the test scope).
VERIFY_ENV_ALLOWED = {
    "CI",
    "TZ",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "NO_COLOR",
    "PYTHONPATH",
    "PYTHONDONTWRITEBYTECODE",
    "PYTEST_ADDOPTS",
}


def parse_verify(cmd: str) -> tuple[list[str], dict[str, str]]:
    """Split a `verify` command into (argv, env_overrides) — WITHOUT a shell (finding H2).

    Handles environment prefixes `VAR=val` restricted to VERIFY_ENV_ALLOWED
    (e.g. `CI=1 …`, `PYTHONPATH=src uv run …`). Keys that hijack other
    processes/shells/binaries (LD_PRELOAD, DYLD_*, BASH_ENV, PYTHONSTARTUP, PATH…)
    are refused: that would be an RCE escalation outside the test scope.
    Raises ValueError if: shell metacharacters, unparsable (unclosed quotes),
    empty, or command outside VERIFY_ALLOWED. The caller then runs the argv
    as-is (`shell=False`), which neutralizes any chaining/injection even if this
    validation were bypassed.
    """
    if _SHELL_META.search(cmd):
        raise ValueError(
            "shell metacharacters forbidden in verify (; & | $ ` > < newline) — "
            "a verify is a single command, not a shell script"
        )
    tokens = shlex.split(cmd)  # may raise ValueError (unclosed quotes)
    env: dict[str, str] = {}
    while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
        k, _, v = tokens[0].partition("=")
        if k not in VERIFY_ENV_ALLOWED:
            raise ValueError(
                f'environment prefix "{k}=" forbidden in verify — '
                f"allowed keys: {', '.join(sorted(VERIFY_ENV_ALLOWED))}. "
                "PYTHONPATH/PYTHONSTARTUP/LD_PRELOAD/BASH_ENV… let you inject "
                "code loaded by the command (RCE without a shell)."
            )
        env[k] = v
        tokens = tokens[1:]
    if not tokens:
        raise ValueError("empty verify (after any environment prefixes)")
    prog = Path(tokens[0]).name
    if prog not in VERIFY_ALLOWED:
        raise ValueError(
            f'verify command "{tokens[0]}" outside allowlist — '
            f"allowed: {', '.join(sorted(VERIFY_ALLOWED))}"
        )
    return tokens, env
