"""Non-eval test of the devis CLI — output on EX-1 (spec devis-pose §5)."""

from devis.cli import main


def test_cli_ex1_nominal(capsys):
    # EX-1: products 1500.00, surface 10 → products 1500.00, installation 450.00, total 1950.00
    main(["--products-eur", "1500.00", "--surface-m2", "10"])
    out = capsys.readouterr().out

    assert "estimate" in out
    assert "1500.00" in out
    assert "450.00" in out
    assert "1950.00" in out
    # BHV-3: products / installation detail on separate lines
    lines = out.splitlines()
    assert any("Products" in line for line in lines)
    assert any("Installation" in line for line in lines)
