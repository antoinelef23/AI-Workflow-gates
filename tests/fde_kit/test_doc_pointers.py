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
