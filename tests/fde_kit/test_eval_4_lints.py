"""T23 — EVAL-4 (part): spec-lint and design-lint, the exit gates of the spec and design
phases (spec BHV-4; design ADR-19, I-26, I-29, I-30). One passing and one failing fixture per rule."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ENGINE = REPO / "lab" / "engine"
sys.path.insert(0, str(ENGINE))

import cli  # noqa: E402
import designlint  # noqa: E402
import speclint  # noqa: E402

pytestmark = pytest.mark.eval


def _spec(
    status: str = "validated",
    invs: str = "- **INV-1** — a rule.",
    bhvs: str = "- **BHV-1** — a behavior.",
    evals: str = "| EVAL-1 | deterministic | d | BHV-1, INV-1 | 100% |",
    oqs: str = "- **OQ-1** — q → *(résolue le 2026-11-12 : x)*",
) -> str:
    return (
        f"---\ntype: spec\nfeature: f\nversion: 1.0.0\nstatus: {status}   # draft | validated\n---\n\n"
        f"# Spec\n\n## 3. Invariants\n\n{invs}\n\n## 4. Behaviors\n\n{bhvs}\n\n"
        "## 7. Evals — merge gate\n\n"
        "| ID | Type | Description | Covers | Success threshold |\n|---|---|---|---|---|\n"
        f"{evals}\n\n## 8. Open questions\n\n{oqs}\n"
    )


def test_eval_4_spec_clean_passes():
    assert speclint.lint(_spec()) == []


def test_eval_4_spec_duplicate_id_fails():
    f = speclint.lint(_spec(bhvs="- **BHV-1** — a.\n- **BHV-1** — b."))
    assert any("BHV-1" in x and "unique" in x for x in f)


def test_eval_4_spec_unique_ids_pass():
    assert not any("unique" in x for x in speclint.lint(_spec()))


def test_eval_4_spec_wrapped_mention_is_not_a_duplicate():
    oq = "- **OQ-1** — q → *(résolue : intégré en\n  BHV-1, INV-1)*\n  EX-1: {a: 1}"
    assert not any("unique" in x for x in speclint.lint(_spec(oqs=oq)))


def test_eval_4_spec_uncovered_bhv_fails():
    f = speclint.lint(_spec(bhvs="- **BHV-1** — a.\n- **BHV-2** — b."))
    assert any("BHV-2" in x and "EVAL" in x for x in f)
    assert not any("BHV-1 " in x for x in f)


def test_eval_4_spec_uncovered_inv_fails():
    f = speclint.lint(_spec(evals="| EVAL-1 | deterministic | d | BHV-1 | 100% |"))
    assert any("INV-1" in x and "EVAL" in x for x in f)


def test_eval_4_spec_covered_by_one_of_several_evals_passes():
    ev = (
        "| EVAL-1 | deterministic | d | BHV-1 | 100% |\n"
        "| EVAL-2 | deterministic | d | INV-1 | 100% |"
    )
    assert speclint.lint(_spec(evals=ev)) == []


def test_eval_4_spec_open_oq_fails():
    f = speclint.lint(_spec(oqs="- **OQ-1** — still open?"))
    assert any("OQ-1" in x and "open" in x for x in f)


def test_eval_4_spec_oq_resolved_on_continuation_line_passes():
    oq = "- **OQ-1** — q →\n  *(résolue le 2026-11-12 : x)*"
    assert speclint.lint(_spec(oqs=oq)) == []


def test_eval_4_spec_draft_status_fails():
    f = speclint.lint(_spec(status="draft"))
    assert any("status" in x and "validated" in x for x in f)


def test_eval_4_spec_missing_frontmatter_fails():
    f = speclint.lint("# Spec\n\n- **BHV-1** — a.\n")
    assert any("status" in x for x in f)


_DESIGN_HEAD = (
    "---\ntype: design\nstatus: validated\n---\n\n## 2. Reference repositories\n\n"
    "| ID | a | b | c | d |\n|---|---|---|---|---|\n"
    "| I-1 | x | y | z | w |\n| E-1 | x | y | z | w |\n\n## 4. ADRs\n\n"
)


def _design(adr: str) -> str:
    return _DESIGN_HEAD + adr


def test_eval_4_design_anchored_passes():
    adr = "### ADR-1 — T\n- **Status:** accepted\n- **Anchored on:** I-1, E-1.\n"
    assert designlint.lint(_design(adr)) == []


def test_eval_4_design_anchored_on_wrapped_line_passes():
    adr = "### ADR-1 — T\n- **Status:** accepted\n- **Anchored on:** ADR-0,\n  E-1 (note).\n- **Consequences:** c\n"
    assert designlint.lint(_design(adr)) == []


def test_eval_4_design_missing_anchor_fails():
    adr = "### ADR-1 — T\n- **Status:** accepted\n- **Decision:** d\n"
    f = designlint.lint(_design(adr))
    assert any("ADR-1" in x and "Anchored on" in x for x in f)


def test_eval_4_design_undefined_reference_fails():
    adr = "### ADR-1 — T\n- **Status:** accepted\n- **Anchored on:** I-99, E-98.\n"
    f = designlint.lint(_design(adr))
    assert any("ADR-1" in x for x in f)


def test_eval_4_design_deliberate_declaration_passes():
    adr = "### ADR-1 — T\n- **Status:** accepted\n- **Anchored on:** sans référence — ADR délibéré (E-21).\n"
    assert designlint.lint(_design(adr)) == []


def test_eval_4_design_superseded_is_exempt():
    adr = "### ADR-1 — T\n- **Status:** superseded by ADR-2\n- **Decision:** d\n"
    assert designlint.lint(_design(adr)) == []


def test_eval_4_cli_rc_and_one_line_per_finding(tmp_path, capsys):
    feat = tmp_path / "work" / "f"
    feat.mkdir(parents=True)
    (feat / "spec.md").write_text(_spec(status="draft", oqs="- **OQ-1** — open"))
    (feat / "design.md").write_text(_design("### ADR-1 — T\n- **Status:** accepted\n"))
    assert cli.main(["spec-lint", str(feat)]) == 1
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 2 and all(line for line in out)
    assert cli.main(["design-lint", str(feat)]) == 1
    assert len(capsys.readouterr().out.strip().splitlines()) == 1
    (feat / "spec.md").write_text(_spec())
    (feat / "design.md").write_text(
        _design("### ADR-1 — T\n- **Status:** accepted\n- **Anchored on:** I-1.\n")
    )
    assert cli.main(["spec-lint", str(feat)]) == 0
    assert cli.main(["design-lint", str(feat)]) == 0
    assert cli.main(["spec-lint", str(tmp_path / "nope")]) == 1


def test_eval_4_justfile_recipes_exist():
    jf = (REPO / "justfile").read_text()
    assert "spec-lint feature:" in jf and "design-lint feature:" in jf
