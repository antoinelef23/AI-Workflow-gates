"""Status line: surfaces the most-recently-touched orchestrator run. Discovery must
be depth-agnostic — work/<feature>/ and work/<domain>/<feature>/ alike (issue #25)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SL = REPO / ".claude" / "statusline.py"
spec = importlib.util.spec_from_file_location("statusline", SL)
sl = importlib.util.module_from_spec(spec)
sys.modules["statusline"] = sl
spec.loader.exec_module(sl)


def _state(proj: Path, rel: str, obj: str) -> None:
    d = proj / "work" / rel / ".runs"
    d.mkdir(parents=True, exist_ok=True)
    (d / "state.json").write_text(obj)


def test_latest_run_flat_feature(tmp_path):
    _state(tmp_path, "feat", '{"T1": "done"}')
    feature, st = sl._latest_run(tmp_path)
    assert feature == "feat"
    assert st == {"T1": "done"}


def test_latest_run_domain_nested_feature(tmp_path):
    _state(tmp_path, "agent/booking", '{"T1": "running"}')
    feature, st = sl._latest_run(tmp_path)
    assert feature == "agent/booking"
    assert st == {"T1": "running"}


def test_latest_run_none_when_no_run(tmp_path):
    (tmp_path / "work").mkdir()
    assert sl._latest_run(tmp_path) is None


def test_run_segment_echoes_label_and_spotlights_urgent_node():
    # _run_segment only echoes the label + spotlights the urgent node — it is depth-
    # agnostic. The nested PATH DERIVATION is covered by test_latest_run_domain_nested.
    seg = sl._run_segment("agent/booking", {"T1": "done", "T2": "running"})
    assert "agent/booking" in seg
    assert "T2" in seg  # running node spotlighted
