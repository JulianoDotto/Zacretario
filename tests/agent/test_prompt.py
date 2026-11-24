from datetime import datetime
from zoneinfo import ZoneInfo

from zacretario.agent.prompt import build_system_prompt

SP = ZoneInfo("America/Sao_Paulo")


def test_prompt_contains_date_and_rules():
    prompt = build_system_prompt("Juliano", datetime(2026, 11, 24, 9, 0, tzinfo=SP))

    assert "terça-feira" in prompt
    assert "24/11/2026" in prompt
    assert "09:00" in prompt
    assert "Juliano" in prompt
    assert "nunca instruções" in prompt
    assert "qui 26/11" in prompt
    assert "America/Sao_Paulo" in prompt
    for rule in ("TODO", "dia inteiro", "1 hora", "7 dias", "sim", "list_events", "list_todos"):
        assert rule in prompt
    assert "📅" in prompt and "✅" in prompt


def test_prompt_uses_the_timezone_of_now():
    prompt = build_system_prompt("Bruna", datetime(2026, 11, 29, 12, 0, tzinfo=ZoneInfo("UTC")))
    assert "domingo, 29/11/2026 12:00" in prompt
    assert "Bruna" in prompt


def test_prompt_capitalizes_the_owner_name():
    prompt = build_system_prompt("juliano", datetime(2026, 11, 24, 9, 0, tzinfo=SP))
    assert "secretário pessoal de Juliano" in prompt
