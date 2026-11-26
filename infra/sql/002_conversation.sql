-- Text-only conversation history used by the agent (replaces n8n's Postgres Chat Memory).
-- Only what the person said and what the bot answered: no tool calls and no signed
-- "thinking" blocks, which break when an old message leaves the memory window.
--   docker compose exec -T postgres psql -U zacretario -d zacretario < sql/002_conversation.sql
-- Safe to run more than once.

CREATE TABLE IF NOT EXISTS conversation (
    id          serial PRIMARY KEY,
    user_key    text NOT NULL REFERENCES users(key) ON DELETE CASCADE,
    role        text NOT NULL CHECK (role IN ('user', 'assistant')),
    text        text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS conversation_user_key_created_at_idx ON conversation (user_key, created_at DESC);

-- The old n8n memory table is no longer used.
DROP TABLE IF EXISTS n8n_chat_histories;
