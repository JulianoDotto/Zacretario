from datetime import UTC, datetime, time

from sqlalchemy import DateTime, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column

from zacretario.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[str] = mapped_column(String(64), index=True)
    text: Mapped[str] = mapped_column(Text)
    done: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    owner: Mapped[str] = mapped_column(String(64), primary_key=True)
    day_start: Mapped[time] = mapped_column(Time, default=time(8, 0))
    day_end: Mapped[time] = mapped_column(Time, default=time(22, 0))
    # Comma-separated weekday numbers, 0 = Monday (e.g. "5,6")
    blocked_weekdays: Mapped[str] = mapped_column(String(32), default="")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" or "assistant"
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProcessedMessage(Base):
    __tablename__ = "processed_messages"

    message_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GoogleCredential(Base):
    __tablename__ = "google_credentials"

    owner: Mapped[str] = mapped_column(String(64), primary_key=True)
    refresh_token: Mapped[str] = mapped_column(Text)
