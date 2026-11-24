from datetime import date, datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import httplib2
import pytest
from googleapiclient.errors import HttpError

from zacretario.calendar.base import (
    CalendarError,
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


def _event_organized_by(organizer: dict) -> dict:
    return {
        "id": "5",
        "summary": "Reunião",
        "start": {"dateTime": "2026-11-27T12:00:00-03:00"},
        "end": {"dateTime": "2026-11-27T13:00:00-03:00"},
        "attendees": [{"email": "me", "self": True}],
        "organizer": organizer,
    }


def test_update_and_delete_refuse_event_organized_by_someone_else(provider, service):
    _events(service).get.return_value.execute.return_value = _event_organized_by(
        {"email": "x", "self": False}
    )

    with pytest.raises(EventHasAttendeesError):
        provider.update_event("5", title="Novo")
    with pytest.raises(EventHasAttendeesError):
        provider.delete_event("5")

    _events(service).patch.assert_not_called()
    _events(service).delete.assert_not_called()


def test_organizer_without_self_key_is_someone_else(provider, service):
    # The API omits read-only booleans that are false, so "self" is usually absent.
    _events(service).get.return_value.execute.return_value = _event_organized_by({"email": "x"})

    with pytest.raises(EventHasAttendeesError):
        provider.update_event("5", title="Novo")
    with pytest.raises(EventHasAttendeesError):
        provider.delete_event("5")

    _events(service).patch.assert_not_called()
    _events(service).delete.assert_not_called()


def test_event_without_organizer_is_editable(provider, service):
    item = _event_organized_by({})
    del item["organizer"]
    _events(service).get.return_value.execute.return_value = item
    _events(service).patch.return_value.execute.return_value = item

    provider.update_event("5", title="Novo")

    _events(service).patch.assert_called_once()


def test_update_allows_event_organized_by_me(provider, service):
    _events(service).get.return_value.execute.return_value = _event_organized_by(
        {"email": "me", "self": True}
    )
    _events(service).patch.return_value.execute.return_value = _event_organized_by(
        {"email": "me", "self": True}
    )

    provider.update_event("5", title="Novo")

    _events(service).patch.assert_called_once()


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


def _existing(service, start, end, **extra):
    _events(service).get.return_value.execute.return_value = {
        "id": "1",
        "summary": "X",
        "start": start,
        "end": end,
        **extra,
    }
    _events(service).patch.return_value.execute.return_value = {
        "id": "1",
        "summary": "X",
        "start": start,
        "end": end,
    }


def test_update_all_day_to_timed_nulls_date(provider, service):
    _existing(service, {"date": "2026-11-28"}, {"date": "2026-11-29"})

    provider.update_event(
        "1",
        start=datetime(2026, 11, 28, 9, 0, tzinfo=SP),
        end=datetime(2026, 11, 28, 10, 0, tzinfo=SP),
        all_day=False,
    )

    kwargs = _events(service).patch.call_args.kwargs
    assert kwargs["sendUpdates"] == "none"
    assert kwargs["body"]["start"] == {
        "dateTime": "2026-11-28T09:00:00-03:00",
        "timeZone": "America/Sao_Paulo",
        "date": None,
    }
    assert kwargs["body"]["end"]["date"] is None


def test_update_timed_to_all_day_nulls_datetime(provider, service):
    _existing(
        service,
        {"dateTime": "2026-11-28T09:00:00-03:00"},
        {"dateTime": "2026-11-28T10:00:00-03:00"},
    )

    provider.update_event("1", start=date(2026, 11, 28), end=date(2026, 11, 29), all_day=True)

    kwargs = _events(service).patch.call_args.kwargs
    assert kwargs["sendUpdates"] == "none"
    assert kwargs["body"]["start"] == {
        "date": "2026-11-28",
        "dateTime": None,
        "timeZone": None,
    }
    assert kwargs["body"]["end"]["dateTime"] is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"start": datetime(2026, 11, 28, 9, tzinfo=SP)},
        {"all_day": True},
        {"start": date(2026, 11, 28), "end": date(2026, 11, 29)},
    ],
)
def test_update_partial_time_args_raise(provider, service, kwargs):
    _existing(service, {"date": "2026-11-28"}, {"date": "2026-11-29"})

    with pytest.raises(CalendarError):
        provider.update_event("1", **kwargs)

    _events(service).patch.assert_not_called()


def test_wrong_types_raise(provider, service):
    d = date(2026, 11, 28)
    dt = datetime(2026, 11, 28, 9, tzinfo=SP)
    with pytest.raises(CalendarError):
        provider.create_event("X", dt, dt, True)
    with pytest.raises(CalendarError):
        provider.create_event("X", d, d, False)
    _events(service).insert.assert_not_called()

    _existing(service, {"date": "2026-11-28"}, {"date": "2026-11-29"})
    with pytest.raises(CalendarError):
        provider.update_event("1", start=d, end=d, all_day=False)
    _events(service).patch.assert_not_called()


def test_update_allowed_when_only_self_attends(provider, service):
    _existing(
        service,
        {"date": "2026-11-28"},
        {"date": "2026-11-29"},
        attendees=[{"email": "me", "self": True}],
    )

    provider.update_event("1", title="Novo")

    _events(service).patch.assert_called_once()


def test_other_http_error_becomes_calendar_error(provider, service):
    error = HttpError(httplib2.Response({"status": 500}), b"boom")
    _events(service).get.return_value.execute.side_effect = error

    with pytest.raises(CalendarError) as info:
        provider.delete_event("1")
    assert not isinstance(info.value, EventNotFoundError)


def test_get_event_maps_fields(provider, service):
    _events(service).get.return_value.execute.return_value = {
        "id": "abc",
        "summary": "Dentista",
        "start": {"dateTime": "2026-11-27T10:00:00-03:00"},
        "end": {"dateTime": "2026-11-27T11:00:00-03:00"},
        "attendees": [{"email": "x@example.com"}],
    }

    event = provider.get_event("abc")

    assert event.id == "abc"
    assert event.start == datetime(2026, 11, 27, 10, 0, tzinfo=SP)
    assert event.has_attendees is True


def test_get_event_missing_raises_not_found(provider, service):
    error = HttpError(httplib2.Response({"status": 404}), b"not found")
    _events(service).get.return_value.execute.side_effect = error

    with pytest.raises(EventNotFoundError):
        provider.get_event("nope")
