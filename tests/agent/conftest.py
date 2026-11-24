from datetime import UTC, datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from zacretario.agent.registry import ToolContext


@pytest.fixture
def make_ctx(session):
    def build(owner: str = "juliano") -> ToolContext:
        return ToolContext(
            owner=owner,
            session=session,
            calendar=MagicMock(),
            tz=ZoneInfo("America/Sao_Paulo"),
            now=datetime(2026, 11, 24, 12, 0, tzinfo=UTC),
        )

    return build
