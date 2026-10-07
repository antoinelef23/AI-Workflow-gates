"""EVAL-3 — availability fusionne les trous adjacents et exclut les cancelled (spec.md §7)."""

import pytest

from booking.availability import availability
from booking.store import BookingStore


@pytest.mark.eval
def test_eval_3_a_adjacent_bookings_no_spurious_gap():
    """BHV-4 — two adjacent bookings (A.end == B.start) do not produce a gap
    at their junction; result sorted by start."""
    store = BookingStore()
    store.book("R1", 540, 600, "alice")  # 09:00–10:00
    store.book("R1", 600, 660, "bob")  # 10:00–11:00, adjacent

    gaps = availability(store, "R1", 480, 720)  # 08:00–12:00

    # Exactly 2 gaps — no zero-width gap at junction 600
    assert gaps == [(480, 540), (660, 720)]


@pytest.mark.eval
def test_eval_3_b_cancel_releases_slot_and_fuses():
    """BHV-3 + BHV-2b + BHV-4 — cancel releases the slot; adjacent gaps merge."""
    store = BookingStore()
    r_alice = store.book("R2", 540, 600, "alice")  # 09:00–10:00
    store.book("R2", 660, 720, "bob")  # 11:00–12:00

    # Before cancel: 3 separate gaps
    before = availability(store, "R2", 480, 780)
    assert before == [(480, 540), (600, 660), (720, 780)]

    # Cancel alice — slot released (BHV-3, BHV-2b)
    result = store.cancel(r_alice["id"])
    assert result == {"status": "cancelled"}

    # After cancel: freed [540,600) fuses with neighbours → single gap [480,660)
    after = availability(store, "R2", 480, 780)
    assert after == [(480, 660), (720, 780)]
