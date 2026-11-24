from datetime import date, datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import httplib2
import pytest
from googleapiclient.errors import HttpError

from zacretario.calendar.base import (
    CalendarEvent,
    EventHasAttendeesError,
    EventNotFoundError,
)
from zacretario.calendar.google import GoogleCalendarProvider

SP = ZoneInfo("America/Sao_Paulo")


@pytest.fixture
def service():
    return MagicMock()


@pytest.fixture
def provider(service):
    return GoogleCalendarProvider(service, tz=SP)


def _events(service):
    return service.events.return_value


def test_create_timed_event_payload(provider, service):
    _events(service).insert.return_value.execute.return_value = {
        "id": "abc",
        "summary": "Dentista",
        "start": {"dateTime": "2026-11-27T10:00:00-03:00"},
        "end": {"dateTime": "2026-11-27T11:00:00-03:00"},
    }

    event = provider.create_event(
        "Dentista",
        datetime(2026, 11, 27, 10, 0, tzinfo=SP),
        datetime(2026, 11, 27, 11, 0, tzinfo=SP),
        False,
    )

    kwargs = _events(service).insert.call_args.kwargs
    assert kwargs["calendarId"] == "primary"
    body = kwargs["body"]
    assert body["summary"] == "Dentista"
    assert body["start"]["dateTime"] == "2026-11-27T10:00:00-03:00"
    assert body["start"]["timeZone"] == "America/Sao_Paulo"
    assert body["extendedProperties"]["private"]["zacretario"] == "true"
    assert event.id == "abc"
    assert event.start == datetime(2026, 11, 27, 10, 0, tzinfo=SP)


def test_create_all_day_event_payload(provider, service):
    _events(service).insert.return_value.execute.return_value = {
        "id": "d1",
        "summary": "Feriado",
        "start": {"date": "2026-11-28"},
        "end": {"date": "2026-11-29"},
    }

    event = provider.create_event("Feriado", date(2026, 11, 28), date(2026, 11, 29), True)

    body = _events(service).insert.call_args.kwargs["body"]
    assert body["start"] == {"date": "2026-11-28"}
    assert body["end"] == {"date": "2026-11-29"}
    assert event.all_day is True
    assert event.start == date(2026, 11, 28)


def test_list_events_maps_fields(provider, service):
    _events(service).list.return_value.execute.return_value = {
        "items": [
            {
                "id": "1",
                "summary": "Reunião",
                "start": {"dateTime": "2026-11-27T13:00:00+00:00"},
                "end": {"dateTime": "2026-11-27T14:00:00+00:00"},
            },
            {
                "id": "2",
                "summary": "Viagem",
                "start": {"date": "2026-11-28"},
                "end": {"date": "2026-11-29"},
            },
            {
                "id": "3",
                "summary": "Almoço",
                "start": {"dateTime": "2026-11-27T12:00:00-03:00"},
                "end": {"dateTime": "2026-11-27T13:00:00-03:00"},
                "attendees": [{"email": "x", "self": True}, {"email": "y"}],
            },
            {"id": "4", "status": "cancelled"},
        ]
    }

    events = provider.list_events(
        datetime(2026, 11, 27, tzinfo=SP), datetime(2026, 11, 30, tzinfo=SP)
    )

    kwargs = _events(service).list.call_args.kwargs
    assert kwargs["singleEvents"] is True
    assert kwargs["orderBy"] == "startTime"
    assert kwargs["timeMin"] == "2026-11-27T00:00:00-03:00"
    assert events == [
        CalendarEvent(
            "1",
            "Reunião",
            datetime(2026, 11, 27, 10, 0, tzinfo=SP),
            datetime(2026, 11, 27, 11, 0, tzinfo=SP),
            False,
            False,
        ),
        CalendarEvent("2", "Viagem", date(2026, 11, 28), date(2026, 11, 29), True),
        CalendarEvent(
            "3",
            "Almoço",
            datetime(2026, 11, 27, 12, 0, tzinfo=SP),
            datetime(2026, 11, 27, 13, 0, tzinfo=SP),
            False,
            True,
        ),
    ]


def test_update_refuses_event_with_attendees(provider, service):
    _events(service).get.return_value.execute.return_value = {
        "id": "3",
        "summary": "Almoço",
        "start": {"dateTime": "2026-11-27T12:00:00-03:00"},
        "end": {"dateTime": "2026-11-27T13:00:00-03:00"},
        "attendees": [{"email": "y"}],
    }

    with pytest.raises(EventHasAttendeesError):
        provider.update_event("3", title="Novo")

    _events(service).patch.assert_not_called()


def test_update_patches_only_given_fields(provider, service):
    _events(service).get.return_value.execute.return_value = {
        "id": "1",
        "summary": "Velho",
        "start": {"dateTime": "2026-11-27T12:00:00-03:00"},
        "end": {"dateTime": "2026-11-27T13:00:00-03:00"},
    }
    _events(service).patch.return_value.execute.return_value = {
        "id": "1",
        "summary": "Novo",
        "start": {"dateTime": "2026-11-27T12:00:00-03:00"},
        "end": {"dateTime": "2026-11-27T13:00:00-03:00"},
    }

    event = provider.update_event("1", title="Novo")

    kwargs = _events(service).patch.call_args.kwargs
    assert kwargs["eventId"] == "1"
    assert kwargs["body"] == {"summary": "Novo"}
    assert kwargs["sendUpdates"] == "none"
    assert event.title == "Novo"


def test_delete_uses_send_updates_none(provider, service):
    _events(service).get.return_value.execute.return_value = {
        "id": "1",
        "summary": "X",
        "start": {"date": "2026-11-28"},
        "end": {"date": "2026-11-29"},
    }

    provider.delete_event("1")

    kwargs = _events(service).delete.call_args.kwargs
    assert kwargs["eventId"] == "1"
    assert kwargs["sendUpdates"] == "none"
    _events(service).delete.return_value.execute.assert_called_once()


def test_missing_event_raises_not_found(provider, service):
    error = HttpError(httplib2.Response({"status": 404}), b"not found")
    _events(service).get.return_value.execute.side_effect = error

    with pytest.raises(EventNotFoundError):
        provider.delete_event("nope")
