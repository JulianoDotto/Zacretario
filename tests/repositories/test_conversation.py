from datetime import UTC, datetime, timedelta

from zacretario.repositories.conversation import append_message, mark_processed, recent_messages
from zacretario.repositories.credentials import get_refresh_token, save_refresh_token

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)


def test_recent_messages_limit_and_age(session):
    append_message(session, "juliano", "user", "antiga", NOW - timedelta(hours=30))
    for i in range(24):
        append_message(session, "juliano", "user", f"msg {i}", NOW - timedelta(minutes=24 - i))

    messages = recent_messages(session, "juliano", limit=20, max_age=timedelta(hours=24), now=NOW)

    assert [m.text for m in messages] == [f"msg {i}" for i in range(4, 24)]


def test_recent_messages_isolated_by_owner(session):
    append_message(session, "juliano", "user", "meu", NOW)
    append_message(session, "maria", "user", "dela", NOW)

    messages = recent_messages(session, "juliano", limit=20, max_age=timedelta(hours=24), now=NOW)

    assert [m.text for m in messages] == ["meu"]


def test_mark_processed_is_idempotent(session):
    assert mark_processed(session, "wamid.1", NOW) is True
    assert mark_processed(session, "wamid.1", NOW) is False
    assert mark_processed(session, "wamid.2", NOW) is True


def test_save_refresh_token_upserts(session):
    assert get_refresh_token(session, "juliano") is None

    save_refresh_token(session, "juliano", "primeiro")
    save_refresh_token(session, "juliano", "segundo")

    assert get_refresh_token(session, "juliano") == "segundo"
