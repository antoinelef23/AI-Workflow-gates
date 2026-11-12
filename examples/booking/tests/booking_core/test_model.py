"""Unit tests for booking.model — INV-2, INV-3, BHV-1a."""

from booking.model import Booking, validate_slot, overlaps


def _b(start: int, end: int) -> Booking:
    return Booking(
        id="x", room_id="A", start=start, end=end, holder="h", status="confirmed"
    )


# --- validate_slot (INV-2 / INV-3) ---


class TestValidateSlot:
    def test_valid_nominal(self):
        assert validate_slot(540, 600) is None

    def test_valid_min_boundary(self):
        assert validate_slot(0, 1) is None

    def test_valid_max_boundary(self):
        assert validate_slot(1200, 1440) is None

    def test_valid_exactly_240(self):
        assert validate_slot(0, 240) is None

    def test_inv2_start_equals_end(self):
        assert validate_slot(600, 600) == "invalid_slot"

    def test_inv2_start_greater_than_end(self):
        assert validate_slot(700, 600) == "invalid_slot"

    def test_inv2_start_negative(self):
        assert validate_slot(-1, 60) == "invalid_slot"

    def test_inv2_end_exceeds_1440(self):
        assert validate_slot(1400, 1441) == "invalid_slot"

    def test_inv2_end_exactly_1440(self):
        assert validate_slot(1400, 1440) is None

    def test_inv3_duration_241(self):
        assert validate_slot(0, 241) == "too_long"

    def test_inv3_duration_240_valid(self):
        assert validate_slot(0, 240) is None

    def test_inv2_checked_before_inv3(self):
        # start==end with potential too_long: invalid_slot wins
        assert validate_slot(600, 600) == "invalid_slot"

    def test_inv3_ex5_from_spec(self):
        # EX-5: 540..800 = 260 min > 240
        assert validate_slot(540, 800) == "too_long"


# --- overlaps (ADR-1, BHV-1a) ---


class TestOverlaps:
    def test_proper_overlap(self):
        assert overlaps(_b(540, 600), _b(570, 630)) is True

    def test_contained(self):
        assert overlaps(_b(540, 700), _b(560, 620)) is True

    def test_no_overlap_before(self):
        assert overlaps(_b(480, 540), _b(600, 660)) is False

    def test_no_overlap_after(self):
        assert overlaps(_b(660, 720), _b(480, 540)) is False

    def test_adjacent_end_equals_start_not_overlap(self):
        # BHV-1a: end of A == start of B → allowed (half-open interval)
        assert overlaps(_b(540, 600), _b(600, 660)) is False

    def test_adjacent_reverse(self):
        assert overlaps(_b(600, 660), _b(540, 600)) is False

    def test_same_interval(self):
        assert overlaps(_b(540, 600), _b(540, 600)) is True

    def test_partial_overlap_left(self):
        assert overlaps(_b(540, 600), _b(500, 560)) is True

    def test_partial_overlap_right(self):
        assert overlaps(_b(540, 600), _b(580, 640)) is True
