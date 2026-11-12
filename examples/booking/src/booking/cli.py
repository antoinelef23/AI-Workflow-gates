"""Manual demo CLI — minimal argparse, in-memory store, time as arguments (ADR-1)."""

import argparse
import json

from .availability import availability as compute_availability
from .store import BookingStore


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="booking",
        description="Manual demo of the room booking manager.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_book = sub.add_parser("book", help="Book a slot.")
    p_book.add_argument("--room", required=True, help="Room identifier.")
    p_book.add_argument(
        "--start", type=int, required=True, help="Start (minutes since midnight)."
    )
    p_book.add_argument(
        "--end", type=int, required=True, help="End (minutes since midnight)."
    )
    p_book.add_argument("--holder", required=True, help="Booking holder.")

    p_cancel = sub.add_parser("cancel", help="Cancel a booking.")
    p_cancel.add_argument(
        "--id", required=True, dest="booking_id", help="Booking identifier."
    )

    p_avail = sub.add_parser("availability", help="Free slots of a room.")
    p_avail.add_argument("--room", required=True, help="Room identifier.")
    p_avail.add_argument(
        "--start",
        type=int,
        required=True,
        help="Window start (minutes since midnight).",
    )
    p_avail.add_argument(
        "--end",
        type=int,
        required=True,
        help="Window end (minutes since midnight).",
    )

    args = parser.parse_args()
    store = BookingStore()

    if args.command == "book":
        result = store.book(args.room, args.start, args.end, args.holder)
    elif args.command == "cancel":
        result = store.cancel(args.booking_id)
    else:
        gaps = compute_availability(store, args.room, args.start, args.end)
        result = {"gaps": [list(g) for g in gaps]}

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
