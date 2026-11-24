import hashlib
import hmac
from dataclasses import dataclass
from typing import Protocol

import httpx

_default_http = httpx.Client(timeout=10)


@dataclass(frozen=True)
class IncomingMessage:
    message_id: str
    sender: str
    type: str
    text: str | None


def verify_signature(app_secret: str, body: bytes, signature_header: str | None) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected.encode(), signature_header.removeprefix("sha256=").encode())


def parse_webhook(payload: dict) -> list[IncomingMessage]:
    # Meta also sends status updates and other fields; anything unexpected is skipped.
    result = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            for msg in value.get("messages") or []:
                message_id, sender = msg.get("id"), msg.get("from")
                if not message_id or not sender:
                    continue
                kind = msg.get("type") or "unknown"
                text = (msg.get("text") or {}).get("body") if kind == "text" else None
                result.append(IncomingMessage(message_id, sender, kind, text))
    return result


def split_message(text: str, limit: int = 4096) -> list[str]:
    parts: list[str] = []
    current: str | None = None  # None = no open part (distinct from an empty line)
    for line in text.split("\n"):
        if len(line) > limit:
            if current is not None:
                parts.append(current)
            chunks = [line[i : i + limit] for i in range(0, len(line), limit)]
            parts.extend(chunks[:-1])
            current = chunks[-1]
        elif current is None:
            current = line
        elif len(current) + 1 + len(line) <= limit:
            current += "\n" + line
        else:
            parts.append(current)
            current = line
    parts.append(current or "")
    return parts


class MessageSender(Protocol):
    def send_text(self, to: str, text: str) -> None: ...


class WhatsAppClient:
    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        api_version: str,
        http: httpx.Client | None = None,
    ):
        self._token = access_token
        self._url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
        self._http = http or _default_http

    def send_text(self, to: str, text: str) -> None:
        if not text.strip():
            return
        for part in split_message(text):
            if not part.strip():
                continue
            response = self._http.post(
                self._url,
                headers={"Authorization": f"Bearer {self._token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "text",
                    "text": {"body": part},
                },
            )
            response.raise_for_status()
