from zoneinfo import ZoneInfo

from zacretario.config import Settings


def test_settings_parses_allowed_users_and_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "t")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "1")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "s")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "v")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("ALLOWED_USERS", '{"5511999990000":"juliano","5511988880000":"bruna"}')

    settings = Settings(_env_file=None)

    assert settings.allowed_users["5511988880000"] == "bruna"
    assert settings.anthropic_model == "claude-sonnet-5-5"
    assert settings.tz == ZoneInfo("America/Sao_Paulo")
    assert settings.history_limit == 20
