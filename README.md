<p align="center"><img src="docs/assets/zacretario-avatar.png" alt="Zacretário logo: a calendar with a Z and a green check mark" width="160"></p>

# Zacretário

A personal secretary that lives in a WhatsApp chat. Write in plain language, and a Claude agent running in **n8n** files the appointment in Google Calendar or adds the task to your to-do list.

This project is also a portfolio piece with one message: **I can use AI to build software and solutions.** It exists in two versions: first as a Python/FastAPI app (tag [`v1-python`](../../tree/v1-python)), then rebuilt as self-hosted n8n workflows, which is what this branch contains. Both were designed, planned and built with Claude Code; see [How it was built](#how-it-was-built).

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
- Voice messages, photos and PDFs: a voice note counts as typed text; a photo of an invitation or a PDF schedule is read and turned into events, after asking when there is no caption or more than one item. Forwarded voice notes and anything written inside a file are treated as data, never as commands.
- Calendar: create, list, reschedule and cancel events, and find free slots ("I need 2h to study this week" proposes times and only books after you approve).
- To-dos: add, list, complete and delete. Preferences such as working hours and blocked weekdays.
- Asks before anything destructive; events with guests or organised by someone else are read-only.
- Each person has their own data, their own Google account and their own short conversation history.
- Only allowlisted numbers get an answer; duplicate deliveries are processed once; the bot ignores its own messages and groups.
- When something fails, the person gets a polite reply and the owner gets a WhatsApp alert with the failing workflow and node.
- Out-of-scope requests ("write a poem") are refused.

## How it works

```
WhatsApp ──► Evolution API ──► n8n ─ Entrada Whatsapp
              (same VPS,        │  normalise, ignore own/group messages,
               internal network)│  drop duplicates, look the sender up in `users`
                                ▼
        audio/image/PDF ─► Ler mídia: Evolution file ─► Groq Whisper | Claude (vision) ─► text
                                ▼
                       Agente Zacretário (AI Agent, Claude)
                       ├─ to-do and preference tools ──► Postgres
                       └─ calendar tools ─► Portão de agenda (logic, no credentials)
                                              └─► Google Agenda (por pessoa)
                                                   one HTTP node per person ──► Google Calendar
                                ▼
WhatsApp ◄── Evolution API ◄── reply           Erros ── alerts the owner on any failure
```

Six workflows, exported in [workflows/](workflows/):

| Workflow | Role |
|---|---|
| **Entrada Whatsapp** | Webhook from Evolution API; filters, deduplication, allowlist; calls the agent; sends the reply |
| **Ler mídia** | Fetches audio, images and PDFs from Evolution, transcribes or extracts them, and returns text marked as "not instructions" |
| **Agente Zacretário** | AI Agent with Claude, text-only history and 11 tools |
| **Portão de agenda** | Calendar logic in Code nodes: builds Google Calendar API requests, read-only check, free slots |
| **Google Agenda (por pessoa)** | The only place with Google credentials: a Switch on the person |
| **Erros** | Error workflow for all the others |

Everything that changes per person or per client lives in the `users` table and in n8n credentials, never inside the nodes. See [docs/future-improvements.md](docs/future-improvements.md#serving-more-people) for how this scales.

## Tech stack

- [n8n](https://n8n.io) 2.x, self-hosted, with JavaScript Code nodes (Luxon for dates)
- Anthropic Claude (`claude-haiku-5-5`) through n8n's AI Agent, with a Groq fallback; Claude also reads images and PDFs
- Groq Whisper (`whisper-large-v3-turbo`) for voice messages
- [Evolution API](https://github.com/EvolutionAPI/evolution-api) v2.3 for WhatsApp
- Google Calendar API (OAuth per person)
- PostgreSQL 16, Caddy 2 (HTTPS), Docker Compose on one VPS

> **Unofficial WhatsApp integration.** Evolution API is not Meta's official API; using it goes against WhatsApp's Terms of Service and the number can be banned. Zacretário uses a dedicated number and only answers people who write to it. [Why not the official API?](docs/why-n8n-evolution.md)

## Getting started

Follow [docs/setup.md](docs/setup.md) top to bottom: VPS and n8n, WhatsApp (Evolution API), database, Anthropic, Google Calendar, importing the workflows from [workflows/](workflows/), and adding people.

Secrets live only in `infra/.env` on the server and in n8n's encrypted credentials. Phone numbers are never committed.

## Project structure

```
infra/               docker-compose.yml, Caddyfile, Postgres init, SQL schema
workflows/           exported n8n workflows (JSON)
  code/              source of every Code node
    tests/           node --test workflows/code/tests/
  fixtures/          anonymised Evolution API and Trello payloads
  prompt.md          the agent's system prompt
  prompt-extracao.md the prompt that reads images and PDFs
  tools.md           the agent's database tools
.github/             the Kanban agent (GitHub Actions workflow, prompt, MCP config)
.claude/skills/      novo-card and testar-card, the Kanban skills for Claude Code
docs/
  setup.md           install guide, from an empty VPS
  kanban.md          the Trello board, the listener and the agent
  why-n8n-evolution.md
  learning-log.md    what each stage taught, and what went wrong
  future-improvements.md
  superpowers/       design specs and implementation plans
```

## How it was built

Both versions followed the same AI-assisted process with Claude Code:

1. **Brainstorm** to turn the idea into requirements and decisions.
2. **Design spec**: [v1](docs/superpowers/specs/2026-11-24-zacretario-design.md), [n8n](docs/superpowers/specs/2026-11-25-n8n-migration-design.md) (in Portuguese).
3. **Implementation plan**: [v1](docs/superpowers/plans/2026-11-24-zacretario.md), [n8n](docs/superpowers/plans/2026-11-25-n8n-migration.md).
4. **Implementation.** v1 was written by Claude Code subagents, each task reviewed before the next. The n8n version was built as a guided walkthrough: Claude navigated the browser and explained each step, and I built the workflows myself in the n8n editor, with Claude writing the Code nodes and some nodes through n8n's MCP server when I asked it to.

[docs/learning-log.md](docs/learning-log.md) records each stage of the n8n build: what was done, the n8n concept behind it, and what went wrong (including a memory bug with Claude's signed thinking blocks that only showed up in long conversations).

## How it changes now: a Kanban board

New features go through a Trello board ([docs/kanban.md](docs/kanban.md)):

1. **Backlog.** A brainstorm in Claude Code ends with the `novo-card` skill, which writes a card: user story, acceptance criteria, a development guide that names only real workflows and files, and a checklist.
2. **Em andamento.** Dragging the card there makes the production n8n (*Kanban: card movido*) start a Claude agent on GitHub Actions, one card at a time. The agent builds the change in a test copy of n8n with the same workflow IDs, exports the JSON, and opens a pull request.
3. **Para teste.** The `testar-card` skill walks through each criterion in the test n8n, including the ones the agent ticked itself.
4. **Pronto.** After the merge, the workflow is promoted from the test n8n to production with the same ID, and the card moves on.

The first card, a daily job that deletes conversation text after 48 hours ([PR #4](https://github.com/JulianoDotto/Zacretario/pull/4)), went through the whole loop. The agent's limits, the defences against a hostile card and what went wrong while setting it up are in [docs/kanban.md](docs/kanban.md#the-agent).

## Scope note

Zacretário is deliberately a calendar and to-do secretary: its system prompt limits it to those skills and politely declines anything else.
