"""Quote export in the contractual format — plain text (spec export-devis, OQ-1 resolved)."""

from devis.format import format_quote


def export_quote(quote: dict) -> bytes:
    """Returns the downloadable quote (BHV-1).

    Plain text: exactly the output of `format_quote`, UTF-8 encoded.
    INV-1 (the "estimate" mention) is carried by `format_quote`.
    """
    return format_quote(quote).encode("utf-8")
