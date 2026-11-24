from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from zacretario.scheduling import Availability, find_free_slots

SP = ZoneInfo("America/Sao_Paulo")
RANGE_START = datetime(2026, 11, 30, 0, 0, tzinfo=SP)  # Monday
RANGE_END = datetime(2026, 12, 7, 0, 0, tzinfo=SP)  # after Sunday


def dt(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=SP)


def search(busy=(), *, duration=timedelta(hours=1), availability=None, **kwargs):
    kwargs.setdefault("range_start", RANGE_START)
    return find_free_slots(
        list(busy),
        range_end=RANGE_END,
        duration=duration,
        availability=availability or Availability(),
        tz=SP,
        **kwargs,
    )


def test_empty_calendar_one_slot_per_day():
    slots = search(duration=timedelta(hours=2))

    assert len(slots) == 5
    assert slots[0] == (dt(30, 8), dt(30, 10))
    assert [s[0].date().day for s in slots] == [30, 1, 2, 3, 4]


def test_respects_buffer_around_events():
    slots = search([(dt(30, 8), dt(30, 9))], max_slots=1)

    assert slots == [(dt(30, 9, 15), dt(30, 10, 15))]


def test_skips_blocked_weekdays():
    availability = Availability(blocked_weekdays=frozenset({0}))

    slots = search(availability=availability)

    assert slots
    assert all(s[0].date().day != 30 for s in slots)


def test_rounds_start_to_quarter_hour():
    slots = search([(dt(30, 8), dt(30, 9, 5))], max_slots=1)

    assert slots[0][0] == dt(30, 9, 30)


def test_gap_too_small_is_skipped():
    busy = [(dt(30, 8), dt(30, 9)), (dt(30, 10), dt(30, 22))]

    slots = search(busy)

    assert all(s[0].date() != dt(30, 0).date() for s in slots)


def test_range_start_mid_day():
    slots = search(range_start=dt(30, 15, 10), max_slots=1)

    assert slots[0][0] == dt(30, 15, 15)


def test_returns_slots_in_given_timezone_for_utc_inputs():
    busy = [(datetime(2026, 11, 30, 11, 0, tzinfo=UTC), datetime(2026, 11, 30, 12, 5, tzinfo=UTC))]

    slots = search(busy, range_start=RANGE_START.astimezone(UTC), max_slots=1)

    assert slots[0][0] == dt(30, 9, 30)
    assert slots[0][0].tzinfo == SP
    assert slots[0][1].tzinfo == SP


def test_overlapping_busy_intervals():
    busy = [(dt(30, 8), dt(30, 10)), (dt(30, 9), dt(30, 11))]

    slots = search(busy, max_slots=1)

    assert slots == [(dt(30, 11, 15), dt(30, 12, 15))]
