---
type: spec
feature: salle-booking
version: 1.0.1
status: validated
owner: Antoine (E2E test)
validated_by: simulated business — 2026-06-15
---

# Spec — Room booking

> **The WHAT. The business contract.** Meeting-room booking manager:
> book a slot, reject overlaps, cancel, compute availability.
> Scope is **pure and deterministic** (in memory, no I/O, time is an input,
> never `now()`) — so it is end-to-end testable.

## 1. Intent

Employees waste time coordinating rooms by email and end up double-booking.
This feature provides the business core that guarantees a room is never
booked twice, and exposes free slots.

**Target KPI:** double-booking rate 0% (vs regular incidents today).

## 2. Glossary

| Business term (EN) | Canonical name (code) | Definition |
|---|---|---|
| Booking | `booking` | Occupation of a room over a slot, with a status |
| Room | `room_id` | Room identifier (string) |
| Slot | `slot` | Interval `[start, end)` in **minutes since midnight** (0 to 1440) |
| Overlap | `overlap` | Two slots of the same room whose intervals intersect |
| Availability | `availability` | Free gaps of a room within a given window |

## 3. Invariants

- **INV-1** — Two `confirmed` bookings of the SAME room NEVER overlap.
- **INV-2** — Every booking respects `0 ≤ start < end ≤ 1440`.
- **INV-3** — A booking's duration MUST be ≤ 240 minutes (`end - start ≤ 240`).

## 4. Behaviors

### BHV-1 — Book a free slot
- **Given** a room with no overlapping booking on `[start, end)`
- **When** booking `(room_id, start, end, holder)`
- **Then** a booking is created with a unique `id` and `status = "confirmed"`
- **Edge cases:**
  - **BHV-1a** — **adjacent** slots (`end of A == start of B`, same room): allowed (no overlap, `[start, end)` is half-open).
  - **BHV-1b** — `start >= end` or outside `[0, 1440]`: rejected, reason `invalid_slot` (INV-2).
  - **BHV-1c** — duration > 240: rejected, reason `too_long` (INV-3).

### BHV-2 — Reject an overlap
- **Given** an existing `confirmed` booking on the room that intersects `[start, end)`
- **When** attempting to book the same slot (same room)
- **Then** rejected, reason `overlap`, no booking created
- **Edge cases:**
  - **BHV-2a** — overlap on ANOTHER room: allowed.
  - **BHV-2b** — overlap with a `cancelled` booking: allowed (the cancelled one does not count).

### BHV-3 — Cancel a booking
- **Given** a `confirmed` booking with a given `id`
- **When** it is cancelled
- **Then** its `status` becomes `"cancelled"` and its slot becomes bookable again (BHV-2b)
- **Edge cases:** **BHV-3a** — cancelling a non-existent `id`: rejected, reason `not_found`.

### BHV-4 — Compute availability
- **Given** a room and a window `[window_start, window_end)`
- **When** requesting `availability(room_id, window_start, window_end)`
- **Then** returns the list of free gaps `(start, end)` within the window, **sorted by start**,
  excluding `confirmed` bookings and merging adjacent gaps.

## 5. Examples

### EX-1 — nominal booking
```yaml
input: { op: book, room_id: "A", start: 540, end: 600, holder: "alice" }   # 09:00–10:00
expected_output: { status: "confirmed" }
covers: [BHV-1]
```

### EX-2 — overlap rejected
```yaml
given: [{ room_id: "A", start: 540, end: 600 }]
input: { op: book, room_id: "A", start: 570, end: 630 }   # 09:30–10:30 overlaps
expected_output: { rejected: "overlap" }
covers: [BHV-2]
```

### EX-3 — adjacent slots allowed
```yaml
given: [{ room_id: "A", start: 540, end: 600 }]
input: { op: book, room_id: "A", start: 600, end: 660 }   # 10:00–11:00 adjacent
expected_output: { status: "confirmed" }
covers: [BHV-1a]
```

### EX-4 — availability
```yaml
given: [{ room_id: "A", start: 540, end: 600 }, { room_id: "A", start: 660, end: 720 }]
input: { op: availability, room_id: "A", window_start: 480, window_end: 780 }  # 08:00–13:00
expected_output: { gaps: [[480, 540], [600, 660], [720, 780]] }
covers: [BHV-4]
```

### EX-5 — duration too long rejected
```yaml
input: { op: book, room_id: "B", start: 540, end: 800 }   # 260 min > 240
expected_output: { rejected: "too_long" }
covers: [BHV-1c]
```

## 6. Non-goals

- **NG-1** — Persistence (database): out of scope, the store is in memory.
- **NG-2** — Time zones / calendar dates: we reason in minutes since midnight over a single day.
- **NG-3** — Recurring bookings: out of scope.

## 7. Evals — merge gate

*Convention: a pytest test marked `@pytest.mark.eval`, name containing the ID in lowercase.*

| ID | Type | Description | Covers | Threshold |
|---|---|---|---|---|
| EVAL-1 | deterministic | EX-1 to EX-5 verified exactly | BHV-1, BHV-1a, BHV-1c, BHV-2, BHV-4 | 100% |
| EVAL-2 | property-based | over 500 sequences of accepted bookings (fixed seed), INV-1 holds (no confirmed overlap) | INV-1, INV-2, INV-3 | 100% |
| EVAL-3 | deterministic | `availability` merges adjacent gaps and excludes `cancelled` ones (BHV-2b) | BHV-4, BHV-3 | 100% |

## 8. Open questions

*(none — spec closed for the E2E test)*

## 9. Changelog

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0.0 | 2026-06-15 | business (E2E simulated) | Creation — contract v1 |
| 1.0.1 | 2026-06-18 | translation | English translation (form only, no substance change) |
