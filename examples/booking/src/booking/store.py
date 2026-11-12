"""BookingStore — in-memory store, INV-1 enforced, ADR-2 soft-delete."""

from uuid import uuid4

from .model import Booking, overlaps, validate_slot


class BookingStore:
    def __init__(self) -> None:
        self._bookings: dict[str, Booking] = {}

    def book(self, room_id: str, start: int, end: int, holder: str) -> dict:
        reason = validate_slot(start, end)
        if reason:
            return {"rejected": reason}

        booking_id = str(uuid4())
        candidate = Booking(
            id=booking_id,
            room_id=room_id,
            start=start,
            end=end,
            holder=holder,
            status="confirmed",
        )
        for existing in self.confirmed(room_id):
            if overlaps(existing, candidate):
                return {"rejected": "overlap"}

        self._bookings[booking_id] = candidate
        return {"status": "confirmed", "id": booking_id}

    def cancel(self, booking_id: str) -> dict:
        booking = self._bookings.get(booking_id)
        if booking is None:
            return {"rejected": "not_found"}
        booking.status = "cancelled"
        return {"status": "cancelled"}

    def confirmed(self, room_id: str) -> list[Booking]:
        return [
            b
            for b in self._bookings.values()
            if b.room_id == room_id and b.status == "confirmed"
        ]
