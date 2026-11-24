from dataclasses import replace
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from zacretario.calendar.base import (
    CalendarError,
    CalendarEvent,
    EventHasAttendeesError,
    EventNotFoundError,
)

SP = ZoneInfo("America/Sao_Paulo")


class FakeCalendar:
    """In-memory CalendarProvider that follows the same rules as the Google one."""

    def __init__(self) -> None:
        self.events: dict[str, CalendarEvent] = {}
        self._next_id = 1

    def add_event(
        self,
        title: str,
        start: datetime | date,
        end: datetime | date,
        all_day: bool = False,
        has_attendees: bool = False,
    ) -> CalendarEvent:
        event = CalendarEvent(f"ev{self._next_id}", title, start, end, all_day, has_attendees)
        self._next_id += 1
        self.events[event.id] = event
        return event

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        found = [
            event
            for event in self.events.values()
            if _as_datetime(event.start) < end and _as_datetime(event.end) > start
        ]
        return sorted(found, key=lambda event: _as_datetime(event.start))

    def get_event(self, event_id: str) -> CalendarEvent:
        if event_id not in self.events:
            raise EventNotFoundError(event_id)
        return self.events[event_id]

    def create_event(self, title, start, end, all_day) -> CalendarEvent:
        _check_types(start, end, all_day)
        return self.add_event(title, start, end, all_day)

    def update_event(self, event_id, *, title=None, start=None, end=None, all_day=None):
        event = self._get_editable(event_id)
        changes: dict = {}
        if title is not None:
            changes["title"] = title
        time_args = (start, end, all_day)
        if any(arg is not None for arg in time_args):
            if any(arg is None for arg in time_args):
                raise CalendarError("start, end e all_day devem ser informados juntos")
            _check_types(start, end, all_day)
            changes.update(start=start, end=end, all_day=all_day)
        updated = replace(event, **changes)
        self.events[event_id] = updated
        return updated

    def delete_event(self, event_id: str) -> None:
        self._get_editable(event_id)
        del self.events[event_id]

    def _get_editable(self, event_id: str) -> CalendarEvent:
        event = self.get_event(event_id)
        if event.has_attendees:
            raise EventHasAttendeesError(event_id)
        return event


def _as_datetime(value: datetime | date) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time(0), tzinfo=SP)


def _check_types(start, end, all_day: bool) -> None:
    for value in (start, end):
        if all_day and (isinstance(value, datetime) or not isinstance(value, date)):
            raise CalendarError("evento de dia inteiro exige date, não datetime")
        if not all_day and (not isinstance(value, datetime) or value.tzinfo is None):
            raise CalendarError("evento com hora exige datetime com fuso")
