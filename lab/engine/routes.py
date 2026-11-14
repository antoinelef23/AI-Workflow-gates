"""One classifier for failure signals (design ADR-20, spec BHV-5/BHV-5c).

``classify`` is a pure function and the ONLY place that picks a route. Structured grammar of
the implementer's last line: ``STATUS: done`` | ``STATUS: blocked — <OQ|ADR|scope>: <reason>``.
A ``blocked`` without a recognized category is ``human`` — never automatic (BHV-5c).
"""

from __future__ import annotations

import re

# Default modes (spec BHV-5 table); the effective policy may override R1..R7 (I-39).
DEFAULT_MODES = {
    "R1": "auto",
    "R2": "proposal",
    "R3": "human",
    "R4": "proposal",
    "R5": "proposal",
    "R6": "auto",
    "R7": "auto",
}
BLOCKED_CATEGORY_ROUTE = {"oq": "R3", "adr": "R4", "scope": "R5"}

_STATUS_RE = re.compile(r"STATUS:[ \t]*(done|blocked)([^\n]*)", re.I)
_CATEGORY_RE = re.compile(r"^[ \t]*[—–-]+[ \t]*(OQ|ADR|scope)[ \t]*:[ \t]*(.*)$", re.I)


def parse_status(text: str) -> tuple[str | None, str]:
    """Last ``STATUS:`` line of ``text`` → (``done``|``blocked``|None, remainder)."""
    matches = _STATUS_RE.findall(text or "")
    if not matches:
        return None, ""
    verdict, rest = matches[-1]
    return verdict.lower(), rest


def classify(signal: dict) -> tuple[str | None, str]:
    """``signal`` → ``(route, detail)``; route ∈ R1..R7 | ``human`` | None (nothing to route).

    Signals: ``verify_red`` (attempt, max_attempts) · ``status`` (text) ·
    ``panel_block`` (cp_mode) · ``reject``.
    """
    kind = signal.get("kind")
    if kind == "verify_red":
        if int(signal["attempt"]) < int(signal["max_attempts"]):
            return "R1", "red before the last attempt"
        return "R2", "red on the last attempt"
    if kind == "status":
        verdict, rest = parse_status(signal.get("text", ""))
        if verdict == "done":
            return None, ""
        if verdict is None:
            return "human", "no STATUS line"
        m = _CATEGORY_RE.match(rest)
        if not m:
            return "human", rest.strip(" —–-:") or "unspecified reason"
        return BLOCKED_CATEGORY_ROUTE[m.group(1).lower()], m.group(2).strip()
    if kind == "panel_block":
        if signal.get("cp_mode") == "auto":
            return "R6", "panel BLOCK on an auto checkpoint"
        return "human", "panel BLOCK on a non-auto checkpoint"
    if kind == "reject":
        return "R7", "signed Owner rejection"
    return "human", f"unclassifiable signal {kind!r}"


def route_mode(route: str, policy: dict | None) -> str:
    """Mode applied to ``route`` from the effective policy; ``human`` is always human."""
    if route not in DEFAULT_MODES:
        return "human"
    if policy:
        entry = policy.get(f"routes.{route}")
        if entry:
            return entry[0]
    return DEFAULT_MODES[route]
