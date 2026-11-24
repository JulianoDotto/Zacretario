from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from fakes import FakeCalendar

from zacretario.agent import calendar_tools  # noqa: F401  (registers the tools)
from zacretario.agent.registry import ToolError, get_tool

SP = ZoneInfo("America/Sao_Paulo")


@pytest.fixture
def ctx(make_ctx):
    context = make_ctx()
    context.calendar = FakeCalendar()
    return context


def run(ctx, name: str, **args) -> str:
    return get_tool(name).handler(ctx, args)


def create(ctx, title="Dentista", date="2026-11-27", start_time=None, end_time=None) -> str:
    return run(
        ctx, "create_event", title=title, date=date, start_time=start_time, end_time=end_time
    )


def test_create_timed_event_defaults_to_one_hour(ctx):
    result = create(ctx, start_time="10:00")

    event = next(iter(ctx.calendar.events.values()))
    assert event.start == datetime(2026, 11, 27, 10, 0, tzinfo=SP)
    assert event.end == datetime(2026, 11, 27, 11, 0, tzinfo=SP)
    assert result == f"Evento criado (id {event.id}): sex 27/11 10:00–11:00 Dentista"


def test_create_all_day_event(ctx):
    create(ctx, title="Feriado")

    event = next(iter(ctx.calendar.events.values()))
    assert event.all_day is True
    assert event.start == date(2026, 11, 27)
    assert event.end == date(2026, 11, 28)


def test_create_event_crossing_midnight(ctx):
    create(ctx, title="Festa", start_time="23:30")

    event = next(iter(ctx.calendar.events.values()))
    assert event.end == datetime(2026, 11, 28, 0, 30, tzinfo=SP)


def test_create_event_with_end_before_start_ends_next_day(ctx):
    create(ctx, title="Festa", start_time="22:00", end_time="02:00")

    event = next(iter(ctx.calendar.events.values()))
    assert event.end == datetime(2026, 11, 28, 2, 0, tzinfo=SP)


def test_create_event_with_bad_date_is_tool_error(ctx):
    with pytest.raises(ToolError):
        create(ctx, date="amanhã")
    with pytest.raises(ToolError):
        create(ctx, start_time="dez da manhã")


def test_list_events_marks_attendees_and_all_day(ctx):
    ctx.calendar.add_event(
        "Dentista",
        datetime(2026, 11, 27, 10, 0, tzinfo=SP),
        datetime(2026, 11, 27, 11, 0, tzinfo=SP),
    )
    ctx.calendar.add_event("Feriado", date(2026, 11, 28), date(2026, 11, 29), all_day=True)
    ctx.calendar.add_event(
        "Reunião",
        datetime(2026, 11, 30, 9, 0, tzinfo=SP),
        datetime(2026, 11, 30, 10, 0, tzinfo=SP),
        has_attendees=True,
    )

    result = run(ctx, "list_events", start_date="2026-11-27", end_date="2026-11-30")

    assert result.splitlines() == [
        "[ev1] sex 27/11 10:00–11:00 Dentista",
        "[ev2] sáb 28/11 (dia todo) Feriado",
        "[ev3] seg 30/11 09:00–10:00 Reunião (com convidados — não posso alterar)",
    ]


def test_list_events_empty(ctx):
    result = run(ctx, "list_events", start_date="2026-11-27", end_date="2026-11-27")

    assert result == "Nenhum compromisso no período."


def test_delete_event(ctx):
    event = ctx.calendar.add_event("X", date(2026, 11, 27), date(2026, 11, 28), all_day=True)

    run(ctx, "delete_event", event_id=event.id)

    assert ctx.calendar.events == {}


def test_delete_event_with_attendees_returns_tool_error(ctx):
    event = ctx.calendar.add_event(
        "Reunião",
        datetime(2026, 11, 27, 9, 0, tzinfo=SP),
        datetime(2026, 11, 27, 10, 0, tzinfo=SP),
        has_attendees=True,
    )

    with pytest.raises(ToolError, match="convidados"):
        run(ctx, "delete_event", event_id=event.id)
    assert event.id in ctx.calendar.events


def test_delete_missing_event_returns_tool_error(ctx):
    with pytest.raises(ToolError, match="não encontrado"):
        run(ctx, "delete_event", event_id="nope")


def update(ctx, event_id, title=None, date=None, start_time=None, end_time=None) -> str:
    return run(
        ctx,
        "update_event",
        event_id=event_id,
        title=title,
        date=date,
        start_time=start_time,
        end_time=end_time,
    )


def test_update_event_title_only(ctx):
    event = ctx.calendar.add_event(
        "Dentista",
        datetime(2026, 11, 27, 10, 0, tzinfo=SP),
        datetime(2026, 11, 27, 11, 0, tzinfo=SP),
    )

    update(ctx, event.id, title="Ortodontista")

    updated = ctx.calendar.events[event.id]
    assert updated.title == "Ortodontista"
    assert updated.start == event.start


def test_update_event_keeps_duration_when_moving_date(ctx):
    event = ctx.calendar.add_event(
        "Workshop",
        datetime(2026, 11, 27, 14, 0, tzinfo=SP),
        datetime(2026, 11, 27, 16, 0, tzinfo=SP),
    )

    update(ctx, event.id, date="2026-11-30")

    updated = ctx.calendar.events[event.id]
    assert updated.start == datetime(2026, 11, 30, 14, 0, tzinfo=SP)
    assert updated.end == datetime(2026, 11, 30, 16, 0, tzinfo=SP)


def test_update_event_keeps_duration_when_moving_start_time(ctx):
    event = ctx.calendar.add_event(
        "Workshop",
        datetime(2026, 11, 27, 14, 0, tzinfo=SP),
        datetime(2026, 11, 27, 16, 0, tzinfo=SP),
    )

    update(ctx, event.id, start_time="09:30")

    updated = ctx.calendar.events[event.id]
    assert updated.start == datetime(2026, 11, 27, 9, 30, tzinfo=SP)
    assert updated.end == datetime(2026, 11, 27, 11, 30, tzinfo=SP)


def test_update_event_end_time_only(ctx):
    event = ctx.calendar.add_event(
        "Workshop",
        datetime(2026, 11, 27, 14, 0, tzinfo=SP),
        datetime(2026, 11, 27, 16, 0, tzinfo=SP),
    )

    update(ctx, event.id, end_time="17:00")

    updated = ctx.calendar.events[event.id]
    assert updated.start == event.start
    assert updated.end == datetime(2026, 11, 27, 17, 0, tzinfo=SP)


def test_update_all_day_event_moves_date(ctx):
    event = ctx.calendar.add_event("Feriado", date(2026, 11, 27), date(2026, 11, 28), all_day=True)

    update(ctx, event.id, date="2026-11-30")

    updated = ctx.calendar.events[event.id]
    assert updated.all_day is True
    assert (updated.start, updated.end) == (date(2026, 11, 30), date(2026, 12, 1))


def test_update_all_day_event_to_timed(ctx):
    event = ctx.calendar.add_event("Feriado", date(2026, 11, 27), date(2026, 11, 28), all_day=True)

    update(ctx, event.id, start_time="10:00")

    updated = ctx.calendar.events[event.id]
    assert updated.all_day is False
    assert updated.start == datetime(2026, 11, 27, 10, 0, tzinfo=SP)
    assert updated.end == datetime(2026, 11, 27, 11, 0, tzinfo=SP)


def test_update_event_with_attendees_returns_tool_error(ctx):
    event = ctx.calendar.add_event(
        "Reunião",
        datetime(2026, 11, 27, 9, 0, tzinfo=SP),
        datetime(2026, 11, 27, 10, 0, tzinfo=SP),
        has_attendees=True,
    )

    with pytest.raises(ToolError, match="convidados"):
        update(ctx, event.id, date="2026-11-30")


def test_update_event_without_changes_is_tool_error(ctx):
    event = ctx.calendar.add_event("X", date(2026, 11, 27), date(2026, 11, 28), all_day=True)

    with pytest.raises(ToolError):
        update(ctx, event.id)


def find(ctx, **overrides) -> str:
    args = {
        "start_date": "2026-11-30",
        "end_date": "2026-11-30",
        "duration_minutes": 60,
        "earliest_time": None,
        "latest_time": None,
    } | overrides
    return run(ctx, "find_free_slots", **args)


def test_find_free_slots_ignores_all_day_and_past(ctx):
    ctx.now = datetime(2026, 11, 30, 15, 10, tzinfo=SP)
    ctx.calendar.add_event("Feriado", date(2026, 11, 30), date(2026, 12, 1), all_day=True)

    assert find(ctx) == "seg 30/11 15:15–16:15"


def test_find_free_slots_avoids_busy_with_buffer(ctx):
    ctx.now = datetime(2026, 11, 24, 12, 0, tzinfo=SP)
    ctx.calendar.add_event(
        "Reunião",
        datetime(2026, 11, 30, 8, 0, tzinfo=SP),
        datetime(2026, 11, 30, 10, 0, tzinfo=SP),
    )

    assert find(ctx) == "seg 30/11 10:15–11:15"


def test_find_free_slots_window_override(ctx):
    ctx.now = datetime(2026, 11, 24, 12, 0, tzinfo=SP)

    assert find(ctx, earliest_time="18:00", latest_time="20:00") == "seg 30/11 18:00–19:00"


def test_find_free_slots_none_found(ctx):
    ctx.now = datetime(2026, 11, 24, 12, 0, tzinfo=SP)

    assert find(ctx, duration_minutes=60 * 20) == "Nenhum horário livre encontrado."


def test_find_free_slots_bad_input_is_tool_error(ctx):
    with pytest.raises(ToolError):
        find(ctx, duration_minutes=0)
    with pytest.raises(ToolError):
        find(ctx, earliest_time="22:00", latest_time="08:00")
    with pytest.raises(ToolError):
        find(ctx, start_date="segunda")
