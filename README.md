# Zacretário

A personal secretary that lives in a WhatsApp chat. Write in plain language, and a Claude tool-use agent files the appointment in Google Calendar or adds the task to your to-do list.

This project is also a portfolio piece with one message: **I can use AI to build software and solutions.** AI is inside the product (an agent with tools) and in the process (designed, planned and implemented with Claude Code; see [How it was built](#how-it-was-built)).

## Example

The bot works in pt-BR; translations are in parentheses.

```
Ana:  Dentista, quinta-feira, 10h da manhã
      (Dentist, Thursday, 10 a.m.)
Bot:  📅 Dentista: qui 26/11 10:00–11:00
      (📅 Dentist: Thu 26/11 10:00–11:00)

Ana:  Comprar ração dos gatos
      (Buy cat food)
Bot:  ✅ TODO adicionado: Comprar ração dos gatos
      (✅ To-do added: Buy cat food)

Ana:  cancela o dentista
      (cancel the dentist)
Bot:  Cancelo *Dentista* de qui 26/11 10:00? (sim/não)
      (Cancel *Dentist* on Thu 26/11 10:00? (yes/no))

Ana:  sim
      (yes)
Bot:  🗑️ Dentista cancelado.
      (🗑️ Dentist cancelled.)
```

## Features

- Free-text messages, no command syntax. Messages with a day or time become calendar events; the rest become to-dos.
- Calendar: create, list, update (reschedule) and cancel events, and find free slots ("I need 2h to study this week" proposes times and only books after you approve).
- To-dos: add, list, complete and delete.
- Preferences, such as working hours and blocked weekdays, used when proposing slots.
- Asks before anything destructive or ambiguous, and every reply states what was understood.
- Short per-user conversation memory, so "yes" and "the second option" work.
- Allowlist of phone numbers, webhook signature check, duplicate-message protection.
- Text only: other message types get a polite notice. Out-of-scope requests ("write a poem") are refused.

## How it works

```
WhatsApp ──► Meta Cloud API ──► POST /webhook (FastAPI)
                                   │ verify signature, answer 200,
                                   │ drop duplicates and unknown numbers
                                   ▼
                              background task
                                   │ load recent conversation
                                   ▼
                          Agent (Claude + tools)
                          ├─ calendar tools ───► Google Calendar
                          ├─ todo tools ───────► Postgres
                          └─ preference tools ─► Postgres
                                   │
                                   ▼
WhatsApp ◄── Meta Cloud API ◄── reply
```

The agent receives text and returns text; WhatsApp is just an adapter. Skills are registered in one place, so adding one does not touch the agent loop. See [docs/future-improvements.md](docs/future-improvements.md) for the extension points.

## Tech stack

- Python 3.12, [uv](https://docs.astral.sh/uv/)
- FastAPI and uvicorn
- Anthropic API (Claude, tool use)
- Google Calendar API (OAuth per user)
- PostgreSQL ([Neon](https://neon.tech)), SQLAlchemy 2, Alembic
- WhatsApp Cloud API (Meta)
- pytest

## Getting started

Follow [docs/local-setup.md](docs/local-setup.md) in order:

1. [Docker (test database)](docs/local-setup.md#docker-test-database)
2. [Neon (database)](docs/local-setup.md#neon-database)
3. [Google Cloud (Calendar)](docs/local-setup.md#google-cloud-calendar)
4. [Meta / WhatsApp](docs/local-setup.md#meta--whatsapp)
5. [Running locally with a tunnel](docs/local-setup.md#running-locally-with-a-tunnel)
6. [Acceptance checklist](docs/local-setup.md#acceptance-checklist)

For a permanent server, domain and HTTPS, see [docs/deploy.md](docs/deploy.md).

Configuration lives in `.env` (copy `.env.example`). Secrets, tokens and phone numbers never go in the repository.

## Running tests

```bash
uv run pytest        # on Windows without uv on PATH: python -m uv run pytest
```

Tests use in-memory SQLite by default. To run them against Postgres:

```bash
docker compose up -d db
export TEST_DATABASE_URL=postgresql+psycopg://zacretario:zacretario@localhost:5433/zacretario_test
uv run pytest
```

A Neon branch works the same way: set `TEST_DATABASE_URL` to its connection string.

`TEST_DATABASE_URL` must be exported in the shell: the tests read `os.environ`, not `.env`. Never point it at your production database, because the tests drop all tables.

## Project structure

```
src/zacretario/
  main.py            FastAPI app and webhook routes
  service.py         message handling: allowlist, dedup, message types
  config.py          settings from environment variables
  channels/          WhatsApp adapter (payload parsing, sending)
  agent/             Claude loop, system prompt, tool registry and skills
  calendar/          CalendarProvider interface and Google implementation
  repositories/      database access (todos, preferences, conversation, credentials)
  scheduling.py      free-slot computation
migrations/          Alembic migrations
scripts/             one-time Google authorization
tests/               mirrors src/
docs/                setup guide, future improvements, spec and plan
```

## How it was built

Zacretário was built with AI end to end:

1. **Brainstorm** with Claude Code to turn the idea into requirements and decisions.
2. **Design spec**: [docs/superpowers/specs/2026-11-24-zacretario-design.md](docs/superpowers/specs/2026-11-24-zacretario-design.md) (in Portuguese).
3. **Implementation plan**: [docs/superpowers/plans/2026-11-24-zacretario.md](docs/superpowers/plans/2026-11-24-zacretario.md), broken into small tasks.
4. **Implementation** task by task by Claude Code subagents, each task independently reviewed before moving on.

The spec and plan are versioned here as evidence of the process.

## Scope note

Meta's WhatsApp Business terms prohibit general-purpose AI chatbots on the API, but allow task-specific assistants. Zacretário is deliberately a calendar and to-do secretary: its system prompt limits it to those skills and politely declines anything else. This is a product requirement as well as a compliance one.
