from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from zacretario.calendar.base import CalendarProvider


@dataclass
class ToolContext:
    owner: str
    session: Session
    calendar: CalendarProvider
    tz: ZoneInfo
    now: datetime


class ToolError(Exception):
    """Shown to the model as an `is_error` tool result."""


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable[[ToolContext, dict], str]


_tools: dict[str, Tool] = {}


def register(tool: Tool) -> Tool:
    if tool.name in _tools:
        raise ValueError(f"Tool already registered: {tool.name}")
    _tools[tool.name] = tool
    return tool


def all_tools() -> list[Tool]:
    return list(_tools.values())


def get_tool(name: str) -> Tool:
    return _tools[name]


def to_api_params(tools: list[Tool]) -> list[dict]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
            "strict": True,
        }
        for tool in tools
    ]
