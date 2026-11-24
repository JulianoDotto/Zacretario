import pytest

import zacretario.agent  # noqa: F401  (registers the skills)
from zacretario.agent.registry import ToolError, get_tool


def test_update_preferences_formats_result(make_ctx):
    ctx = make_ctx()
    result = get_tool("update_preferences").handler(
        ctx, {"day_start": "07:00", "day_end": None, "blocked_weekdays": [6]}
    )
    assert result == "Janela: 07:00–22:00. Dias bloqueados: domingo"
    assert get_tool("get_preferences").handler(ctx, {}) == result


def test_get_preferences_defaults(make_ctx):
    assert get_tool("get_preferences").handler(make_ctx(), {}) == (
        "Janela: 08:00–22:00. Dias bloqueados: nenhum"
    )


def test_update_preferences_invalid_window_raises_tool_error(make_ctx):
    with pytest.raises(ToolError):
        get_tool("update_preferences").handler(
            make_ctx(), {"day_start": "23:00", "day_end": None, "blocked_weekdays": None}
        )
