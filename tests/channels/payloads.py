def _wrap(value: dict) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "WABA_ID", "changes": [{"field": "messages", "value": value}]}],
    }


_BASE = {
    "messaging_product": "whatsapp",
    "metadata": {"display_phone_number": "15550000000", "phone_number_id": "PHONE_ID"},
    "contacts": [{"profile": {"name": "Juliano"}, "wa_id": "5511999990000"}],
}

TEXT_PAYLOAD = _wrap(
    {
        **_BASE,
        "messages": [
            {
                "from": "5511999990000",
                "id": "wamid.X",
                "timestamp": "1764000000",
                "type": "text",
                "text": {"body": "Dentista quinta 10h"},
            }
        ],
    }
)

STATUS_PAYLOAD = _wrap(
    {
        **_BASE,
        "statuses": [
            {
                "id": "wamid.Y",
                "status": "delivered",
                "timestamp": "1764000001",
                "recipient_id": "5511999990000",
            }
        ],
    }
)

AUDIO_PAYLOAD = _wrap(
    {
        **_BASE,
        "messages": [
            {
                "from": "5511999990000",
                "id": "wamid.A",
                "timestamp": "1764000002",
                "type": "audio",
                "audio": {"id": "MEDIA_ID", "mime_type": "audio/ogg"},
            }
        ],
    }
)
