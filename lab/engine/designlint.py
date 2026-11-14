#!/usr/bin/env python3
"""design-lint — exit gate of the *design* phase (spec BHV-4; design ADR-19, I-29, I-30).

Pure function ``lint(text) -> list[str]`` (one line per finding) + a CLI (rc 0/1).
Rule: every ADR whose status is not ``superseded`` has an ``Anchored on:`` line citing at
least one I-n or E-n defined in §2, OR declares « sans référence — ADR délibéré ».

Usage: designlint.py <feature-dir | design.md>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_ADR = re.compile(r"^###\s+(ADR-\w+)\b")
_DEFINED = re.compile(r"^\s*\|\s*([IE]-\d+)\s*\|", re.M)
_REF = re.compile(r"\b[IE]-\d+\b")
_STATUS = re.compile(r"\*\*Status:?\*\*:?\s*(\S+)", re.I)
_ANCHOR = re.compile(r"\*\*Anchored on:?\*\*:?\s*(.*)", re.I)
_DELIBERATE = re.compile(r"sans référence\s*[—–-]\s*(?:ADR\s+)?délibéré", re.I)


def _blocks(text: str) -> list[tuple[str, list[str]]]:
    out: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        m = _ADR.match(line)
        if m:
            out.append((m.group(1), []))
        elif out:
            out[-1][1].append(line)
    return out


def _anchor_text(body: list[str]) -> str | None:
    """The `Anchored on:` bullet, with its wrapped continuation lines."""
    for i, line in enumerate(body):
        m = _ANCHOR.search(line)
        if m:
            parts = [m.group(1)]
            for nxt in body[i + 1 :]:
                if not nxt.strip() or re.match(r"\s*[-*]\s|#", nxt):
                    break
                parts.append(nxt.strip())
            return " ".join(parts)
    return None


def lint(text: str) -> list[str]:
    defined = set(_DEFINED.findall(text))
    findings: list[str] = []
    for adr, body in _blocks(text):
        sm = next((_STATUS.search(ln) for ln in body if _STATUS.search(ln)), None)
        if sm and sm.group(1).lower().startswith("superseded"):
            continue
        anchor = _anchor_text(body)
        if anchor is None:
            findings.append(f"{adr}: no `Anchored on:` line")
        elif _DELIBERATE.search(anchor):
            continue
        elif not set(_REF.findall(anchor)) & defined:
            findings.append(
                f"{adr}: `Anchored on:` cites no I-n/E-n defined in §2"
                " (nor « sans référence — ADR délibéré »)"
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: designlint.py <feature-dir | design.md>", file=sys.stderr)
        return 2
    p = Path(args[0])
    if p.is_dir():
        p = p / "design.md"
    if not p.is_file():
        print(f"design-lint: {p} not found", file=sys.stderr)
        return 1
    findings = lint(p.read_text(encoding="utf-8"))
    for f in findings:
        print(f"{p}: {f}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
