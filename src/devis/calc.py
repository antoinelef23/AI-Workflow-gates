"""Domaine pur — calcul du devis de pose (spec devis-pose, ADR-1)."""

INSTALLATION_RATE_EUR_PER_M2 = 45.00  # BHV-1
VOLUME_DISCOUNT_THRESHOLD_EUR = 2000.00  # BHV-2: strictly greater (BHV-2a)
VOLUME_DISCOUNT_RATE = 0.05  # BHV-2


def compute_quote(products_subtotal_eur: float, surface_m2: float) -> dict:
    """Calcule le devis produits + pose.

    Output contract = keys of the spec Examples (design.md §5):
    products_eur, installation_eur, total_eur, is_estimate.
    """
    # INV-1: total ≥ 0 for any inputs — lower bounds at 0.
    products = max(0.0, products_subtotal_eur)
    surface = max(0.0, surface_m2)

    if products > VOLUME_DISCOUNT_THRESHOLD_EUR:
        # INV-3 : la remise ne porte que sur le sous-total produits.
        products *= 1 - VOLUME_DISCOUNT_RATE

    products_eur = round(products, 2)
    installation_eur = round(surface * INSTALLATION_RATE_EUR_PER_M2, 2)
    return {
        "products_eur": products_eur,
        "installation_eur": installation_eur,
        "total_eur": round(products_eur + installation_eur, 2),
        "is_estimate": True,  # INV-2
    }
