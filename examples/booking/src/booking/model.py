"""Pure domain: Booking entity, INV-2/INV-3 validation, overlap test ADR-1."""

from dataclasses import dataclass


@dataclass
class Booking:
    id: str
    room_id: str
    start: int
    end: int
    holder: str
    status: str  # "confirmed" | "cancelled"


def validate_slot(start: int, end: int) -> str | None:
    """Return rejection reason or None if the slot is valid (INV-2, INV-3)."""
    if not (0 <= start < end <= 1440):
        return "invalid_slot"
    if end - start > 240:
        return "too_long"
    return None


def overlaps(a: Booking, b: Booking) -> bool:
    """True iff [a.start, a.end) and [b.start, b.end) intersect (ADR-1, BHV-1a)."""
    return a.start < b.end and b.start < a.end
