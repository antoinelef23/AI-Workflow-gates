"""Brand/proper-noun guard: the lab stays generic. Detection is a word-boundary,
case-insensitive denylist; the scope EXCLUDES usage a posteriori (work/, **/assets/)
and the detector's own config. No real brand names live in this test — synthetic
terms only (the e2e drives a temp denylist via LAB_BRAND_DENYLIST).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GUARD = REPO / "lab" / "engine" / "brand_guard.py"
spec = importlib.util.spec_from_file_location("brand_guard", GUARD)
bg = importlib.util.module_from_spec(spec)
sys.modules["brand_guard"] = bg
spec.loader.exec_module(bg)


# --------------------------------------------------------------- unit: denylist


def test_load_denylist_skips_comments_and_blanks(tmp_path):
    d = tmp_path / "deny.txt"
    d.write_text("# header\n\nAcmeCorp\n  Globex  \n# trailing comment\n")
    terms = bg.load_denylist(d)
    assert [t for t, _ in terms] == ["AcmeCorp", "Globex"]


def test_missing_denylist_is_empty(tmp_path):
    assert bg.load_denylist(tmp_path / "nope.txt") == []


def test_word_boundary_no_substring_false_positive(tmp_path):
    d = tmp_path / "deny.txt"
    d.write_text("Zorp\n")  # synthetic term — this file is itself in scope of the guard
    (_, pat) = bg.load_denylist(d)[0]
    assert pat.search("we use Zorp here")
    assert pat.search("(Zorp)")
    assert not pat.search("Zorpon")  # longer word -> not a hit
    assert not pat.search("xZorp")


def test_case_insensitive(tmp_path):
    d = tmp_path / "deny.txt"
    d.write_text("AcmeCorp\n")
    (_, pat) = bg.load_denylist(d)[0]
    assert pat.search("acmecorp") and pat.search("ACMECORP")


def test_multiword_term(tmp_path):
    d = tmp_path / "deny.txt"
    d.write_text("Initech Systems\n")
    (_, pat) = bg.load_denylist(d)[0]
    assert pat.search("built for Initech Systems today")


def test_multiword_separator_variants_are_caught(tmp_path):
    # a space in the denylist must catch hyphen / double-space / nbsp variants —
    # otherwise the hyphenated (domain-name) form of a two-word brand slips past.
    d = tmp_path / "deny.txt"
    d.write_text("Initech Systems\n")
    (_, pat) = bg.load_denylist(d)[0]
    for variant in (
        "Initech-Systems",
        "Initech  Systems",  # double space
        "Initech Systems",  # nbsp
        "Initech–Systems",  # en dash
    ):
        assert pat.search(bg._normalize(variant)), variant
    assert not pat.search(bg._normalize("Initechsystems"))  # no separator -> not a hit


def test_normalize_folds_accents_and_strips_invisibles():
    # NFD accent (e + combining acute) folds to NFC — synthetic word, no real brand
    nfd = "Cafe\u0301"
    assert bg._normalize(nfd) == "Caf\u00e9"
    # zero-width space (U+200B) and soft hyphen (U+00AD) are removed
    assert bg._normalize("A\u200bB\u00adC") == "ABC"


def test_scan_catches_evasions(tmp_path):
    d = tmp_path / "deny.txt"
    d.write_text("Initech Systems\nAcme\n")
    terms = bg.load_denylist(d)
    f = tmp_path / "doc.md"
    # hyphenated multiword, NFD accent-free here, and a zero-width-split single word
    f.write_text("Ship to Initech-Systems.\nA​cme is the client.\n")
    hits = bg.scan_file(str(f), terms)
    found = {t for _, t, _ in hits}
    assert "Initech Systems" in found  # hyphen variant caught
    assert "Acme" in found  # zero-width split caught


# --------------------------------------------------------------- unit: scope


def test_in_scope_excludes_usage_and_config_and_data():
    assert bg.in_scope("lab/templates/spec.md")
    assert bg.in_scope("docs/how-to/x.md")
    assert bg.in_scope("CLAUDE.md")
    # excluded: usage a posteriori
    assert not bg.in_scope("work/feat/spec.md")
    assert not bg.in_scope("assets/raw.txt")
    assert not bg.in_scope("work/feat/assets/transcript.md")
    # excluded: detector config + data/binary
    assert not bg.in_scope("lab/engine/brand_denylist.txt")
    assert not bg.in_scope("lab/models/scorecards/x.jsonl")
    assert not bg.in_scope("sbom.json")
    assert not bg.in_scope("uv.lock")


# ----------------------------------------------- footgun guard: real denylist


def test_real_denylist_has_no_lab_vocabulary():
    """The spec-ID prefixes are vocabulary, not brands — listing one would flag the
    whole repo. This locks that mistake out."""
    terms = {t.upper() for t, _ in bg.load_denylist(bg.DENYLIST_PATH)}
    vocab = {"INV", "BHV", "EX", "EVAL", "NG", "OQ", "ADR", "CP"}
    assert not (terms & vocab), (
        f"lab vocabulary leaked into the denylist: {terms & vocab}"
    )


# --------------------------------------------------------------- e2e (subprocess)


def _git(wd, *a):
    subprocess.run(["git", *a], cwd=wd, capture_output=True, check=True)


def _repo(tmp_path):
    wd = tmp_path / "r"
    wd.mkdir()
    _git(wd, "init", "-q")
    _git(wd, "config", "user.email", "t@x")
    _git(wd, "config", "user.name", "t")
    deny = tmp_path / "deny.txt"  # OUTSIDE the repo, so it is never scanned
    deny.write_text("AcmeCorp\nGlobex\n")
    return wd, deny


def _run(wd, deny, *flags):
    return subprocess.run(
        [sys.executable, str(GUARD), *flags],
        cwd=wd,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "LAB_BRAND_DENYLIST": str(deny)},
    )


def test_all_flags_lab_content_but_not_usage(tmp_path):
    wd, deny = _repo(tmp_path)
    (wd / "lab").mkdir()
    (wd / "lab" / "x.md").write_text("This mentions AcmeCorp in the framework.\n")
    (wd / "work").mkdir()
    (wd / "work" / "y.md").write_text("A real feature for Globex (allowed here).\n")
    (wd / "work" / "feat").mkdir()
    (wd / "work" / "feat" / "assets").mkdir()
    (wd / "work" / "feat" / "assets" / "z.md").write_text("Globex transcript.\n")
    for f in ["lab/x.md", "work/y.md", "work/feat/assets/z.md"]:
        _git(wd, "add", f)
    _git(wd, "commit", "-qm", "x")

    r = _run(wd, deny, "--all")
    assert r.returncode == 1, r.stdout
    assert "lab/x.md" in r.stdout
    assert "AcmeCorp" in r.stdout
    assert "work/y.md" not in r.stdout  # usage a posteriori excluded
    assert "assets/z.md" not in r.stdout  # nested assets excluded


def test_all_clean_passes(tmp_path):
    wd, deny = _repo(tmp_path)
    (wd / "lab").mkdir()
    (wd / "lab" / "x.md").write_text("A perfectly generic framework doc.\n")
    _git(wd, "add", "lab/x.md")
    _git(wd, "commit", "-qm", "x")
    r = _run(wd, deny, "--all")
    assert r.returncode == 0, r.stdout
    assert "clean" in r.stdout


def test_staged_only(tmp_path):
    wd, deny = _repo(tmp_path)
    (wd / "lab").mkdir()
    (wd / "lab" / "x.md").write_text("intro AcmeCorp\n")
    # not staged yet -> nothing to scan
    r0 = _run(wd, deny, "--staged")
    assert r0.returncode == 0, r0.stdout
    _git(wd, "add", "lab/x.md")
    r1 = _run(wd, deny, "--staged")
    assert r1.returncode == 1, r1.stdout
    assert "lab/x.md" in r1.stdout


# ------------------------------------------- meta: the real tree stays generic


def test_real_repo_tree_is_clean():
    """The de-branding holds: scanning the actual committed tree with the real
    denylist finds nothing. If this fails, a brand leaked into the lab."""
    r = subprocess.run(
        [sys.executable, str(GUARD), "--all"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout
