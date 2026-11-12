#!/usr/bin/env bash
# SessionStart hook — injects the portable hard rules into the session context (BHV-2b, ADR-3).
set -euo pipefail
cat "${CLAUDE_PLUGIN_ROOT}/rules/hard-rules.md"
