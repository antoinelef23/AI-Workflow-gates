"""Unit tests for the export (BHV-1, BHV-1a)."""

from devis.export import export_quote
from devis.format import format_quote

EX1_QUOTE = {
    "products_eur": 2375.00,
    "installation_eur": 900.00,
    "total_eur": 3275.00,
    "is_estimate": True,
}


def test_bhv_1_export_est_exactement_format_quote_utf8():
    # BHV-1: exactly the output of format_quote, encoded UTF-8
    assert export_quote(EX1_QUOTE) == format_quote(EX1_QUOTE).encode("utf-8")


def test_bhv_1a_devis_sans_pose():
    # BHV-1a: quote without installation (surface 0) — valid export, Installation line at 0.00 EUR
    quote = {
        "products_eur": 1500.00,
        "installation_eur": 0.00,
        "total_eur": 1500.00,
        "is_estimate": True,
    }
    texte = export_quote(quote).decode("utf-8")
    assert "Installation: 0.00 EUR" in texte.splitlines()
