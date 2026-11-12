"""Kit docs must point to the examples' new home (spec INV-9, design ADR-9).

Not an eval: no file under docs/ cites a demo product path without the `examples/` prefix.
A project-relative feature argument is allowed on a line that also names its instance
(`--project examples/<x>`, `validate-project examples/<x>`), since the orchestrator resolves
the feature against that project.
"""

import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2] / "docs"

# A bare citation is one not preceded by the matching examples/<instance>/ prefix.
BARE = [
    re.compile(r"(?<!examples/devis/)work/devis-pose"),
    re.compile(r"(?<!examples/devis/)work/export-devis"),
    re.compile(r"(?<!examples/booking/)work/salle-booking"),
    re.compile(r"(?<!examples/devis/)docs/export-"),
]
INSTANCE_ARG = re.compile(r"project\s+examples/")


def test_docs_do_not_cite_demo_paths_without_examples_prefix():
    offenders = []
    for md in sorted(DOCS.rglob("*.md")):
        for n, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            if INSTANCE_ARG.search(line):
                continue
            if any(p.search(line) for p in BARE):
                offenders.append(f"{md.relative_to(DOCS.parent)}:{n}: {line.strip()}")
    assert not offenders, "bare demo paths:\n" + "\n".join(offenders)


# The kit ships as a plugin under lab/plugin/ (design ADR-1, ADR-3): there is no `.claude/`
# tree in the kit any more, so no doc may point at one. The user-level `~/.claude/settings.json`
# (where the FDE wires the status line) is not the kit's and stays allowed.
ROOT = DOCS.parent
STALE_CLAUDE = re.compile(r"(?<!~/)\.claude/(agents|hooks|skills|settings\.json|statusline\.py)")


def test_docs_do_not_reference_the_removed_kit_dot_claude():
    offenders = []
    files = [ROOT / "README.md", *sorted(DOCS.rglob("*.md"))]
    for md in files:
        for n, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            if STALE_CLAUDE.search(line):
                offenders.append(f"{md.relative_to(ROOT)}:{n}: {line.strip()}")
    assert not offenders, "stale .claude/ references:\n" + "\n".join(offenders)
