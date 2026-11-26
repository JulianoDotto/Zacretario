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
