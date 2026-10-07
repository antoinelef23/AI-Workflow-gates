"""EVAL-3 — client formatting (BHV-3) on the EX-2 data."""

import pytest

from devis.format import format_quote

# Dict matching the design.md §5 contract (Examples keys), EX-2 values.
EX2_QUOTE = {
    "products_eur": 2375.00,
    "installation_eur": 900.00,
    "total_eur": 3275.00,
    "is_estimate": True,
}


@pytest.mark.eval
def test_eval_3_format_ex2():
    texte = format_quote(EX2_QUOTE)

    # BHV-3: "estimate" mention
    assert "estimate" in texte.lower()

    # BHV-3: total in euros with exactly 2 decimals
    assert "3275.00" in texte

    # BHV-3: products / installation detail on separate lines
    lignes = texte.splitlines()
    lignes_produits = [ligne for ligne in lignes if "2375.00" in ligne]
    lignes_pose = [ligne for ligne in lignes if "900.00" in ligne]
    assert len(lignes_produits) == 1
    assert len(lignes_pose) == 1
    assert lignes_produits[0] != lignes_pose[0]
