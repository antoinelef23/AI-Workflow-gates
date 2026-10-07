"""EVAL-1 — Examples EX-1 to EX-5 checked exactly (spec.md §5, §7)."""

import pytest

from booking.availability import availability
from booking.store import BookingStore


@pytest.mark.eval
def test_eval_1_ex1_nominal_confirmed():
    """EX-1 — nominal confirmed booking (BHV-1)."""
    store = BookingStore()
    result = store.book("A", 540, 600, "alice")
    assert result["status"] == "confirmed"
    assert "id" in result


@pytest.mark.eval
def test_eval_1_ex2_overlap_rejected():
    """EX-2 — overlap rejected (BHV-2)."""
    store = BookingStore()
    store.book("A", 540, 600, "alice")
    result = store.book("A", 570, 630, "bob")
    assert result == {"rejected": "overlap"}


@pytest.mark.eval
def test_eval_1_ex3_adjacent_allowed():
    """EX-3 — adjacent slots allowed (BHV-1a)."""
    store = BookingStore()
    store.book("A", 540, 600, "alice")
    result = store.book("A", 600, 660, "bob")
    assert result["status"] == "confirmed"


@pytest.mark.eval
def test_eval_1_ex4_availability():
    """EX-4 — availability = [[480,540],[600,660],[720,780]] (BHV-4)."""
    store = BookingStore()
    store.book("A", 540, 600, "alice")
    store.book("A", 660, 720, "bob")
    gaps = availability(store, "A", 480, 780)
    assert gaps == [(480, 540), (600, 660), (720, 780)]


@pytest.mark.eval
def test_eval_1_ex5_too_long_rejected():
    """EX-5 — duration 260 min rejected too_long (BHV-1c)."""
    store = BookingStore()
    result = store.book("B", 540, 800, "carol")
    assert result == {"rejected": "too_long"}
