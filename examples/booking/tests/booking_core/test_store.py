"""Unit tests for booking.store — BHV-1..3, INV-1."""

from booking.store import BookingStore


class TestBook:
    def test_bhv1_nominal_confirmed(self):
        s = BookingStore()
        r = s.book("A", 540, 600, "alice")
        assert r["status"] == "confirmed"
        assert "id" in r

    def test_bhv1_returns_unique_ids(self):
        s = BookingStore()
        r1 = s.book("A", 540, 600, "alice")
        r2 = s.book("A", 600, 660, "bob")
        assert r1["id"] != r2["id"]

    def test_bhv1b_invalid_slot_start_equals_end(self):
        s = BookingStore()
        assert s.book("A", 600, 600, "alice") == {"rejected": "invalid_slot"}

    def test_bhv1b_invalid_slot_start_negative(self):
        s = BookingStore()
        assert s.book("A", -1, 60, "alice") == {"rejected": "invalid_slot"}

    def test_bhv1b_invalid_slot_end_over_1440(self):
        s = BookingStore()
        assert s.book("A", 1400, 1441, "alice") == {"rejected": "invalid_slot"}

    def test_bhv1c_too_long(self):
        s = BookingStore()
        assert s.book("A", 540, 800, "alice") == {"rejected": "too_long"}

    def test_bhv2_overlap_rejected(self):
        s = BookingStore()
        s.book("A", 540, 600, "alice")
        assert s.book("A", 570, 630, "bob") == {"rejected": "overlap"}

    def test_bhv2_exact_same_slot_rejected(self):
        s = BookingStore()
        s.book("A", 540, 600, "alice")
        assert s.book("A", 540, 600, "bob") == {"rejected": "overlap"}

    def test_bhv1a_adjacent_allowed(self):
        s = BookingStore()
        s.book("A", 540, 600, "alice")
        r = s.book("A", 600, 660, "bob")
        assert r["status"] == "confirmed"

    def test_bhv2a_other_room_allowed(self):
        s = BookingStore()
        s.book("A", 540, 600, "alice")
        r = s.book("B", 540, 600, "bob")
        assert r["status"] == "confirmed"

    def test_bhv2b_cancelled_ignored(self):
        s = BookingStore()
        r1 = s.book("A", 540, 600, "alice")
        s.cancel(r1["id"])
        r2 = s.book("A", 540, 600, "bob")
        assert r2["status"] == "confirmed"


class TestCancel:
    def test_bhv3_cancel_confirmed(self):
        s = BookingStore()
        r = s.book("A", 540, 600, "alice")
        assert s.cancel(r["id"]) == {"status": "cancelled"}

    def test_bhv3_cancelled_slot_rebookable(self):
        s = BookingStore()
        r = s.book("A", 540, 600, "alice")
        s.cancel(r["id"])
        r2 = s.book("A", 540, 600, "charlie")
        assert r2["status"] == "confirmed"

    def test_bhv3a_not_found(self):
        s = BookingStore()
        assert s.cancel("nonexistent-id") == {"rejected": "not_found"}

    def test_bhv3_confirmed_drops_from_confirmed_list(self):
        s = BookingStore()
        r = s.book("A", 540, 600, "alice")
        s.cancel(r["id"])
        assert s.confirmed("A") == []


class TestConfirmed:
    def test_only_confirmed_returned(self):
        s = BookingStore()
        r1 = s.book("A", 540, 600, "alice")
        r2 = s.book("A", 600, 660, "bob")
        s.cancel(r2["id"])
        confirmed = s.confirmed("A")
        assert len(confirmed) == 1
        assert confirmed[0].id == r1["id"]

    def test_only_same_room_returned(self):
        s = BookingStore()
        s.book("A", 540, 600, "alice")
        s.book("B", 540, 600, "bob")
        assert len(s.confirmed("A")) == 1
        assert len(s.confirmed("B")) == 1
