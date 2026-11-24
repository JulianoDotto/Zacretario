from datetime import time

from zacretario.agent.registry import Tool, ToolContext, ToolError, register
from zacretario.repositories import preferences

WEEKDAY_NAMES = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _describe(ctx: ToolContext) -> str:
    availability = preferences.get_availability(ctx.session, ctx.owner)
    blocked = ", ".join(WEEKDAY_NAMES[day] for day in sorted(availability.blocked_weekdays))
    return (
        f"Janela: {availability.day_start:%H:%M}–{availability.day_end:%H:%M}. "
        f"Dias bloqueados: {blocked or 'nenhum'}"
    )


def _get_preferences(ctx: ToolContext, args: dict) -> str:
    return _describe(ctx)


def _update_preferences(ctx: ToolContext, args: dict) -> str:
    try:
        day_start = time.fromisoformat(args["day_start"]) if args["day_start"] else None
        day_end = time.fromisoformat(args["day_end"]) if args["day_end"] else None
        blocked = set(args["blocked_weekdays"]) if args["blocked_weekdays"] is not None else None
        preferences.update_availability(
            ctx.session,
            ctx.owner,
            day_start=day_start,
            day_end=day_end,
            blocked_weekdays=blocked,
        )
    except ValueError as error:
        raise ToolError(str(error)) from error
    return _describe(ctx)


register(
    Tool(
        name="get_preferences",
        description="Mostra a janela de horário e os dias bloqueados para encaixar eventos.",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        handler=_get_preferences,
    )
)
register(
    Tool(
        name="update_preferences",
        description=(
            "Altera a janela de horário e/ou os dias bloqueados. "
            "Use null nos campos que não devem mudar."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "day_start": {
                    "type": ["string", "null"],
                    "description": "Início do dia no formato HH:MM.",
                },
                "day_end": {
                    "type": ["string", "null"],
                    "description": "Fim do dia no formato HH:MM.",
                },
                "blocked_weekdays": {
                    "type": ["array", "null"],
                    "items": {"type": "integer"},
                    "description": "Dias bloqueados (0=segunda a 6=domingo); [] libera.",
                },
            },
            "required": ["day_start", "day_end", "blocked_weekdays"],
            "additionalProperties": False,
        },
        handler=_update_preferences,
    )
)
