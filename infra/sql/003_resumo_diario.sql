-- Daily summary: when each person wants it (NULL = off) and the day it was last sent.
--   docker compose exec -T postgres psql -U zacretario -d zacretario < sql/003_resumo_diario.sql
-- Safe to run more than once.

ALTER TABLE preferences ADD COLUMN IF NOT EXISTS daily_summary_time time DEFAULT '07:00';
ALTER TABLE preferences ADD COLUMN IF NOT EXISTS daily_summary_sent_on date;
