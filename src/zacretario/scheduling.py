from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

SLOT_STEP_MINUTES = 15


@dataclass(frozen=True)
class Availability:
    day_start: time = time(8)
    day_end: time = time(22)
    # Weekday numbers, 0 = Monday
    blocked_weekdays: frozenset[int] = field(default_factory=frozenset)


def find_free_slots(
    busy: list[tuple[datetime, datetime]],
    *,
    range_start: datetime,
    range_end: datetime,
    duration: timedelta,
    availability: Availability,
    tz: ZoneInfo,
    buffer: timedelta = timedelta(minutes=15),
    max_slots: int = 5,
) -> list[tuple[datetime, datetime]]:
    """Propose at most one free slot per day, in chronological order."""
    padded_busy = sorted((start - buffer, end + buffer) for start, end in busy)
    slots: list[tuple[datetime, datetime]] = []

    for day in _days_between(range_start.astimezone(tz), range_end.astimezone(tz)):
        if len(slots) >= max_slots:
            break
        if day.weekday() in availability.blocked_weekdays:
            continue
        window_start = max(datetime.combine(day, availability.day_start, tzinfo=tz), range_start)
        window_end = min(datetime.combine(day, availability.day_end, tzinfo=tz), range_end)
        slot = _first_slot_in_window(padded_busy, window_start, window_end, duration)
        if slot:
            slots.append(slot)

    return slots


def _days_between(start: datetime, end: datetime) -> list[date]:
    days = (end.date() - start.date()).days + 1
    return [start.date() + timedelta(days=i) for i in range(days)]


def _first_slot_in_window(
    busy: list[tuple[datetime, datetime]],
    window_start: datetime,
    window_end: datetime,
    duration: timedelta,
) -> tuple[datetime, datetime] | None:
    cursor = window_start
    # The final sentinel turns the time after the last event into one more gap.
    for busy_start, busy_end in [*busy, (window_end, window_end)]:
        gap_end = min(busy_start, window_end)
        start = _round_up_to_step(cursor)
        if start + duration <= gap_end:
            return start, start + duration
        cursor = max(cursor, busy_end)
    return None


def _round_up_to_step(moment: datetime) -> datetime:
    step = timedelta(minutes=SLOT_STEP_MINUTES)
    midnight = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    steps = -((midnight - moment) // step)  # ceiling division
    return midnight + steps * step
