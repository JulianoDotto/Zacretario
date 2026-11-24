import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker

from zacretario.agent.agent import Agent
from zacretario.agent.registry import ToolContext
from zacretario.calendar.base import CalendarProvider
from zacretario.channels.whatsapp import IncomingMessage, MessageSender
from zacretario.config import Settings
from zacretario.db import session_scope
from zacretario.repositories import conversation

logger = logging.getLogger(__name__)

NON_TEXT_NOTICE = "Por enquanto eu só entendo mensagens de texto 🙂"
ERROR_MESSAGE = (
    "Tive um problema pra processar isso agora. Antes de mandar de novo, confere com "
    '"o que tenho pra fazer?" se algo já foi registrado.'
)


def resolve_owner(sender: str, allowed_users: dict[str, str]) -> str | None:
    """Find the owner of a sender number, tolerating Brazil's optional 9th digit.

    The Cloud API often delivers Brazilian mobiles as 55 + DDD + 8 digits (12 digits)
    while users configure 55 + DDD + 9 + 8 digits (13 digits), or the other way around.
    """
    if sender in allowed_users:
        return allowed_users[sender]
    for number, owner in allowed_users.items():
        if _without_ninth_digit(number) == _without_ninth_digit(sender):
            return owner
    return None


def _without_ninth_digit(number: str) -> str:
    if number.startswith("55") and len(number) == 13 and number[4] == "9":
        return number[:4] + number[5:]
    return number


@dataclass
class Deps:
    settings: Settings
    session_factory: sessionmaker[Session]
    agent: Agent
    sender: MessageSender
    calendar_for: Callable[[Session, str], CalendarProvider]
    # Must return a UTC-aware datetime: the repositories store it as given.
    clock: Callable[[], datetime]


def handle_message(message: IncomingMessage, deps: Deps) -> None:
    """Runs in a background task, so it must never raise."""
    try:
        owner = resolve_owner(message.sender, deps.settings.allowed_users)
        if owner is None:
            logger.info("Ignoring message from unknown number %s", message.sender)
            return
        with session_scope(deps.session_factory) as session:
            if not conversation.mark_processed(session, message.message_id, deps.clock()):
                return
        _respond(message, owner, deps)
    except Exception:
        logger.exception("Unexpected failure handling message %s", message.message_id)


def _respond(message: IncomingMessage, owner: str, deps: Deps) -> None:
    try:
        if message.type != "text":
            deps.sender.send_text(message.sender, NON_TEXT_NOTICE)
            return
        reply = _run_agent(message, owner, deps)
        if not reply.strip():
            raise ValueError("Agent returned an empty reply")
        deps.sender.send_text(message.sender, reply)
    except Exception:
        logger.exception("Failed to process message %s", message.message_id)
        try:
            deps.sender.send_text(message.sender, ERROR_MESSAGE)
        except Exception:
            logger.exception("Failed to send the error message to %s", message.sender)


def _run_agent(message: IncomingMessage, owner: str, deps: Deps) -> str:
    settings = deps.settings
    text = message.text or ""
    with session_scope(deps.session_factory) as session:
        now = deps.clock()
        history = [
            (m.role, m.text)
            for m in conversation.recent_messages(
                session,
                owner,
                limit=settings.history_limit,
                max_age=timedelta(hours=settings.history_max_age_hours),
                now=now,
            )
        ]
        ctx = ToolContext(
            owner=owner,
            session=session,
            calendar=deps.calendar_for(session, owner),
            tz=settings.tz,
            now=now.astimezone(settings.tz),
        )
        reply = deps.agent.reply(ctx, owner, history, text)
        if reply.strip():
            conversation.append_message(session, owner, "user", text, now)
            conversation.append_message(session, owner, "assistant", reply, deps.clock())
    return reply
