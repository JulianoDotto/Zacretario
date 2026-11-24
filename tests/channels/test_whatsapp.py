import hashlib
import hmac
import json

import httpx
import pytest
from payloads import AUDIO_PAYLOAD, STATUS_PAYLOAD, TEXT_PAYLOAD

from zacretario.channels.whatsapp import (
    IncomingMessage,
    WhatsAppClient,
    parse_webhook,
    split_message,
    verify_signature,
)


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_verify_signature_accepts_valid_and_rejects_invalid():
    body = b'{"a": 1}'
    good = _sign("secret", body)
    assert verify_signature("secret", body, good)
    assert not verify_signature("other", body, good)
    assert not verify_signature("secret", b"tampered", good)
    assert not verify_signature("secret", body, None)
    assert not verify_signature("secret", body, good.removeprefix("sha256="))
    assert not verify_signature("secret", body, "sha256=")


def test_parse_text_message():
    assert parse_webhook(TEXT_PAYLOAD) == [
        IncomingMessage("wamid.X", "5511999990000", "text", "Dentista quinta 10h")
    ]


def test_parse_ignores_status_updates():
    assert parse_webhook(STATUS_PAYLOAD) == []


def test_parse_non_text_message():
    [msg] = parse_webhook(AUDIO_PAYLOAD)
    assert msg.type == "audio"
    assert msg.text is None


def test_parse_is_defensive():
    assert parse_webhook({}) == []
    assert parse_webhook({"entry": [{}, {"changes": [{}, {"value": {}}]}]}) == []
    assert parse_webhook({"entry": [{"changes": [{"value": {"messages": [{}]}}]}]}) == []


def test_split_long_message():
    lines = [f"{i:03d}" + "x" * 17 for i in range(300)]
    text = "\n".join(lines)
    parts = split_message(text)
    assert len(parts) > 1
    assert all(len(p) <= 4096 for p in parts)
    assert "\n".join(parts) == text
    assert all(set(p.split("\n")) <= set(lines) for p in parts)


def test_split_short_and_oversized_line():
    assert split_message("oi") == ["oi"]
    parts = split_message("a" * 10000, limit=4096)
    assert [len(p) for p in parts] == [4096, 4096, 1808]


def _client(handler) -> WhatsAppClient:
    return WhatsAppClient(
        "TOKEN", "PHONE_ID", "v21.0", http=httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_send_text_posts_expected_payload():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    _client(handler).send_text("5511999990000", "Olá")
    [req] = seen
    assert str(req.url) == "https://graph.facebook.com/v21.0/PHONE_ID/messages"
    assert req.headers["Authorization"] == "Bearer TOKEN"
    assert json.loads(req.content) == {
        "messaging_product": "whatsapp",
        "to": "5511999990000",
        "type": "text",
        "text": {"body": "Olá"},
    }


def test_send_text_skips_blank_and_raises_on_error():
    calls = []

    def ok(request):
        calls.append(request)
        return httpx.Response(200, json={})

    _client(ok).send_text("1", "  \n ")
    assert calls == []

    with pytest.raises(httpx.HTTPStatusError):
        _client(lambda r: httpx.Response(401)).send_text("1", "oi")


def test_split_preserves_blank_lines():
    text = "\nA\n\nB\n"
    assert "\n".join(split_message(text, limit=3)) == text


def test_verify_signature_rejects_non_ascii_header():
    assert verify_signature("secret", b"{}", "sha256=é") is False


def test_send_text_skips_blank_parts():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content)["text"]["body"])
        return httpx.Response(200, json={})

    _client(handler).send_text("1", "a" * 4096 + "\n")
    assert bodies == ["a" * 4096]
    bodies.clear()
    _client(handler).send_text("1", "\n" + "a" * 5000)
    assert bodies and all(b.strip() for b in bodies)
