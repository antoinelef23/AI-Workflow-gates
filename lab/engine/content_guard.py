#!/usr/bin/env python3
"""SUBSTANCE vs FORM guardrail for spec.md and design.md.

Principle: the **substance** (the spec's business contract, the design's technical
picture) changes ONLY by explicit human amendment (version bump). The **form** (layout,
table↔list, bold, section order, prose rewording) may evolve freely — notably so another
model understands it better — BUT without ever altering the substance.

This script makes the rule mechanical: it extracts a **substance fingerprint** robust to
form and refuses any substance change that does not come with a version bump.

The fingerprint = STRUCTURED, testable content, normalized (formatting stripped):
  - the per-ID assertions: INV / BHV / EX / EVAL / NG / OQ (spec) and ADR (design),
    with their continuation lines (Given/When/Then, example YAML, ADR decision);
  - the canonical glossary names (the code MUST use them → that's substance);
  - the KPI lines (numeric values = substance).
Free prose (intent, comments) is NOT in the fingerprint: rewording it is form.

Usage:
  content_guard.py <old.md> <new.md>              # compare two files
  content_guard.py --git work/feat/spec.md        # compare the working tree to HEAD
                                                   # exit 1 if the substance changes without a version bump
  content_guard.py --against <ref> work/feat/spec.md  # compare the working tree to <ref>
                                                   # (CI: <ref> = base branch, not HEAD)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ID = r"(?:INV|BHV|EX|EVAL|NG|OQ|ADR)-\w+"
# Includes digits / "." / ")": a numbered list "1. **INV-1** …" must also have
# its ID captured (finding M1) — otherwise the ID and its continuation lines drop
# out of the fingerprint and the substance can change without a version bump.
_LEADING = re.compile(r"^[\s#\-*|`>.)0-9]+")
_DEF = re.compile(rf"^\*{{0,2}}({ID})")
_HEAD2 = re.compile(r"^#{1,2}\s")  # ## section → reset of the ID context
_KPI = re.compile(r"KPI", re.I)
_FMT = re.compile(r"[`*_#>|]")


def _norm(s: str) -> str:
    """Normalize a line: strip markdown formatting (bold, table, bullets,
    em-dash separators) so list↔table↔prose yield the same substance."""
    s = _FMT.sub(" ", s)  # ` * _ # > |
    s = re.sub(
        r"^\s*\d+[.)]\s+", " ", s
    )  # leading numbering "1." / "2)" (M1: list↔num)
    s = re.sub(r"^\s*[-*]\s+", " ", s)  # leading list bullet
    # Only TYPOGRAPHIC dashes "—"/"–" are prose separators. The ASCII hyphen "-"
    # is kept: otherwise "end - start" ≡ "end start" would mask an operator
    # removal (finding L2).
    s = re.sub(r"\s+[—–]\s+", " ", s)  # spaced "—" / "–" separators
    return re.sub(r"\s+", " ", s).strip()


def extract_content(text: str) -> dict[str, str]:
    """Substance fingerprint: {key -> normalized text}. Robust to form.

    Known scope limit (finding L1): only the substance CARRIED BY AN ID
    (INV/BHV/EX/EVAL/NG/OQ/ADR), the glossary and the KPIs is fingerprinted.
    Normative prose WITHOUT an ID ("- X MUST be positive") is not tracked — that
    is a deliberate choice (convention: all testable substance carries an ID)."""
    content: dict[str, list[str]] = {}
    current: str | None = None
    in_glossary = False

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = _LEADING.sub("", line)
        m = _DEF.match(stripped)
        if m:  # a line that INTRODUCES an ID (def, not inline mention)
            current = m.group(1)
            content.setdefault(current, []).append(_norm(line))
            continue
        if _HEAD2.match(line):  # section boundary
            current = None
            in_glossary = (
                "gloss—" in line.lower()
                or "glossary" in line.lower()
                or "glossaire" in line.lower()
            )
            continue
        # continuation lines attached to the current ID (Given/When/Then, YAML, ADR…)
        if current and line.strip():
            content[current].append(_norm(line))
            continue
        # glossary: canonical names (code), whatever the form (table OR list)
        if in_glossary:
            for c in re.findall(r"`([^`]+)`", line):
                content[f"GLOSS:{c}"] = [c]
        # KPI lines outside an ID
        if _KPI.search(line):
            content.setdefault("KPI", []).append(_norm(line))

    return {k: " ".join(v) for k, v in content.items()}


def diff_content(old: str, new: str) -> dict[str, tuple[str, str]]:
    """Returns {key -> (before, after)} for each modified/added/removed substance element."""
    a, b = extract_content(old), extract_content(new)
    changed: dict[str, tuple[str, str]] = {}
    for k in sorted(set(a) | set(b)):
        if a.get(k, "") != b.get(k, ""):
            changed[k] = (a.get(k, "∅"), b.get(k, "∅"))
    return changed


def _version(text: str) -> str | None:
    m = re.search(r"^version:\s*([\w.\-]+)", text, re.M)
    return m.group(1) if m else None


def _focus(a: str, b: str, ctx: int = 25, tail: int = 70) -> tuple[str, str]:
    """Frame the preview around the FIRST divergence (otherwise a diff far
    into a long line stays invisible — both sides look identical)."""
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    start = max(0, i - ctx)
    pre = "…" if start > 0 else ""

    def cut(s: str) -> str:
        end = i + tail
        return pre + s[start:end] + ("…" if end < len(s) else "")

    return cut(a), cut(b)


def main() -> int:
    # NB (finding L3): --git compares the working tree to HEAD — it is an ADVISORY
    # guardrail (pre-commit / pre-review), not a barrier at commit time. The bytes
    # already in HEAD were never guarded. For a hard barrier, hook into pre-commit
    # on the indexed content.
    args = sys.argv[1:]
    if args and args[0] == "--git":
        path = args[1]
        new = Path(path).read_text(encoding="utf-8")
        try:
            rel = (
                subprocess.run(
                    ["git", "ls-files", "--full-name", path],
                    capture_output=True,
                    text=True,
                ).stdout.strip()
                or path
            )
            old = subprocess.run(
                ["git", "show", f"HEAD:{rel}"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        except subprocess.CalledProcessError:
            print(f"✅ {path}: new file (no HEAD version to compare)")
            return 0
    elif len(args) == 3 and args[0] == "--against":
        # CI (finding M11): compare the working tree to an arbitrary base (the
        # base branch), not HEAD — otherwise on a clean checkout tree==HEAD and the
        # guardrail would always pass trivially.
        ref, path = args[1], args[2]
        new = Path(path).read_text(encoding="utf-8")
        rel = (
            subprocess.run(
                ["git", "ls-files", "--full-name", path],
                capture_output=True,
                text=True,
            ).stdout.strip()
            or path
        )
        shown = subprocess.run(
            ["git", "show", f"{ref}:{rel}"], capture_output=True, text=True
        )
        if shown.returncode != 0:
            print(f"✅ {path}: absent from {ref} (new file) — nothing to compare.")
            return 0
        old = shown.stdout
    elif len(args) == 2:
        old = Path(args[0]).read_text(encoding="utf-8")
        new = Path(args[1]).read_text(encoding="utf-8")
        path = args[1]
    else:
        print(__doc__)
        return 2

    changed = diff_content(old, new)
    if not changed:
        print(f"✅ {path}: substance identical — the form may evolve freely.")
        return 0

    bumped = _version(old) != _version(new)
    print(
        f"{'✅' if bumped else '⛔'} {path}: {len(changed)} substance element(s) modified:"
    )
    for k, (av, ap) in changed.items():
        fa, fb = _focus(av, ap)
        print(f"  • {k}\n      before: {fa}\n      after: {fb}")
    if bumped:
        print(
            f"→ version bumped ({_version(old)} → {_version(new)}): amendment assumed, OK."
        )
        return 0
    print(
        "→ ⛔ the SUBSTANCE changed WITHOUT a version bump. A reformat must only touch the FORM.\n"
        "  If intentional (business/technical amendment), bump `version:` + changelog\n"
        "  (separate commit). Otherwise, restore the substance and keep only the formatting."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
