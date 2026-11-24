from datetime import time

from sqlalchemy.orm import Session

from zacretario.models import UserPreference
from zacretario.scheduling import Availability


def _to_availability(row: UserPreference | None) -> Availability:
    if row is None:
        return Availability()
    blocked = frozenset(int(day) for day in row.blocked_weekdays.split(",") if day)
    return Availability(row.day_start, row.day_end, blocked)


def get_availability(session: Session, owner: str) -> Availability:
    return _to_availability(session.get(UserPreference, owner))


def update_availability(
    session: Session,
    owner: str,
    *,
    day_start: time | None = None,
    day_end: time | None = None,
    blocked_weekdays: set[int] | None = None,
) -> Availability:
    current = get_availability(session, owner)
    new_start = day_start if day_start is not None else current.day_start
    new_end = day_end if day_end is not None else current.day_end
    new_blocked = (
        frozenset(blocked_weekdays) if blocked_weekdays is not None else current.blocked_weekdays
    )

    if new_start >= new_end:
        raise ValueError("day_start must be before day_end")
    if any(day < 0 or day > 6 for day in new_blocked):
        raise ValueError("blocked_weekdays must be between 0 (Monday) and 6 (Sunday)")

    row = session.get(UserPreference, owner)
    if row is None:
        row = UserPreference(owner=owner)
        session.add(row)
    row.day_start = new_start
    row.day_end = new_end
    row.blocked_weekdays = ",".join(str(day) for day in sorted(new_blocked))
    session.commit()
    return _to_availability(row)
