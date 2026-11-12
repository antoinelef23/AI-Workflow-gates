"""EVAL-1 — plain-text export (BHV-1, INV-1) on the EX-1 data."""

import pytest

from devis.export import export_quote

# Dict matching the devis-pose design.md §5 contract, EX-1 values.
EX1_QUOTE = {
    "products_eur": 2375.00,
    "installation_eur": 900.00,
    "total_eur": 3275.00,
    "is_estimate": True,
}


@pytest.mark.eval
def test_eval_1_export_ex1():
    export = export_quote(EX1_QUOTE)

    # BHV-1: plain text encoded UTF-8
    assert isinstance(export, bytes)
    texte = export.decode("utf-8")

    # INV-1: "estimate" mention
    assert "estimate" in texte.lower()

    # EX-1: total with exactly 2 decimals
    assert "3275.00" in texte

    # EX-1: distinct Products / Installation lines
    lignes = texte.splitlines()
    lignes_produits = [ligne for ligne in lignes if ligne.startswith("Products")]
    lignes_pose = [ligne for ligne in lignes if ligne.startswith("Installation")]
    assert len(lignes_produits) == 1
    assert len(lignes_pose) == 1
    assert lignes_produits[0] != lignes_pose[0]
