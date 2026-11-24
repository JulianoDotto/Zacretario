import pytest

import zacretario.agent  # noqa: F401  (registers the skills)
from zacretario.agent.registry import ToolError, all_tools, get_tool, to_api_params
from zacretario.repositories.todos import add_todo


def test_add_and_list_todos_via_tools(make_ctx):
    ctx = make_ctx()
    created = get_tool("add_todo").handler(ctx, {"text": "comprar leite"})
    listed = get_tool("list_todos").handler(ctx, {})
    assert created.startswith("TODO #") and created.endswith("criado: comprar leite")
    assert listed.startswith("#") and listed.endswith(" comprar leite")


def test_complete_unknown_todo_raises_tool_error(make_ctx):
    with pytest.raises(ToolError, match="TODO #999 não encontrado"):
        get_tool("complete_todo").handler(make_ctx(), {"todo_id": 999})


def test_complete_and_delete_todo(make_ctx):
    ctx = make_ctx()
    get_tool("add_todo").handler(ctx, {"text": "a"})
    get_tool("add_todo").handler(ctx, {"text": "b"})
    lines = get_tool("list_todos").handler(ctx, {}).splitlines()
    first, second = (int(line.split()[0][1:]) for line in lines)

    assert get_tool("complete_todo").handler(ctx, {"todo_id": first}) == (
        f"TODO #{first} concluído: a"
    )
    assert get_tool("delete_todo").handler(ctx, {"todo_id": second}) == f"TODO #{second} apagado"
    assert get_tool("list_todos").handler(ctx, {}) == "Nenhum TODO em aberto."
    with pytest.raises(ToolError):
        get_tool("delete_todo").handler(ctx, {"todo_id": second})


def test_tools_are_scoped_to_context_owner(session, make_ctx):
    add_todo(session, "bruna", "tarefa da bruna")
    assert get_tool("list_todos").handler(make_ctx("juliano"), {}) == "Nenhum TODO em aberto."
    assert "tarefa da bruna" in get_tool("list_todos").handler(make_ctx("bruna"), {})


def test_registry_api_params_are_strict():
    params = to_api_params(all_tools())
    assert params
    for item in params:
        assert item["strict"] is True
        assert item["input_schema"]["additionalProperties"] is False
        assert set(item["input_schema"]["required"]) == set(item["input_schema"]["properties"])
