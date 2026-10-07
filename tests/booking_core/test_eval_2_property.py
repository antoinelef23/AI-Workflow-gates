"""EVAL-2 — property-based: INV-1/INV-2/INV-3 over 500 random sequences (seed fixe)."""

import random

import pytest

from booking.model import overlaps
from booking.store import BookingStore

ROOMS = ["A", "B", "C"]
N_SEQUENCES = 500
SEED = 42


@pytest.mark.eval
def test_eval_2_property_invariants():
    rng = random.Random(SEED)

    for seq_idx in range(N_SEQUENCES):
        store = BookingStore()
        n_ops = rng.randint(5, 30)

        for _ in range(n_ops):
            room_id = rng.choice(ROOMS)
            start = rng.randint(0, 1380)
            duration = rng.randint(1, 250)
            end = min(start + duration, 1440)
            holder = f"user_{rng.randint(0, 9)}"
            store.book(room_id, start, end, holder)

        for room_id in ROOMS:
            confirmed = store.confirmed(room_id)

            for i, a in enumerate(confirmed):
                for j in range(i + 1, len(confirmed)):
                    b = confirmed[j]
                    assert not overlaps(a, b), (
                        f"INV-1 violated at sequence {seq_idx}: "
                        f"room={room_id} {a} overlaps {b}"
                    )

                assert 0 <= a.start < a.end <= 1440, (
                    f"INV-2 violated at sequence {seq_idx}: room={room_id} {a}"
                )
                assert a.end - a.start <= 240, (
                    f"INV-3 violated at sequence {seq_idx}: room={room_id} {a}"
                )
