from datetime import date, datetime
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from zacretario.calendar.base import (
    CalendarError,
    CalendarEvent,
    EventHasAttendeesError,
    EventNotFoundError,
)
from zacretario.config import Settings

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


class GoogleCalendarProvider:
    def __init__(self, service, tz: ZoneInfo, calendar_id: str = "primary"):
        self._events = service.events()
        self._calendar_id = calendar_id
        self._tz = tz

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        response = self._execute(
            self._events.list(
                calendarId=self._calendar_id,
                timeMin=start.astimezone(self._tz).isoformat(),
                timeMax=end.astimezone(self._tz).isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
        )
        return [
            self._to_event(item)
            for item in response.get("items", [])
            if item.get("status") != "cancelled"
        ]

    def get_event(self, event_id: str) -> CalendarEvent:
        item = self._execute(self._events.get(calendarId=self._calendar_id, eventId=event_id))
        return self._to_event(item)

    def create_event(
        self,
        title: str,
        start: datetime | date,
        end: datetime | date,
        all_day: bool,
    ) -> CalendarEvent:
        self._check_types(start, end, all_day)
        body = {
            "summary": title,
            "start": self._time_field(start, all_day),
            "end": self._time_field(end, all_day),
            "extendedProperties": {"private": {"zacretario": "true"}},
        }
        item = self._execute(
            self._events.insert(calendarId=self._calendar_id, body=body, sendUpdates="none")
        )
        return self._to_event(item)

    def update_event(
        self,
        event_id: str,
        *,
        title: str | None = None,
        start: datetime | date | None = None,
        end: datetime | date | None = None,
        all_day: bool | None = None,
    ) -> CalendarEvent:
        self._get_editable(event_id)

        body: dict = {}
        if title is not None:
            body["summary"] = title

        time_args = (start, end, all_day)
        if any(arg is not None for arg in time_args):
            if any(arg is None for arg in time_args):
                raise CalendarError("start, end e all_day devem ser informados juntos")
            self._check_types(start, end, all_day)
            body["start"] = self._time_field(start, all_day, clear_other=True)
            body["end"] = self._time_field(end, all_day, clear_other=True)

        item = self._execute(
            self._events.patch(
                calendarId=self._calendar_id,
                eventId=event_id,
                body=body,
                sendUpdates="none",
            )
        )
        return self._to_event(item)

    def delete_event(self, event_id: str) -> None:
        self._get_editable(event_id)
        self._execute(
            self._events.delete(calendarId=self._calendar_id, eventId=event_id, sendUpdates="none")
        )

    def _get_editable(self, event_id: str) -> dict:
        """Fetch the event, refusing if other people are invited."""
        item = self._execute(self._events.get(calendarId=self._calendar_id, eventId=event_id))
        if _has_attendees(item):
            raise EventHasAttendeesError(event_id)
        return item

    def _execute(self, request):
        try:
            return request.execute()
        except HttpError as error:
            if error.resp.status == 404:
                raise EventNotFoundError(str(error)) from error
            raise CalendarError(str(error)) from error

    def _check_types(self, start, end, all_day: bool) -> None:
        for value in (start, end):
            if all_day and (isinstance(value, datetime) or not isinstance(value, date)):
                raise CalendarError("evento de dia inteiro exige date, não datetime")
            if not all_day and (not isinstance(value, datetime) or value.tzinfo is None):
                raise CalendarError("evento com hora exige datetime com fuso")

    def _time_field(self, value: datetime | date, all_day: bool, clear_other: bool = False) -> dict:
        # events.patch merges nested objects, so when switching between all-day
        # and timed we must explicitly null the keys of the old format.
        if all_day:
            field = {"date": value.isoformat()}
            if clear_other:
                field.update({"dateTime": None, "timeZone": None})
            return field
        field = {
            "dateTime": value.astimezone(self._tz).isoformat(),
            "timeZone": self._tz.key,
        }
        if clear_other:
            field["date"] = None
        return field

    def _parse_time(self, field: dict) -> datetime | date:
        if "dateTime" in field:
            return datetime.fromisoformat(field["dateTime"]).astimezone(self._tz)
        return date.fromisoformat(field["date"])

    def _to_event(self, item: dict) -> CalendarEvent:
        return CalendarEvent(
            id=item["id"],
            title=item.get("summary", ""),
            start=self._parse_time(item["start"]),
            end=self._parse_time(item["end"]),
            all_day="date" in item["start"],
            has_attendees=_has_attendees(item),
        )


def _has_attendees(item: dict) -> bool:
    return any(not a.get("self") for a in item.get("attendees", []))


def build_google_provider(refresh_token: str, settings: Settings) -> GoogleCalendarProvider:
    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )
    service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
    return GoogleCalendarProvider(service, tz=settings.tz)
