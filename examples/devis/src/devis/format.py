"""Pure quote presentation (BHV-3) — no dependency on the calc module."""


def format_quote(quote: dict) -> str:
    """Formate un devis pour affichage client.

    `quote` respecte le contrat des Examples (design.md §5) :
    `products_eur`, `installation_eur`, `total_eur`, `is_estimate`.
    """
    return "\n".join(
        [
            "Quote — non-binding estimate",
            f"Products: {quote['products_eur']:.2f} EUR",
            f"Installation: {quote['installation_eur']:.2f} EUR",
            f"Total: {quote['total_eur']:.2f} EUR",
        ]
    )
