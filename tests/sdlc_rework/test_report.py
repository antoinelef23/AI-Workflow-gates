"""Run report (spec BHV-1, EX-1) — journal aggregation and INV-4 tolerance."""

from __future__ import annotations

import json

import pytest

import journal_io
import run_report


def write_journal(feature, lines):
    runs = feature / ".runs"
    runs.mkdir(parents=True)
    (runs / "journal.jsonl").write_text(
        "\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8"
    )


EX1 = [
    {
        "event": "task_attempt",
        "id": "T1",
        "attempt": 1,
        "model": "m",
        "cost_usd": 0.10,
        "ok": True,
    },
    {"event": "task_done", "id": "T1", "attempts": 1},
    {
        "event": "task_attempt",
        "id": "T2",
        "attempt": 1,
        "model": "m",
        "cost_usd": 0.20,
        "ok": True,
    },
    {"event": "eval_fail", "id": "T2", "attempt": 1},
    {
        "event": "task_attempt",
        "id": "T2",
        "attempt": 2,
        "model": "m",
        "cost_usd": 0.15,
        "ok": True,
    },
    {"event": "task_done", "id": "T2", "attempts": 2},
]


# ------------------------------------------------------------- unit: journal_io


def test_read_events_absent_file_yields_empty(tmp_path):
    assert journal_io.read_events(tmp_path / "nope") == []  # INV-4


def test_read_events_skips_malformed_lines(tmp_path):
    runs = tmp_path / ".runs"
    runs.mkdir()
    (runs / "journal.jsonl").write_text('{"event": "task_done", "id": "T1"}\n{oops\n')
    assert len(journal_io.read_events(tmp_path)) == 1


# --------------------------------------------------------------- eval: EX-1


@pytest.mark.eval
def test_ex1_numbers_exact(tmp_path, capsys):
    feat = tmp_path / "work" / "feat"
    write_journal(feat, EX1)
    rc = run_report.main(["work/feat", "--json", "--root", str(tmp_path)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    s = out["features"]["work/feat"]
    assert s["tasks_done"] == 2  # EVAL-1 / EX-1
    assert s["first_pass_rate"] == 0.5
    assert s["mean_attempts"] == 1.5
    assert s["cost_usd"] == 0.45
    assert s["models"]["m"]["attempts"] == 3
    assert s["failures"]["eval_fail"] == {"T2": 1}  # BHV-1b clustering


@pytest.mark.eval
def test_no_journal_reports_nothing_and_passes(tmp_path, capsys):
    (tmp_path / "work").mkdir()
    rc = run_report.main(["--root", str(tmp_path)])
    assert rc == 0  # INV-4: absence of telemetry is not a failure
    assert "no journal" in capsys.readouterr().out


def test_discovery_finds_domain_nested_features(tmp_path, capsys):
    write_journal(tmp_path / "work" / "dom" / "feat", EX1[:2])
    rc = run_report.main(["--json", "--root", str(tmp_path)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert list(out["features"]) == ["work/dom/feat"]


def test_review_costs_split_from_task_costs(tmp_path, capsys):
    write_journal(
        tmp_path / "work" / "feat",
        EX1
        + [
            {
                "event": "review",
                "id": "CP-1",
                "model": "r",
                "verdict": "PASS",
                "cost_usd": 0.30,
                "ok": True,
            }
        ],
    )
    run_report.main(["work/feat", "--json", "--root", str(tmp_path)])
    s = json.loads(capsys.readouterr().out)["features"]["work/feat"]
    assert s["cost_task_usd"] == 0.45
    assert s["cost_review_usd"] == 0.30
    assert s["cost_usd"] == 0.75
