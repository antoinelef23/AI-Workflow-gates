"""Unit tests for booking.availability — BHV-4."""

from booking.store import BookingStore
from booking.availability import availability


class TestAvailability:
    def test_ex4_from_spec(self):
        # EX-4: two bookings 09:00-10:00 and 11:00-12:00, window 08:00-13:00
        s = BookingStore()
        s.book("A", 540, 600, "alice")
        s.book("A", 660, 720, "bob")
        result = availability(s, "A", 480, 780)
        assert result == [(480, 540), (600, 660), (720, 780)]

    def test_no_bookings_full_window(self):
        s = BookingStore()
        result = availability(s, "A", 480, 780)
        assert result == [(480, 780)]

    def test_fully_booked_no_gaps(self):
        s = BookingStore()
        s.book("A", 480, 720, "alice")
        result = availability(s, "A", 480, 720)
        assert result == []

    def test_booking_covers_window(self):
        # Booking [480, 720] (240 min, valid) entirely covers the window [540, 660]
        s = BookingStore()
        s.book("A", 480, 720, "alice")
        result = availability(s, "A", 540, 660)
        assert result == []

    def test_booking_before_window(self):
        s = BookingStore()
        s.book("A", 300, 480, "alice")
        result = availability(s, "A", 480, 720)
        assert result == [(480, 720)]

    def test_booking_after_window(self):
        s = BookingStore()
        s.book("A", 720, 900, "alice")
        result = availability(s, "A", 480, 720)
        assert result == [(480, 720)]

    def test_booking_partially_overlaps_start(self):
        s = BookingStore()
        s.book("A", 400, 540, "alice")
        result = availability(s, "A", 480, 720)
        assert result == [(540, 720)]

    def test_booking_partially_overlaps_end(self):
        s = BookingStore()
        s.book("A", 660, 800, "alice")
        result = availability(s, "A", 480, 720)
        assert result == [(480, 660)]

    def test_cancelled_booking_ignored(self):
        # BHV-2b: cancelled bookings do not block availability
        s = BookingStore()
        r = s.book("A", 540, 600, "alice")
        s.cancel(r["id"])
        result = availability(s, "A", 480, 780)
        assert result == [(480, 780)]

    def test_adjacent_bookings_no_gap_between(self):
        # BHV-1a: adjacent bookings leave no slot between them
        s = BookingStore()
        s.book("A", 540, 600, "alice")
        s.book("A", 600, 660, "bob")
        result = availability(s, "A", 480, 780)
        assert result == [(480, 540), (660, 780)]

    def test_other_room_not_included(self):
        s = BookingStore()
        s.book("B", 540, 600, "alice")
        result = availability(s, "A", 480, 780)
        assert result == [(480, 780)]

    def test_sorted_by_start(self):
        s = BookingStore()
        s.book("A", 660, 720, "bob")
        s.book("A", 540, 600, "alice")
        result = availability(s, "A", 480, 780)
        starts = [g[0] for g in result]
        assert starts == sorted(starts)
