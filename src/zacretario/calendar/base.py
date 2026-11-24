from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


class CalendarError(Exception):
    pass


class EventNotFoundError(CalendarError):
    pass


class EventHasAttendeesError(CalendarError):
    pass


@dataclass(frozen=True)
class CalendarEvent:
    id: str
    title: str
    # All-day events use `date`, and `end` is exclusive (Google's convention).
    start: datetime | date
    end: datetime | date
    all_day: bool
    has_attendees: bool = False


class CalendarProvider(Protocol):
    """Extension point: Google today, Outlook/iCloud later."""

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]: ...

    def create_event(
        self,
        title: str,
        start: datetime | date,
        end: datetime | date,
        all_day: bool,
    ) -> CalendarEvent: ...

    def update_event(
        self,
        event_id: str,
        *,
        title: str | None = None,
        start: datetime | date | None = None,
        end: datetime | date | None = None,
        all_day: bool | None = None,
    ) -> CalendarEvent:
        """Time changes need start, end and all_day together (else CalendarError).

        all_day=True requires `date` values; all_day=False requires aware datetimes.
        """
        ...

    def delete_event(self, event_id: str) -> None: ...
