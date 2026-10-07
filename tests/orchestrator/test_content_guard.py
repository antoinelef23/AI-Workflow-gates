"""Substance/form guardrail: the form may move freely, the substance changes only by
amendment (version bump). Direct tests on extract_content / diff_content + git.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "content_guard", REPO / "lab" / "engine" / "content_guard.py"
)
cg = importlib.util.module_from_spec(spec)
sys.modules["content_guard"] = cg
spec.loader.exec_module(cg)


SPEC_LIST = """---
version: 1.0.0
---
## 2. Glossary
| Term | Canonical name | Definition |
|---|---|---|
| Quote | `quote` | estimate |

## 3. Invariants
- **INV-1** — The total MUST be >= 0.
- **INV-2** — `is_estimate` MUST be True.

## 4. Behaviors
### BHV-1 — installation
- **Given** a surface > 0
- **Then** installation = surface × 45.0
"""

# SAME SUBSTANCE, different form: table instead of list, bold moved, sections reordered
SPEC_TABLE = """---
version: 1.0.0
---
## 4. Behaviors

### BHV-1 — installation
**Given** a surface > 0 **Then** installation = surface × 45.0

## 3. Invariants

| ID | Rule |
|---|---|
| INV-1 | The total MUST be >= 0. |
| INV-2 | `is_estimate` MUST be True. |

## 2. Glossary
- Quote (`quote`): estimate
"""


def test_form_change_preserves_content():
    assert cg.diff_content(SPEC_LIST, SPEC_TABLE) == {}, cg.diff_content(
        SPEC_LIST, SPEC_TABLE
    )


def test_changed_invariant_is_detected():
    altered = SPEC_LIST.replace("MUST be >= 0", "MUST be > 0")
    changed = cg.diff_content(SPEC_LIST, altered)
    assert "INV-1" in changed


def test_changed_behavior_value_is_detected():
    altered = SPEC_LIST.replace("× 45.0", "× 50.0")
    changed = cg.diff_content(SPEC_LIST, altered)
    assert "BHV-1" in changed


def test_changed_glossary_canonical_name_is_detected():
    altered = SPEC_LIST.replace("`quote`", "`devis_obj`")
    changed = cg.diff_content(SPEC_LIST, altered)
    assert any(k.startswith("GLOSS:") for k in changed)


def _git(wd, *a):
    subprocess.run(
        ["git", *a],
        cwd=wd,
        capture_output=True,
        check=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@x",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@x",
            "PATH": __import__("os").environ["PATH"],
        },
    )


def _run_guard(wd, path):
    return subprocess.run(
        [
            sys.executable,
            str(REPO / "lab" / "engine" / "content_guard.py"),
            "--git",
            path,
        ],
        cwd=wd,
        capture_output=True,
        text=True,
    )


def test_git_reformat_ok_but_content_change_blocked(tmp_path):
    wd = tmp_path / "r"
    (wd / "work").mkdir(parents=True)
    f = wd / "work" / "spec.md"
    f.write_text(SPEC_LIST)
    _git(wd, "init", "-q")
    _git(wd, "add", "-A")
    _git(wd, "commit", "-qm", "v1")

    # pure reformat (table) → substance identical → exit 0
    f.write_text(SPEC_TABLE)
    r = _run_guard(wd, "work/spec.md")
    assert r.returncode == 0, r.stdout

    # substance change WITHOUT a version bump → exit 1
    f.write_text(SPEC_LIST.replace("× 45.0", "× 50.0"))
    r = _run_guard(wd, "work/spec.md")
    assert r.returncode == 1, r.stdout
    assert "SUBSTANCE changed WITHOUT" in r.stdout

    # same change WITH a version bump (amendment) → exit 0
    f.write_text(
        SPEC_LIST.replace("× 45.0", "× 50.0").replace(
            "version: 1.0.0", "version: 1.1.0"
        )
    )
    r = _run_guard(wd, "work/spec.md")
    assert r.returncode == 0, r.stdout


# ----------------------------------------------------- M1: numbered lists


def test_numbered_list_ids_are_captured():
    # finding M1: "1. **INV-1** …" must have its ID captured in the fingerprint.
    numbered = """---
version: 1.0.0
---
## 3. Invariants
1. **INV-1** — The total MUST be >= 0.
2. **INV-2** — `is_estimate` MUST be True.
"""
    content = cg.extract_content(numbered)
    assert "INV-1" in content and "INV-2" in content


def test_bullet_to_numbered_is_form_only():
    # Reformatting bullet → number is FORM: no substance change.
    bullet = "---\nversion: 1.0.0\n---\n## Inv\n- **INV-1** — total >= 0\n"
    numbered = "---\nversion: 1.0.0\n---\n## Inv\n1. **INV-1** — total >= 0\n"
    assert cg.diff_content(bullet, numbered) == {}


def test_substance_change_in_numbered_list_is_detected():
    # The substance changes in a numbered list → detected (before M1: invisible).
    a = "---\nversion: 1.0.0\n---\n## Inv\n1. **INV-1** — total >= 0\n"
    b = "---\nversion: 1.0.0\n---\n## Inv\n1. **INV-1** — total >= 100\n"
    assert "INV-1" in cg.diff_content(a, b)


# ----------------------------------------------------- L2: operator hyphen


def test_operator_hyphen_drop_is_detected():
    # finding L2: "price - discount" → "price discount" = substance change.
    with_op = (
        "---\nversion: 1.0.0\n---\n## Inv\n- **INV-1** — cost = price - discount\n"
    )
    without = "---\nversion: 1.0.0\n---\n## Inv\n- **INV-1** — cost = price discount\n"
    assert "INV-1" in cg.diff_content(with_op, without)


def test_typographic_dash_separator_is_still_form():
    # The typographic dash "—" stays a form separator (normalized).
    a = "---\nversion: 1.0.0\n---\n## Inv\n- **INV-1** — total >= 0\n"
    b = "---\nversion: 1.0.0\n---\n## Inv\n- **INV-1**   total >= 0\n"
    assert cg.diff_content(a, b) == {}


def test_inline_id_crossref_is_not_a_definition():
    # A design.md that REFERENCES an ID inline (without defining it) stays valid: its
    # substance is not fingerprinted by that ID, and a prose reformat triggers nothing.
    a = "---\nversion: 1.0.0\n---\n# Design\nReuses the base (ADR-1: pure functions).\n"
    b = "---\nversion: 1.0.0\n---\n# Design\nBuilds on the base (ADR-1: pure functions).\n"
    assert cg.diff_content(a, b) == {}  # free prose = form


# ----------------------------------------------------- M11: --against <ref> (CI)


def test_against_ref_detects_change_vs_base(tmp_path):
    # finding M11: --against compares the working tree to an arbitrary BASE (not HEAD)
    # — it is the only useful mode in CI (on a clean checkout, tree==HEAD).
    wd = tmp_path / "r"
    (wd / "work").mkdir(parents=True)
    f = wd / "work" / "spec.md"
    f.write_text(SPEC_LIST)
    _git(wd, "init", "-q")
    _git(wd, "add", "-A")
    _git(wd, "commit", "-qm", "v1")
    _git(wd, "branch", "base")

    # same content as base → no change (the --against mode works outside HEAD)
    r = subprocess.run(
        [
            sys.executable,
            str(REPO / "lab" / "engine" / "content_guard.py"),
            "--against",
            "base",
            "work/spec.md",
        ],
        cwd=wd,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout

    # change the substance without a bump → detected vs base
    f.write_text(SPEC_LIST.replace("× 45.0", "× 99.0"))
    r = subprocess.run(
        [
            sys.executable,
            str(REPO / "lab" / "engine" / "content_guard.py"),
            "--against",
            "base",
            "work/spec.md",
        ],
        cwd=wd,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1, r.stdout
    assert "SUBSTANCE changed WITHOUT" in r.stdout


def test_ci_checks_blocks_fond_change_without_bump(tmp_path):
    # finding M11/L5: ci_checks.sh discovers the features changed vs BASE and blocks a
    # substance change without a bump; the bump unblocks it.
    import os
    import shutil

    wd = tmp_path / "r"
    wd.mkdir()
    shutil.copytree(REPO / "lab" / "engine", wd / "lab" / "engine")
    shutil.copy(REPO / "justfile", wd / "justfile")
    # pyproject.toml is for the `just validate` sub-step (plan-lint → orchestrate.py,
    # which resolves its repo root by walking up to it); content_guard/ci_checks.sh
    # themselves are cwd-relative and don't need it.
    (wd / "pyproject.toml").write_text("[project]\nname = 't'\nversion = '0'\n")
    (wd / "work" / "feat").mkdir(parents=True)
    (wd / "work" / "feat" / "spec.md").write_text(SPEC_LIST)
    # -b base: deterministic initial branch (otherwise "main" locally but "master"
    # on Ubuntu CI's git → the base would be missing and the fail-safe skip would
    # make the test pass wrongly).
    _git(wd, "init", "-q", "-b", "base")
    _git(wd, "add", "-A")
    _git(wd, "commit", "-qm", "base")
    _git(wd, "checkout", "-q", "-b", "feature")
    (wd / "work" / "feat" / "spec.md").write_text(SPEC_LIST.replace("× 45.0", "× 99.0"))
    _git(wd, "commit", "-qam", "sneaky")

    env = {**os.environ, "BASE": "base"}
    r = subprocess.run(
        ["bash", "lab/engine/ci_checks.sh"],
        cwd=wd,
        env=env,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1, r.stdout + r.stderr
    assert "work/feat" in r.stdout

    # bump → unblocks
    (wd / "work" / "feat" / "spec.md").write_text(
        SPEC_LIST.replace("× 45.0", "× 99.0").replace(
            "version: 1.0.0", "version: 1.1.0"
        )
    )
    _git(wd, "commit", "-qam", "bump")
    r2 = subprocess.run(
        ["bash", "lab/engine/ci_checks.sh"],
        cwd=wd,
        env=env,
        capture_output=True,
        text=True,
    )
    assert r2.returncode == 0, r2.stdout + r2.stderr


def test_ci_checks_detects_domain_nested_feature(tmp_path):
    # issue #25: a feature can live under an optional domain layer
    # work/<domain>/<feature>/. ci_checks must still find it (nearest ancestor with
    # spec.md), not collapse it to work/<domain>.
    import os
    import shutil

    wd = tmp_path / "r"
    wd.mkdir()
    shutil.copytree(REPO / "lab" / "engine", wd / "lab" / "engine")
    shutil.copy(REPO / "justfile", wd / "justfile")
    (wd / "pyproject.toml").write_text("[project]\nname = 't'\nversion = '0'\n")
    feat = wd / "work" / "agent" / "booking"
    feat.mkdir(parents=True)
    (feat / "spec.md").write_text(SPEC_LIST)
    _git(wd, "init", "-q", "-b", "base")
    _git(wd, "add", "-A")
    _git(wd, "commit", "-qm", "base")
    _git(wd, "checkout", "-q", "-b", "feature")
    (feat / "spec.md").write_text(SPEC_LIST.replace("× 45.0", "× 99.0"))
    _git(wd, "commit", "-qam", "sneaky")

    r = subprocess.run(
        ["bash", "lab/engine/ci_checks.sh"],
        cwd=wd,
        env={**os.environ, "BASE": "base"},
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1, r.stdout + r.stderr
    assert "work/agent/booking" in r.stdout  # the leaf, not work/agent


def test_ci_checks_guards_design_when_spec_absent(tmp_path):
    # the substance guard must not be keyed to spec.md alone: a design.md substance
    # change with no sibling spec.md (e.g. spec deleted in the same change) must still
    # be detected via the design.md member of the triplet.
    import os
    import shutil

    design = "---\nversion: 1.0.0\n---\n## Decisions\n- **ADR-1** — installation rate MUST be 45.0.\n"
    wd = tmp_path / "r"
    wd.mkdir()
    shutil.copytree(REPO / "lab" / "engine", wd / "lab" / "engine")
    shutil.copy(REPO / "justfile", wd / "justfile")
    (wd / "pyproject.toml").write_text("[project]\nname = 't'\nversion = '0'\n")
    feat = wd / "work" / "feat"
    feat.mkdir(parents=True)
    (feat / "design.md").write_text(design)  # NOTE: no spec.md in this feature
    _git(wd, "init", "-q", "-b", "base")
    _git(wd, "add", "-A")
    _git(wd, "commit", "-qm", "base")
    _git(wd, "checkout", "-q", "-b", "feature")
    (feat / "design.md").write_text(design.replace("45.0", "99.0"))
    _git(wd, "commit", "-qam", "sneaky design change")

    r = subprocess.run(
        ["bash", "lab/engine/ci_checks.sh"],
        cwd=wd,
        env={**os.environ, "BASE": "base"},
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1, r.stdout + r.stderr
    assert "work/feat" in r.stdout
