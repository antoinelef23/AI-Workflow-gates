#!/usr/bin/env python3
"""Signed approval tokens (HMAC) — prevent an agent from forging its own
checkpoint validation. The merge is human, always (CLAUDE.md, hard rules).

Threat model closed here (finding H1): an agent (Write/Edit in acceptEdits, or
Bash) that writes `feature/.approvals/<CP>` itself to self-validate. Before, the
gate reduced to `approval.exists()` — forgeable with a single `Write`.

- Without LAB_APPROVAL_SECRET: back-compatible mode. An unsigned token is accepted
  WITH a warning (forgery is NOT blocked — configure the secret).
- With LAB_APPROVAL_SECRET: a token without a valid HMAC signature is REJECTED. An
  agent therefore cannot validate itself without the secret, which the orchestrator
  removes from the sub-agents' environment (cf. orchestrate.run_claude).

Known residual (finding M4): as long as agents run on the same host WITHOUT a
sandbox, an agent with arbitrary code execution (inherent to an agent that runs
its tests) could exfiltrate the secret from the Owner's dotfiles. Full
confinement comes with the sandbox (branch ship/portable-sandbox). Here we close
the naive / per-tool forgery and bind the token to the checkpoint.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sys
from pathlib import Path

ENV_SECRET = "LAB_APPROVAL_SECRET"


def _secret() -> bytes | None:
    # An empty OR whitespace-only secret is treated as absent (zero entropy):
    # no false sense of security with LAB_APPROVAL_SECRET="   ".
    s = (os.environ.get(ENV_SECRET) or "").strip()
    return s.encode() if s else None


def _feature_id(feature: Path) -> str:
    # parent/name (e.g. work/feat) rather than the basename alone — avoids a token
    # collision between work/x and examples/x. Stable between approve.sh and the
    # orchestrator (both resolve the path before calling).
    return f"{feature.parent.name}/{feature.name}"


def _payload(feature: Path, cp_id: str) -> str:
    # Bound to the checkpoint and the feature — NOT to the tasks.md content (mutated
    # by run_log during the run, which would invalidate a legitimate token).
    # Freshness (anti-replay, finding H4) is ensured by consuming the token after
    # honoring it in the orchestrator (wait_checkpoint) + the gitignore of .approvals.
    return f"{cp_id}|{_feature_id(feature)}"


def sign(feature: Path, cp_id: str, author: str, ts: str) -> str:
    lines = [
        f"approved_by={author}",
        f"at={ts}",
        f"payload={_payload(feature, cp_id)}",
    ]
    sec = _secret()
    if sec:
        sig = hmac.new(
            sec, _payload(feature, cp_id).encode(), hashlib.sha256
        ).hexdigest()
        lines.append(f"sig={sig}")
    return "\n".join(lines) + "\n"


def _fields(content: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in content.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


def verify(feature: Path, cp_id: str, content: str) -> tuple[bool, str]:
    """(accepted, reason). Refuses an invalid signed token; accepts (with a
    warning) an unsigned token only if no secret is configured."""
    sec = _secret()
    if sec is None:
        return (
            True,
            "unsigned (LAB_APPROVAL_SECRET absent — forgery not blocked, "
            "configure the secret to harden the checkpoint)",
        )
    sig = _fields(content).get("sig")
    if not sig:
        return (
            False,
            "token without a signature while LAB_APPROVAL_SECRET is set "
            "(likely forgery by an agent)",
        )
    expected = hmac.new(
        sec, _payload(feature, cp_id).encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return (
            False,
            "invalid signature (forged token or inconsistent checkpoint/feature)",
        )
    return True, "valid signature"


def _cli(argv: list[str]) -> int:
    """Internal usage for approve.sh: approvals.py sign <CP> <feature_dir> <author>."""
    if len(argv) >= 4 and argv[0] == "sign":
        from datetime import datetime

        cp, feature_dir, author = argv[1], argv[2], argv[3]
        feature = Path(feature_dir).resolve()
        d = feature / ".approvals"
        d.mkdir(parents=True, exist_ok=True)
        (d / cp).write_text(
            sign(feature, cp, author, datetime.now().isoformat(timespec="seconds")),
            encoding="utf-8",
        )
        if _secret() is None:
            print(
                "⚠️  LAB_APPROVAL_SECRET not set: UNSIGNED token (an agent "
                "could forge it). Export the secret to harden.",
                file=sys.stderr,
            )
        return 0
    print("usage: approvals.py sign <CP> <feature_dir> <author>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
