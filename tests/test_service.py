from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from zacretario.channels.whatsapp import IncomingMessage
from zacretario.config import Settings
from zacretario.repositories.conversation import recent_messages
from zacretario.service import Deps, handle_message, resolve_owner

PHONE = "5511999990000"
NOTICE = "Por enquanto eu só entendo mensagens de texto 🙂"
APOLOGY = (
    "Tive um problema pra processar isso agora. Antes de mandar de novo, confere com "
    '"o que tenho pra fazer?" se algo já foi registrado.'
)


class FakeSender:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    def send_text(self, to, text):
        self.sent.append((to, text))


class FakeAgent:
    def __init__(self, reply="Feito!"):
        self.reply_value = reply
        self.error: Exception | None = None
        self.calls: list[dict] = []

    def reply(self, ctx, user_name, history, text):
        self.calls.append({"ctx": ctx, "user_name": user_name, "history": history, "text": text})
        if self.error:
            raise self.error
        return self.reply_value


def make_message(message_id="wamid.1", sender=PHONE, type="text", text="oi"):
    return IncomingMessage(message_id=message_id, sender=sender, type=type, text=text)


@pytest.fixture
def sender():
    return FakeSender()


@pytest.fixture
def agent():
    return FakeAgent()


@pytest.fixture
def clock():
    state = {"now": datetime(2026, 11, 24, 15, 0, tzinfo=UTC)}

    def now():
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return now


@pytest.fixture
def deps(session_factory, sender, agent, clock):
    settings = Settings.model_construct(
        allowed_users={PHONE: "juliano"},
        history_limit=20,
        history_max_age_hours=24,
        timezone="America/Sao_Paulo",
    )
    return Deps(
        settings=settings,
        session_factory=session_factory,
        agent=agent,
        sender=sender,
        calendar_for=lambda session, owner: MagicMock(),
        clock=clock,
    )


def stored(session, clock):
    return [
        (m.role, m.text)
        for m in recent_messages(
            session, "juliano", limit=50, max_age=timedelta(hours=48), now=clock()
        )
    ]


def test_unknown_number_is_ignored(deps, sender, agent):
    handle_message(make_message(sender="5500000000000"), deps)
    assert sender.sent == []
    assert agent.calls == []


def test_duplicate_message_processed_once(deps, sender):
    message = make_message()
    handle_message(message, deps)
    handle_message(message, deps)
    assert sender.sent == [(PHONE, "Feito!")]


def test_non_text_gets_polite_notice(deps, sender, agent):
    handle_message(make_message(type="audio", text=None), deps)
    assert sender.sent == [(PHONE, NOTICE)]
    assert agent.calls == []


def test_reply_is_sent_and_history_saved(deps, sender, session, clock):
    handle_message(make_message(text="marca dentista"), deps)
    assert sender.sent == [(PHONE, "Feito!")]
    assert stored(session, clock) == [("user", "marca dentista"), ("assistant", "Feito!")]


def test_context_uses_owner_name_and_local_time(deps, agent):
    handle_message(make_message(), deps)
    call = agent.calls[0]
    assert call["user_name"] == "juliano"
    assert call["ctx"].owner == "juliano"
    assert call["ctx"].now.utcoffset() == timedelta(hours=-3)


def test_history_is_passed_to_agent(deps, agent):
    handle_message(make_message("wamid.1", text="primeira"), deps)
    handle_message(make_message("wamid.2", text="segunda"), deps)
    assert agent.calls[0]["history"] == []
    assert agent.calls[1]["history"] == [("user", "primeira"), ("assistant", "Feito!")]
    assert agent.calls[1]["text"] == "segunda"


def test_agent_failure_sends_apology(deps, sender, agent, session, clock):
    agent.error = RuntimeError("boom")
    handle_message(make_message(), deps)
    assert sender.sent == [(PHONE, APOLOGY)]
    assert stored(session, clock) == []


def test_blank_reply_sends_apology_and_saves_nothing(deps, sender, agent, session, clock):
    agent.reply_value = "  "
    handle_message(make_message(), deps)
    assert sender.sent == [(PHONE, APOLOGY)]
    assert stored(session, clock) == []


def test_failing_apology_does_not_propagate(deps, sender, agent):
    agent.error = RuntimeError("boom")

    def broken_send(to, text):
        raise ConnectionError("down")

    sender.send_text = broken_send
    handle_message(make_message(), deps)


def test_resolve_owner_exact_match():
    assert resolve_owner("5511999990000", {"5511999990000": "juliano"}) == "juliano"


def test_resolve_owner_sender_without_ninth_digit():
    assert resolve_owner("551199990000", {"5511999990000": "juliano"}) == "juliano"


def test_resolve_owner_configured_without_ninth_digit():
    assert resolve_owner("5511999990000", {"551199990000": "juliano"}) == "juliano"


def test_resolve_owner_does_not_fuzz_non_brazilian_numbers():
    assert resolve_owner("14155550123", {"141555550123": "ana"}) is None
    assert resolve_owner("441234567890", {"4412345678900": "ana"}) is None


def test_resolve_owner_unknown_number():
    assert resolve_owner("5521988887777", {"5511999990000": "juliano"}) is None


def test_message_from_number_without_ninth_digit_replies_to_sender(deps, sender):
    handle_message(make_message(sender="551199990000"), deps)

    assert sender.sent == [("551199990000", "Feito!")]
