from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from zacretario.agent.registry import Tool, ToolContext, ToolError, register
from zacretario.calendar.base import (
    CalendarError,
    CalendarEvent,
    EventHasAttendeesError,
    EventNotFoundError,
)
from zacretario.repositories import preferences
from zacretario.scheduling import find_free_slots

WEEKDAY_ABBREVIATIONS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
DEFAULT_DURATION = timedelta(hours=1)
ATTENDEES_SUFFIX = " (com convidados — não posso alterar)"


# --- Shared helpers ---------------------------------------------------------


def _parse_date(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise ToolError(f"Data inválida: {text!r} (use AAAA-MM-DD)") from error


def _parse_time(text: str) -> time:
    try:
        return time.fromisoformat(text)
    except ValueError as error:
        raise ToolError(f"Hora inválida: {text!r} (use HH:MM)") from error


def _day_start(day: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, time(0), tzinfo=tz)


def _timed_range(
    day: date, start_time: time, end_time: time | None, tz: ZoneInfo
) -> tuple[datetime, datetime]:
    """No end means one hour; an end at or before the start means the next day."""
    start = datetime.combine(day, start_time, tzinfo=tz)
    if end_time is None:
        return start, start + DEFAULT_DURATION
    end = datetime.combine(day, end_time, tzinfo=tz)
    if end <= start:
        end += timedelta(days=1)
    return start, end


@contextmanager
def _calendar_errors() -> Iterator[None]:
    # Subclasses first: EventNotFoundError and EventHasAttendeesError are CalendarErrors.
    try:
        yield
    except EventHasAttendeesError as error:
        raise ToolError(
            "Este evento tem outros participantes ou foi organizado por outra pessoa, "
            "então não posso alterá-lo nem cancelá-lo."
        ) from error
    except EventNotFoundError as error:
        raise ToolError("Evento não encontrado.") from error
    except CalendarError as error:
        raise ToolError(f"Erro no calendário: {error}") from error


def _format_day(moment: datetime | date) -> str:
    return f"{WEEKDAY_ABBREVIATIONS[moment.weekday()]} {moment:%d/%m}"


def _format_range(start: datetime, end: datetime) -> str:
    return f"{_format_day(start)} {start:%H:%M}–{end:%H:%M}"


def format_event(event: CalendarEvent, tz: ZoneInfo) -> str:
    """One line like 'qui 27/11 10:00–11:00 Dentista'."""
    if event.all_day:
        when = f"{_format_day(event.start)} (dia todo)"
    else:
        when = _format_range(event.start.astimezone(tz), event.end.astimezone(tz))
    suffix = ATTENDEES_SUFFIX if event.has_attendees else ""
    return f"{when} {event.title}{suffix}"


# --- Handlers ---------------------------------------------------------------


def _create_event(ctx: ToolContext, args: dict) -> str:
    day = _parse_date(args["date"])
    if args["start_time"] is None:
        start, end, all_day = day, day + timedelta(days=1), True
    else:
        start_time = _parse_time(args["start_time"])
        end_time = _parse_time(args["end_time"]) if args["end_time"] else None
        start, end = _timed_range(day, start_time, end_time, ctx.tz)
        all_day = False

    with _calendar_errors():
        event = ctx.calendar.create_event(args["title"], start, end, all_day)
    return f"Evento criado (id {event.id}): {format_event(event, ctx.tz)}"


def _list_events(ctx: ToolContext, args: dict) -> str:
    start = _day_start(_parse_date(args["start_date"]), ctx.tz)
    end = _day_start(_parse_date(args["end_date"]) + timedelta(days=1), ctx.tz)

    with _calendar_errors():
        events = ctx.calendar.list_events(start, end)
    if not events:
        return "Nenhum compromisso no período."
    return "\n".join(f"[{event.id}] {format_event(event, ctx.tz)}" for event in events)


def _new_times(
    event: CalendarEvent, args: dict, tz: ZoneInfo
) -> tuple[datetime | date, datetime | date, bool]:
    """Compute the new (start, end, all_day) of an event, keeping its duration when possible."""
    new_day = _parse_date(args["date"]) if args["date"] else None
    start_time = _parse_time(args["start_time"]) if args["start_time"] else None
    end_time = _parse_time(args["end_time"]) if args["end_time"] else None

    if event.all_day:
        if start_time is not None:  # all-day becomes a timed event
            start, end = _timed_range(new_day or event.start, start_time, end_time, tz)
            return start, end, False
        if end_time is not None:
            raise ToolError("Evento de dia inteiro não tem horário de fim; informe start_time.")
        return new_day, new_day + (event.end - event.start), True

    local_start = event.start.astimezone(tz)
    duration = event.end - event.start
    day = new_day or local_start.date()
    start = datetime.combine(day, start_time or local_start.time(), tzinfo=tz)
    if end_time is None:
        return start, start + duration, False
    return (*_timed_range(day, start.time(), end_time, tz), False)


def _update_event(ctx: ToolContext, args: dict) -> str:
    changes_time = any(args[key] for key in ("date", "start_time", "end_time"))
    if not changes_time and not args["title"]:
        raise ToolError("Nada para alterar: informe título, data ou horário.")

    with _calendar_errors():
        kwargs: dict = {"title": args["title"]}
        if changes_time:
            event = ctx.calendar.get_event(args["event_id"])
            start, end, all_day = _new_times(event, args, ctx.tz)
            kwargs.update(start=start, end=end, all_day=all_day)
        updated = ctx.calendar.update_event(args["event_id"], **kwargs)
    return f"Evento atualizado (id {updated.id}): {format_event(updated, ctx.tz)}"


def _delete_event(ctx: ToolContext, args: dict) -> str:
    with _calendar_errors():
        ctx.calendar.delete_event(args["event_id"])
    return f"Evento {args['event_id']} apagado."


def _find_free_slots(ctx: ToolContext, args: dict) -> str:
    if args["duration_minutes"] <= 0:
        raise ToolError("A duração deve ser maior que zero.")
    first_day = _parse_date(args["start_date"])
    last_day = _parse_date(args["end_date"])

    availability = preferences.get_availability(ctx.session, ctx.owner)
    if args["earliest_time"]:
        availability = replace(availability, day_start=_parse_time(args["earliest_time"]))
    if args["latest_time"]:
        availability = replace(availability, day_end=_parse_time(args["latest_time"]))
    if availability.day_start >= availability.day_end:
        raise ToolError("O horário inicial deve ser anterior ao final.")

    range_start = max(_day_start(first_day, ctx.tz), ctx.now.astimezone(ctx.tz))
    range_end = _day_start(last_day + timedelta(days=1), ctx.tz)
    with _calendar_errors():
        events = ctx.calendar.list_events(range_start, range_end)
    busy = [(event.start, event.end) for event in events if not event.all_day]

    slots = find_free_slots(
        busy,
        range_start=range_start,
        range_end=range_end,
        duration=timedelta(minutes=args["duration_minutes"]),
        availability=availability,
        tz=ctx.tz,
    )
    if not slots:
        return "Nenhum horário livre encontrado."
    return "\n".join(_format_range(start, end) for start, end in slots)


# --- Registration -----------------------------------------------------------


def _nullable(type_: str, description: str) -> dict:
    return {"anyOf": [{"type": type_}, {"type": "null"}], "description": description}


_DATE = "Data no formato AAAA-MM-DD."
_TIME = "Hora no formato HH:MM."


def _schema(properties: dict) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


register(
    Tool(
        name="create_event",
        description=(
            "Cria um compromisso no calendário. Sem start_time vira evento de dia inteiro; "
            "sem end_time dura 1 hora. Se end_time for menor ou igual a start_time, "
            "termina no dia seguinte."
        ),
        input_schema=_schema(
            {
                "title": {"type": "string", "description": "Título do evento."},
                "date": {"type": "string", "description": _DATE},
                "start_time": _nullable("string", _TIME),
                "end_time": _nullable("string", _TIME),
            }
        ),
        handler=_create_event,
    )
)
register(
    Tool(
        name="list_events",
        description="Lista os compromissos do calendário entre duas datas (inclusivas).",
        input_schema=_schema(
            {
                "start_date": {"type": "string", "description": _DATE},
                "end_date": {"type": "string", "description": _DATE},
            }
        ),
        handler=_list_events,
    )
)
register(
    Tool(
        name="update_event",
        description=(
            "Altera um compromisso (id vindo de list_events). Use null no que não deve mudar. "
            "Mudando só a data ou o início, a duração original é mantida. "
            "Eventos com convidados ou organizados por outra pessoa não podem ser alterados."
        ),
        input_schema=_schema(
            {
                "event_id": {"type": "string", "description": "Id do evento."},
                "title": _nullable("string", "Novo título."),
                "date": _nullable("string", _DATE),
                "start_time": _nullable("string", _TIME),
                "end_time": _nullable("string", _TIME),
            }
        ),
        handler=_update_event,
    )
)
register(
    Tool(
        name="delete_event",
        description=(
            "Apaga um compromisso (id vindo de list_events). "
            "Eventos com convidados ou organizados por outra pessoa não podem ser apagados."
        ),
        input_schema=_schema({"event_id": {"type": "string", "description": "Id do evento."}}),
        handler=_delete_event,
    )
)
register(
    Tool(
        name="find_free_slots",
        description=(
            "Sugere horários livres (no máximo um por dia) respeitando a janela de horário do "
            "usuário. earliest_time/latest_time sobrescrevem a janela só nesta busca."
        ),
        input_schema=_schema(
            {
                "start_date": {"type": "string", "description": _DATE},
                "end_date": {"type": "string", "description": _DATE},
                "duration_minutes": {"type": "integer", "description": "Duração em minutos."},
                "earliest_time": _nullable("string", _TIME),
                "latest_time": _nullable("string", _TIME),
            }
        ),
        handler=_find_free_slots,
    )
)
