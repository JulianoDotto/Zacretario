import logging

import pytest
from fakes import FakeAnthropic, response, text_block, tool_use_block

import zacretario.agent  # noqa: F401  (registers the skills)
from zacretario.agent.agent import REFUSAL_MESSAGE, Agent, AgentError
from zacretario.agent.registry import Tool, all_tools
from zacretario.repositories.todos import list_open_todos

MODEL = "claude-sonnet-5-5"


def make_agent(client, tools=None, max_iterations=8) -> Agent:
    return Agent(client, MODEL, tools or all_tools(), max_iterations=max_iterations)


def last_user_content(call: dict) -> list:
    message = call["messages"][-1]
    assert message["role"] == "user"
    return message["content"]


def test_plain_answer_returns_text(make_ctx):
    client = FakeAnthropic([response("end_turn", text_block("Oi, Juliano! "))])
    assert make_agent(client).reply(make_ctx(), "Juliano", [], "oi") == "Oi, Juliano!"


def test_executes_tool_and_returns_final_text(make_ctx, session):
    client = FakeAnthropic(
        [
            response("tool_use", tool_use_block("tu_1", "add_todo", {"text": "Comprar ração"})),
            response("end_turn", text_block("✅ Anotado")),
        ]
    )
    ctx = make_ctx()

    assert make_agent(client).reply(ctx, "Juliano", [], "comprar ração") == "✅ Anotado"
    assert [todo.text for todo in list_open_todos(session, ctx.owner)] == ["Comprar ração"]

    second = client.calls[1]
    assert second["messages"][-2]["role"] == "assistant"
    [result] = last_user_content(second)
    assert result["type"] == "tool_result"
    assert result["tool_use_id"] == "tu_1"
    assert "Comprar ração" in result["content"]
    assert not result.get("is_error")


def test_parallel_tool_calls_return_single_user_message(make_ctx):
    client = FakeAnthropic(
        [
            response(
                "tool_use",
                text_block("Vou anotar."),
                tool_use_block("tu_1", "add_todo", {"text": "a"}),
                tool_use_block("tu_2", "add_todo", {"text": "b"}),
            ),
            response("end_turn", text_block("Pronto")),
        ]
    )
    make_agent(client).reply(make_ctx(), "Juliano", [], "anota a e b")

    messages = client.calls[1]["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert len(messages[1]["content"]) == 3  # assistant content is kept whole
    results = messages[2]["content"]
    assert [r["tool_use_id"] for r in results] == ["tu_1", "tu_2"]
    assert all(r["type"] == "tool_result" for r in results)


def test_tool_error_is_reported_to_model(make_ctx):
    client = FakeAnthropic(
        [
            response("tool_use", tool_use_block("tu_1", "complete_todo", {"todo_id": 999})),
            response("end_turn", text_block("Não achei esse TODO.")),
        ]
    )
    reply = make_agent(client).reply(make_ctx(), "Juliano", [], "conclui o 999")

    assert reply == "Não achei esse TODO."
    [result] = last_user_content(client.calls[1])
    assert result["is_error"] is True
    assert "999" in result["content"]


def test_unknown_tool_and_unexpected_exception_become_errors(make_ctx, caplog):
    def explode(ctx, args):
        raise RuntimeError("segredo interno")

    boom = Tool("boom", "Explode.", {"type": "object", "properties": {}}, explode)
    client = FakeAnthropic(
        [
            response(
                "tool_use",
                tool_use_block("tu_1", "boom", {}),
                tool_use_block("tu_2", "nao_existe", {}),
            ),
            response("end_turn", text_block("Tive um problema.")),
        ]
    )
    with caplog.at_level(logging.ERROR):
        reply = make_agent(client, tools=[boom]).reply(make_ctx(), "Juliano", [], "x")

    assert reply == "Tive um problema."
    boom_result, unknown_result = last_user_content(client.calls[1])
    assert boom_result["is_error"] is True
    assert "segredo interno" not in boom_result["content"]
    assert unknown_result["is_error"] is True
    assert "nao_existe" in unknown_result["content"]
    assert "segredo interno" in caplog.text


def test_refusal_returns_polite_message(make_ctx):
    client = FakeAnthropic([response("refusal")])
    reply = make_agent(client).reply(make_ctx(), "Juliano", [], "algo proibido")
    assert reply == REFUSAL_MESSAGE
    assert reply == (
        "Desculpe, não posso ajudar com isso. Posso cuidar da sua agenda e das suas tarefas 🙂"
    )


def test_pause_turn_continues_the_loop(make_ctx):
    client = FakeAnthropic(
        [
            response("pause_turn", text_block("Pensando...")),
            response("end_turn", text_block("Feito")),
        ]
    )
    assert make_agent(client).reply(make_ctx(), "Juliano", [], "oi") == "Feito"
    assert client.calls[1]["messages"][-1]["role"] == "assistant"


def test_max_tokens_raises_agent_error(make_ctx):
    client = FakeAnthropic([response("max_tokens", text_block("cortad"))])
    with pytest.raises(AgentError):
        make_agent(client).reply(make_ctx(), "Juliano", [], "oi")


def test_iteration_cap_raises_agent_error(make_ctx):
    client = FakeAnthropic(
        lambda i: response("tool_use", tool_use_block(f"tu_{i}", "list_todos", {}))
    )
    with pytest.raises(AgentError):
        make_agent(client, max_iterations=3).reply(make_ctx(), "Juliano", [], "loop")
    assert len(client.calls) == 3


def test_request_shape(make_ctx):
    client = FakeAnthropic([response("end_turn", text_block("ok"))])
    history = [("user", "oi"), ("assistant", "Olá!")]
    make_agent(client).reply(make_ctx(), "Juliano", history, "tenho algo amanhã?")

    [call] = client.calls
    assert call["model"] == MODEL
    assert call["max_tokens"] == 16000
    assert call["fallbacks"] == "default"
    assert call["output_config"] == {"effort": "medium"}
    assert call["betas"] == ["server-side-fallback-2026-07-01"]
    assert "Juliano" in call["system"]
    # ctx.now is 12:00 UTC; the prompt shows it in the user's timezone.
    assert "terça-feira, 24/11/2026 09:00" in call["system"]
    assert {tool["name"] for tool in call["tools"]} >= {"add_todo", "list_events"}
    for forbidden in ("tool_choice", "thinking", "temperature", "top_p", "top_k"):
        assert forbidden not in call
    assert call["messages"] == [
        {"role": "user", "content": "oi"},
        {"role": "assistant", "content": "Olá!"},
        {"role": "user", "content": "tenho algo amanhã?"},
    ]


def test_history_is_normalized_to_alternate_roles(make_ctx):
    client = FakeAnthropic([response("end_turn", text_block("ok"))])
    history = [
        ("assistant", "lembrete solto"),
        ("user", "a"),
        ("user", "b"),
        ("assistant", "c"),
    ]
    make_agent(client).reply(make_ctx(), "Juliano", history, "d")

    assert client.calls[0]["messages"] == [
        {"role": "user", "content": "a\n\nb"},
        {"role": "assistant", "content": "c"},
        {"role": "user", "content": "d"},
    ]


def test_history_ending_with_user_is_merged_with_new_message(make_ctx):
    client = FakeAnthropic([response("end_turn", text_block("ok"))])
    make_agent(client).reply(make_ctx(), "Juliano", [("user", "a")], "b")
    assert client.calls[0]["messages"] == [{"role": "user", "content": "a\n\nb"}]
