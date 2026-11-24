from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zacretario.models import ConversationMessage, ProcessedMessage


def append_message(session: Session, owner: str, role: str, text: str, now: datetime) -> None:
    session.add(ConversationMessage(owner=owner, role=role, text=text, created_at=now))
    session.commit()


def recent_messages(
    session: Session, owner: str, *, limit: int, max_age: timedelta, now: datetime
) -> list[ConversationMessage]:
    # Filter by age in SQL: SQLite drops tzinfo on read, so Python-side comparisons would break.
    cutoff = now.astimezone(UTC) - max_age
    query = (
        select(ConversationMessage)
        .where(ConversationMessage.owner == owner, ConversationMessage.created_at >= cutoff)
        .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
        .limit(limit)
    )
    return list(reversed(session.scalars(query).all()))


def mark_processed(session: Session, message_id: str, now: datetime) -> bool:
    """Return True if the message is new, False if it was already seen."""
    try:
        with session.begin_nested():
            session.add(ProcessedMessage(message_id=message_id, received_at=now))
    except IntegrityError:
        return False
    session.commit()
    return True
