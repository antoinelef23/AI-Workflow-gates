"""Computes a room's free gaps within a window — BHV-4."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .store import BookingStore


def availability(
    store: BookingStore, room_id: str, ws: int, we: int
) -> list[tuple[int, int]]:
    """Return free slots in [ws, we) for room_id, sorted by start, gaps merged."""
    confirmed = store.confirmed(room_id)

    occupied = sorted(
        (max(b.start, ws), min(b.end, we))
        for b in confirmed
        if b.start < we and b.end > ws
    )

    gaps: list[tuple[int, int]] = []
    cursor = ws
    for occ_start, occ_end in occupied:
        if cursor < occ_start:
            gaps.append((cursor, occ_start))
        cursor = max(cursor, occ_end)
    if cursor < we:
        gaps.append((cursor, we))

    return gaps
