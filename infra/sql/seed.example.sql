-- Example users. Do NOT commit real numbers: copy this, edit it on the server, run it there.
--   docker compose exec -T postgres psql -U zacretario -d zacretario < sql/seed.sql
-- whatsapp_id = the exact `sender` value shown by the "Normalizar mensagem" node
-- (the "Número desconhecido" node shows it for numbers not in this table yet).

INSERT INTO users (key, whatsapp_id, name) VALUES
    ('ana',   '5511900000000', 'Ana'),
    ('bruno', '5511911111111', 'Bruno')
ON CONFLICT (key) DO NOTHING;

INSERT INTO preferences (user_key) VALUES ('ana'), ('bruno')
ON CONFLICT (user_key) DO NOTHING;

-- Test person for agent evaluations (workflows/fixtures/testes-agente.md).
-- No WhatsApp: the fake whatsapp_id never matches a real sender. calendar_id is a
-- separate Google calendar ("Zacretário teste") in the owner's account; in
-- "Google Agenda (por pessoa)" the rule `teste` reuses the owner's credential.
INSERT INTO users (key, whatsapp_id, name, calendar_id) VALUES
    ('teste', 'teste-sem-whatsapp', 'Teste', '<id>@group.calendar.google.com')
ON CONFLICT (key) DO NOTHING;

INSERT INTO preferences (user_key) VALUES ('teste')
ON CONFLICT (user_key) DO NOTHING;
