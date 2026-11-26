-- Zacretário data, in the `zacretario` database. Run as the `zacretario` user:
--   docker compose exec -T postgres psql -U zacretario -d zacretario < sql/001_schema.sql
-- Safe to run more than once.

-- Who may talk to the bot, and everything that changes per person/client.
CREATE TABLE IF NOT EXISTS users (
    key          text PRIMARY KEY,                 -- short id used by workflows, e.g. 'juliano'
    whatsapp_id  text UNIQUE NOT NULL,             -- the `sender` shown by "Normalizar mensagem": phone digits or an @lid id
    name         text NOT NULL,                    -- how the bot calls the person
    calendar_id  text NOT NULL DEFAULT 'primary',
    timezone     text NOT NULL DEFAULT 'America/Sao_Paulo',
    active       boolean NOT NULL DEFAULT true
);

-- Scheduling preferences. Weekdays: 0 = Monday ... 6 = Sunday.
CREATE TABLE IF NOT EXISTS preferences (
    user_key          text PRIMARY KEY REFERENCES users(key) ON DELETE CASCADE,
    day_start         time NOT NULL DEFAULT '08:00',
    day_end           time NOT NULL DEFAULT '22:00',
    blocked_weekdays  int[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS todos (
    id          serial PRIMARY KEY,
    user_key    text NOT NULL REFERENCES users(key) ON DELETE CASCADE,
    text        text NOT NULL,
    done        boolean NOT NULL DEFAULT false,
    created_at  timestamptz NOT NULL DEFAULT now(),
    done_at     timestamptz
);
CREATE INDEX IF NOT EXISTS todos_user_key_idx ON todos (user_key);

-- WhatsApp message ids already handled, so a re-delivered message is processed once.
CREATE TABLE IF NOT EXISTS processed_messages (
    message_id   text PRIMARY KEY,
    received_at  timestamptz NOT NULL DEFAULT now()
);
