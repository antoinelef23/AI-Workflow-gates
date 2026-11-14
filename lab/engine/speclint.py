#!/usr/bin/env python3
"""spec-lint — exit gate of the *spec* phase (spec BHV-4; design ADR-19, I-26, I-30).

Pure function ``lint(text) -> list[str]`` (one line per finding) + a CLI (rc 0/1), same
shape as plan-lint (I-29). Rules: IDs unique; every BHV and INV covered by at least one
EVAL (the *Covers* column of §7); 0 open OQ (closed = its line says « résolue »);
frontmatter ``status: validated``.

Reuses ``content_guard.extract_content`` (ID extraction) and the frontmatter reader of
``plan.parse_tasks_md`` — neither is copied.

Usage: speclint.py <feature-dir | spec.md>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from content_guard import _LEADING, extract_content  # noqa: E402
from plan import parse_tasks_md  # noqa: E402

_RESOLVED = re.compile(r"résolue?s?\b", re.I)
_COVERED_ID = re.compile(r"(?:BHV|INV)-\w+")
# A *definition* line: the ID opens a bullet/heading/table row and is followed by a dash or
# a cell separator — not a wrapped line that merely starts with a mention ("BHV-2b, NG-6 ;").
_DEF_STRICT = re.compile(
    r"^\*{0,2}((?:INV|BHV|EX|EVAL|NG|OQ|ADR)-\w+)\*{0,2}\s*(?:[—–|]|$)"
)
_EVAL_ROW = re.compile(r"^\s*\|\s*EVAL-\w+\s*\|")


class _Text:
    """Duck-types the only thing parse_tasks_md needs from a Path: ``read_text``."""

    def __init__(self, text: str):
        self._text = text

    def read_text(self, encoding: str = "utf-8") -> str:
        return self._text


def frontmatter(text: str) -> dict:
    return parse_tasks_md(_Text(text))[0]  # type: ignore[arg-type]


def _duplicates(text: str) -> list[str]:
    seen: dict[str, int] = {}
    for line in text.splitlines():
        m = _DEF_STRICT.match(_LEADING.sub("", line))
        if m:
            seen[m.group(1)] = seen.get(m.group(1), 0) + 1
    return sorted(k for k, n in seen.items() if n > 1)


def _covered(text: str) -> set[str]:
    out: set[str] = set()
    for line in text.splitlines():
        if _EVAL_ROW.match(line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 4:  # ID | Type | Description | Covers | threshold
                out.update(_COVERED_ID.findall(cells[3]))
    return out


def lint(text: str) -> list[str]:
    findings: list[str] = []
    status = frontmatter(text).get("status", "")
    if status != "validated":
        findings.append(
            f"frontmatter status is {status or 'missing'!r}, expected 'validated'"
        )
    for k in _duplicates(text):
        findings.append(f"{k}: ID defined more than once (IDs must be unique)")
    content = extract_content(text)
    covered = _covered(text)
    for k in sorted(content):
        if re.match(r"(?:BHV|INV)-", k) and k not in covered:
            findings.append(f"{k}: not covered by any EVAL (Covers column of §7)")
        if k.startswith("OQ-") and not _RESOLVED.search(content[k]):
            findings.append(f"{k}: open question (no « résolue » on its line)")
    return findings


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: speclint.py <feature-dir | spec.md>", file=sys.stderr)
        return 2
    p = Path(args[0])
    if p.is_dir():
        p = p / "spec.md"
    if not p.is_file():
        print(f"spec-lint: {p} not found", file=sys.stderr)
        return 1
    findings = lint(p.read_text(encoding="utf-8"))
    for f in findings:
        print(f"{p}: {f}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
