import hashlib
import hmac
import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import zacretario.models  # noqa: F401
from zacretario import main
from zacretario.config import Settings
from zacretario.db import Base
from zacretario.service import Deps

PHONE = "5511999990000"
SECRET = "app-secret"
VERIFY_TOKEN = "verify-me"


class FakeSender:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    def send_text(self, to, text):
        self.sent.append((to, text))


class FakeAgent:
    def reply(self, ctx, user_name, history, text):
        return "Feito!"


@pytest.fixture
def sender():
    return FakeSender()


@pytest.fixture
def session_factory():
    # Background tasks run in a worker thread, so the in-memory SQLite connection must be shared.
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def client(session_factory, sender):
    settings = Settings.model_construct(
        allowed_users={PHONE: "juliano"},
        history_limit=20,
        history_max_age_hours=24,
        timezone="America/Sao_Paulo",
        whatsapp_app_secret=SECRET,
        whatsapp_verify_token=VERIFY_TOKEN,
    )
    deps = Deps(
        settings=settings,
        session_factory=session_factory,
        agent=FakeAgent(),
        sender=sender,
        calendar_for=lambda session, owner: MagicMock(),
        clock=lambda: datetime.now(UTC),
    )
    return TestClient(main.create_app(deps))


def sign(body: bytes) -> dict:
    digest = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return {"X-Hub-Signature-256": f"sha256={digest}"}


def text_payload(text="oi"):
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wamid.1",
                                    "from": PHONE,
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_webhook_verification_ok_and_forbidden(client):
    ok = client.get(
        "/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "123"},
    )
    assert ok.status_code == 200
    assert ok.text == "123"

    bad_token = client.get(
        "/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "123"},
    )
    assert bad_token.status_code == 403

    bad_mode = client.get(
        "/webhook",
        params={"hub.mode": "other", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "123"},
    )
    assert bad_mode.status_code == 403


def test_post_with_bad_signature_is_rejected(client, sender):
    body = json.dumps(text_payload()).encode()
    response = client.post(
        "/webhook", content=body, headers={"X-Hub-Signature-256": "sha256=deadbeef"}
    )
    assert response.status_code == 401
    assert sender.sent == []

    assert client.post("/webhook", content=body).status_code == 401
    assert sender.sent == []


def test_post_dispatches_messages(client, sender):
    body = json.dumps(text_payload()).encode()
    response = client.post("/webhook", content=body, headers=sign(body))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert sender.sent == [(PHONE, "Feito!")]


def test_post_status_update_returns_ok_without_reply(client, sender):
    payload = {"entry": [{"changes": [{"value": {"statuses": [{"id": "x", "status": "read"}]}}]}]}
    body = json.dumps(payload).encode()
    response = client.post("/webhook", content=body, headers=sign(body))
    assert response.status_code == 200
    assert sender.sent == []


def test_post_invalid_json_with_valid_signature_returns_ok(client, sender):
    body = b"not json"
    response = client.post("/webhook", content=body, headers=sign(body))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert sender.sent == []
