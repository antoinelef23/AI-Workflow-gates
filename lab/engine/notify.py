#!/usr/bin/env python3
"""Notifications — terminal + optional macOS banner + optional team chat. Pure
side-effect helper, no orchestrator state; silenced by LAB_NO_NOTIFY (tests/CI)."""

from __future__ import annotations

import os
import subprocess


def _gchat(msg: str) -> None:
    """Team chat notification (opt-in). No-op if LAB_GCHAT_WEBHOOK absent; never crashes.
    Lets a squad (not just the Owner at their Mac) see checkpoints/blocks."""
    url = os.environ.get("LAB_GCHAT_WEBHOOK")
    if not url:
        return
    try:
        import json as _json
        import urllib.request

        req = urllib.request.Request(
            url,
            data=_json.dumps({"text": f"[AI-Native Lab] {msg}"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def notify(msg: str) -> None:
    print(f"🔔 {msg}", flush=True)
    if os.environ.get(
        "LAB_NO_NOTIFY"
    ):  # tests / CI: no external notification (incl. _gchat)
        return
    _gchat(msg)
    try:
        # msg passed as argv (item 1 of argv), NEVER interpolated into the
        # AppleScript source: an agent-generated `reason` can no longer inject a
        # `do shell script` via osascript (finding M2).
        subprocess.run(
            [
                "osascript",
                "-e",
                "on run argv",
                "-e",
                'display notification (item 1 of argv) with title (item 2 of argv) sound name "Glass"',
                "-e",
                "end run",
                msg,
                "AI-Native Lab",
            ],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass
