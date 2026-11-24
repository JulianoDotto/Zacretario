# Zacretário — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um secretário pessoal no WhatsApp, para dois usuários, que registra compromissos no Google Calendar, mantém TODOs, responde consultas e propõe encaixes, interpretando linguagem natural com Claude.

**Architecture:** FastAPI recebe o webhook da Meta, valida, deduplica e despacha cada mensagem para uma tarefa em background. Um agente (loop manual de tool use com a API da Anthropic) recebe texto e devolve texto, chamando ferramentas registradas num único lugar. As ferramentas usam um `CalendarProvider` (Google é a primeira implementação) e repositórios SQLAlchemy sobre Postgres (Neon). O WhatsApp é só um adaptador de canal.

**Tech Stack:** Python ≥3.12, uv, FastAPI, Uvicorn, SQLAlchemy 2 (sync) + Alembic, psycopg 3, pydantic-settings, httpx, anthropic (SDK oficial), google-api-python-client + google-auth-oauthlib, pytest, ruff.

**Spec:** `docs/superpowers/specs/2026-11-24-zacretario-design.md`

## Global Constraints

- Python `>=3.12`; dependências via `uv`; lint/format com `ruff`; testes com `pytest`.
- Código **síncrono** de ponta a ponta (SQLAlchemy sync, `anthropic.Anthropic`, `httpx.Client`, cliente Google): mais legível para quem está aprendendo. FastAPI roda as tarefas sync em threadpool.
- Identificadores, nomes de arquivos e commits em **inglês**; textos enviados ao usuário e o prompt de sistema em **português (pt-BR)**; README em **inglês**.
- Modelo default `claude-sonnet-5-5`, configurável por `ANTHROPIC_MODEL`. Não usar `tool_choice` forçado (`any`/`tool` retornam 400 nesse modelo); não usar `thinking: {type: "disabled"}` (400).
- Fuso default `America/Sao_Paulo` (`TIMEZONE`). Todos os `datetime` internos são **aware**; no banco, sempre gravados em **UTC** (assim as comparações funcionam igual no Postgres e no SQLite dos testes, que descarta o fuso).
- Evento com hora e sem fim → **1 hora**. Dia sem hora → **dia inteiro**. Consulta sem período → **próximos 7 dias** + **todos os TODOs abertos**.
- Encaixe: janela default **08:00–22:00**, todos os dias, folga de **15 min**; personalizável por usuário e persistida no banco.
- Histórico de conversa: últimas **20** mensagens dentro das últimas **24 h** (`HISTORY_LIMIT`, `HISTORY_MAX_AGE_HOURS`).
- Eventos com outros participantes **nunca** são alterados ou cancelados; alterações usam `sendUpdates="none"`; eventos criados recebem `extendedProperties.private.zacretario="true"`.
- Números fora de `ALLOWED_USERS` são ignorados sem resposta e sem chamada ao LLM.
- Nenhum segredo, número de telefone ou token no repositório; `.env`, `*.db` e `token*.json` no `.gitignore`.
- Modularidade (spec §9): habilidades num registro único; calendário atrás de `CalendarProvider`; agente não conhece WhatsApp; todo dado tem `owner`.
- Comentários só onde o *porquê* não é óbvio; sem abstrações além das listadas aqui.
- Testes de banco rodam contra **Postgres em Docker** (`docker-compose.yml`, serviço `db`, `postgres:17`, porta host **5433**) via `TEST_DATABASE_URL=postgresql+psycopg://zacretario:zacretario@localhost:5433/zacretario_test`. Sem essa variável, caem para SQLite em memória (para quem clonar sem Docker).
- Todo passo manual do autor (contas, chaves, DNS) vive numa seção própria de `docs/local-setup.md`, com cabeçalhos `##` estáveis: `## Docker (test database)`, `## Neon (database)`, `## Google Cloud (Calendar)`, `## Meta / WhatsApp`, `## Running locally with a tunnel`, `## Domain & DNS`. Ao pedir uma ação ao autor, linkar a seção exata (ex.: `docs/local-setup.md#meta--whatsapp`).

## Review Focus

1. **Resposta maior que o limite do WhatsApp (4096 caracteres)**, por exemplo uma lista longa de TODOs → deve ser dividida em várias mensagens, quebrando em fim de linha. Teste na Task 9.
2. **A Meta reenvia o mesmo webhook** (retries) → a mensagem é processada uma única vez. Teste na Task 10.
3. **Webhooks de status** (delivered/read), sem `messages` → ignorados sem erro e sem resposta. Teste na Task 9.
4. **Horário perto da meia-noite**: "Festa 23h30" sem fim → termina 00:30 do dia seguinte, no fuso do usuário. Teste na Task 7.
5. **Falha externa no meio da conversa** (Google ou Anthropic fora, id inválido) → a ferramenta devolve `is_error` e o agente segue; uma exceção fora das ferramentas gera uma resposta de desculpas, e o webhook não falha. Testes nas Tasks 8 e 10.

---

## Estrutura de arquivos

```
pyproject.toml  .env.example  .gitignore  README.md  alembic.ini
docs/future-improvements.md  docs/local-setup.md  docs/deploy.md
deploy/zacretario.service  deploy/Caddyfile
migrations/env.py  migrations/versions/0001_initial.py
scripts/authorize_google.py
src/zacretario/
  config.py                 Settings + get_settings()
  db.py                     engine, SessionLocal, Base, session_scope()
  models.py                 ORM: Todo, UserPreference, ConversationMessage, ProcessedMessage, GoogleCredential
  repositories/todos.py     funções de TODO
  repositories/preferences.py
  repositories/conversation.py   histórico + deduplicação
  repositories/credentials.py
  scheduling.py             Availability + find_free_slots (puro)
  calendar/base.py          CalendarEvent, CalendarProvider (Protocol), erros
  calendar/google.py        GoogleCalendarProvider
  agent/registry.py         Tool, ToolContext, ToolError, registro
  agent/todo_tools.py       habilidades de TODO
  agent/preference_tools.py habilidades de preferências
  agent/calendar_tools.py   habilidades de calendário
  agent/prompt.py           build_system_prompt()
  agent/agent.py            Agent (loop de tool use)
  channels/whatsapp.py      IncomingMessage, verify_signature, parse_webhook, split_message, WhatsAppClient
  service.py                Deps + handle_message()
  main.py                   create_app() + rotas
tests/  (espelha src/; conftest.py com fixture de sessão)
```

---

### Task 1: Scaffold do projeto e configuração

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`, `docker-compose.yml`, `docs/local-setup.md` (esqueleto com os seis cabeçalhos das Global Constraints; só a seção Docker preenchida), `src/zacretario/__init__.py`, `src/zacretario/config.py`, `tests/test_config.py`

**Interfaces:**
- Produces: `Settings` (pydantic-settings, lê `.env`) com campos `database_url: str`, `anthropic_api_key: str`, `anthropic_model: str = "claude-sonnet-5-5"`, `whatsapp_access_token: str`, `whatsapp_phone_number_id: str`, `whatsapp_app_secret: str`, `whatsapp_verify_token: str`, `whatsapp_api_version: str = "v23.0"`, `allowed_users: dict[str, str]` (env `ALLOWED_USERS` em JSON, telefone E.164 sem `+` → nome do usuário), `google_client_id: str`, `google_client_secret: str`, `timezone: str = "America/Sao_Paulo"`, `history_limit: int = 20`, `history_max_age_hours: int = 24`; propriedade `tz -> ZoneInfo`; `get_settings() -> Settings` com `lru_cache`.

- [ ] **Step 1:** `git init`; instalar uv (`python -m pip install uv`); `uv init --package --name zacretario`; `uv add fastapi uvicorn[standard] sqlalchemy alembic "psycopg[binary]" pydantic-settings httpx anthropic google-api-python-client google-auth-oauthlib`; `uv add --dev pytest ruff`. Configurar `[tool.ruff]` (line-length 100, regras `E,F,I,UP,B`) e `[tool.pytest.ini_options] testpaths=["tests"]`. `.gitignore`: `.env`, `.venv/`, `__pycache__/`, `*.db`, `token*.json`, `client_secret*.json`. `.env.example` lista cada variável de `Settings` com comentário de onde obtê-la (apontando a seção de `docs/local-setup.md`) e valores fictícios (`ALLOWED_USERS={"5511900000000":"juliano"}`), mais `TEST_DATABASE_URL`. `docker-compose.yml`: serviço `db` (`postgres:17`, usuário/senha `zacretario`, banco `zacretario_test`, porta `5433:5432`). Seção `## Docker (test database)` do `local-setup.md`: `docker compose up -d db` e como exportar `TEST_DATABASE_URL`.
- [ ] **Step 2: Teste que falha** — `test_settings_parses_allowed_users_and_defaults(monkeypatch)`: com as variáveis obrigatórias setadas e `ALLOWED_USERS='{"5511999990000":"juliano","5511988880000":"bruna"}'`, `Settings(_env_file=None)` tem `allowed_users["5511988880000"] == "bruna"`, `anthropic_model == "claude-sonnet-5-5"`, `tz == ZoneInfo("America/Sao_Paulo")`, `history_limit == 20`.
- [ ] **Step 3:** `uv run pytest tests/test_config.py -v` → FAIL (módulo não existe).
- [ ] **Step 4:** Implementar `config.py`.
- [ ] **Step 5:** `uv run pytest -v && uv run ruff check .` → PASS, sem avisos.
- [ ] **Step 6:** Commit: o `docs/` existente + os arquivos acima. Mensagem: `chore: scaffold project with settings`.

### Task 2: Banco de dados, modelos e TODOs

**Files:**
- Create: `src/zacretario/db.py`, `src/zacretario/models.py`, `src/zacretario/repositories/__init__.py`, `src/zacretario/repositories/todos.py`, `alembic.ini`, `migrations/env.py`, `migrations/versions/0001_initial.py`, `tests/conftest.py`, `tests/repositories/test_todos.py`

**Interfaces:**
- Produces:
  - `db.py`: `Base(DeclarativeBase)`; `make_session_factory(database_url: str) -> sessionmaker[Session]`; `session_scope(factory) -> ContextManager[Session]` (commit no sucesso, rollback na exceção).
  - `models.py` (tipos portáveis, sem nada específico de Postgres):
    - `Todo`: `id: int` pk, `owner: str` (index), `text: str`, `done: bool = False`, `created_at: datetime` (tz-aware, default agora UTC), `done_at: datetime | None`.
    - `UserPreference`: `owner: str` pk, `day_start: time = 08:00`, `day_end: time = 22:00`, `blocked_weekdays: str = ""` (CSV de inteiros, 0 = segunda).
    - `ConversationMessage`: `id` pk, `owner` (index), `role: str` (`"user"`|`"assistant"`), `text: str`, `created_at`.
    - `ProcessedMessage`: `message_id: str` pk, `received_at`.
    - `GoogleCredential`: `owner: str` pk, `refresh_token: str`.
  - `repositories/todos.py`: `add_todo(session, owner: str, text: str) -> Todo`; `list_open_todos(session, owner) -> list[Todo]` (ordem de criação); `complete_todo(session, owner, todo_id: int) -> Todo | None`; `delete_todo(session, owner, todo_id: int) -> bool`. Qualquer operação com `todo_id` de outro `owner` se comporta como "não encontrado".
  - `tests/conftest.py`: fixture `session` usando `TEST_DATABASE_URL` se definida (o Postgres do `docker-compose.yml`), senão `sqlite+pysqlite:///:memory:`; cria as tabelas com `Base.metadata.create_all` e descarta (`drop_all`) no fim de cada teste. Rodar a suíte nas duas configurações pelo menos uma vez nesta task.

- [ ] **Step 1: Testes que falham** em `tests/repositories/test_todos.py`:
  - `test_add_and_list_open_todos`: adiciona "Comprar ração dos gatos" e "Trocar lâmpada" para `juliano` → `list_open_todos` devolve os dois textos nessa ordem.
  - `test_complete_todo_removes_from_open_list`: após `complete_todo`, o item tem `done is True` e `done_at` preenchido, e não aparece em `list_open_todos`.
  - `test_delete_todo`: `delete_todo` → `True` e a lista fica vazia; um segundo `delete_todo` com o mesmo id → `False`.
  - `test_owners_are_isolated`: um TODO de `bruna` não aparece na lista de `juliano`; `complete_todo(session, "juliano", id_da_bruna)` → `None`; `delete_todo(session, "juliano", id_da_bruna)` → `False`, e o item continua aberto para `bruna`.
- [ ] **Step 2:** `uv run pytest tests/repositories -v` → FAIL.
- [ ] **Step 3:** Implementar `db.py`, `models.py` e `todos.py`. Configurar o Alembic (`migrations/env.py` lê `get_settings().database_url` e usa `Base.metadata`). Gerar `0001_initial.py` com as 5 tabelas, escrita à mão ou com `alembic revision --autogenerate` revisado.
- [ ] **Step 4:** `uv run pytest -v` → PASS.
- [ ] **Step 5:** Commit `feat: add database models and todo repository`.

### Task 3: Preferências, histórico e deduplicação

**Files:**
- Create: `src/zacretario/scheduling.py` (só o `Availability` nesta task), `src/zacretario/repositories/preferences.py`, `src/zacretario/repositories/conversation.py`, `src/zacretario/repositories/credentials.py`, `tests/repositories/test_preferences.py`, `tests/repositories/test_conversation.py`

**Interfaces:**
- Consumes: modelos da Task 2.
- Produces:
  - `scheduling.Availability` (`@dataclass(frozen=True)`): `day_start: time = time(8)`, `day_end: time = time(22)`, `blocked_weekdays: frozenset[int] = frozenset()`.
  - `preferences.get_availability(session, owner) -> Availability` (devolve os defaults se não houver linha); `preferences.update_availability(session, owner, *, day_start: time | None = None, day_end: time | None = None, blocked_weekdays: set[int] | None = None) -> Availability` (só altera o que não for `None`; levanta `ValueError` se `day_start >= day_end` ou se algum dia estiver fora de 0..6).
  - `conversation.append_message(session, owner, role: str, text: str, now: datetime) -> None`; `conversation.recent_messages(session, owner, *, limit: int, max_age: timedelta, now: datetime) -> list[ConversationMessage]` (as últimas `limit` dentro de `max_age`, em ordem cronológica); `conversation.mark_processed(session, message_id: str, now: datetime) -> bool` (`True` se for nova, `False` se já tinha sido vista).
  - `credentials.get_refresh_token(session, owner) -> str | None`; `credentials.save_refresh_token(session, owner, token: str) -> None` (upsert).

- [ ] **Step 1: Testes que falham:**
  - `test_availability_defaults`: `get_availability` sem linha → `Availability(time(8), time(22), frozenset())`.
  - `test_update_availability_partial`: `update_availability(..., day_start=time(7))` e depois `update_availability(..., blocked_weekdays={6})` → `Availability(time(7), time(22), frozenset({6}))`.
  - `test_update_availability_rejects_inverted_window`: `day_start=time(23), day_end=time(7)` → `ValueError`.
  - `test_recent_messages_limit_and_age`: 25 mensagens, sendo uma com 30 h de idade → com `limit=20` e `max_age=24h` devolve as 20 mais novas, em ordem cronológica e sem a antiga.
  - `test_recent_messages_isolated_by_owner`.
  - `test_mark_processed_is_idempotent`: primeira chamada `True`, segunda com o mesmo id `False`.
  - `test_save_refresh_token_upserts`: salvar duas vezes para o mesmo `owner` → `get_refresh_token` devolve o último valor.
- [ ] **Step 2:** `uv run pytest tests/repositories -v` → FAIL.
- [ ] **Step 3:** Implementar. Em `mark_processed`, tentar o insert e tratar `IntegrityError` com rollback de um savepoint (`session.begin_nested()`).
- [ ] **Step 4:** `uv run pytest -v` → PASS.
- [ ] **Step 5:** Commit `feat: add preferences, conversation history and dedupe repositories`.

### Task 4: Busca de horários livres

**Files:**
- Modify: `src/zacretario/scheduling.py`
- Test: `tests/test_scheduling.py`

**Interfaces:**
- Consumes: `Availability` (Task 3). Os eventos chegam como intervalos ocupados, para manter o módulo puro (sem depender do calendário).
- Produces: `find_free_slots(busy: list[tuple[datetime, datetime]], *, range_start: datetime, range_end: datetime, duration: timedelta, availability: Availability, tz: ZoneInfo, buffer: timedelta = timedelta(minutes=15), max_slots: int = 5) -> list[tuple[datetime, datetime]]`.

Algoritmo: para cada dia local entre `range_start` e `range_end`, pular os dias em `blocked_weekdays` e montar a janela `[day_start, day_end]` recortada pelo intervalo pedido. Subtrair cada intervalo ocupado expandido por `buffer` dos dois lados. Em cada lacuna livre, o início é arredondado para cima até o próximo múltiplo de 15 min. Se `início + duration <= fim da lacuna`, gerar **um** slot `(início, início + duration)`. Parar em `max_slots`. Ordem cronológica.

- [ ] **Step 1: Testes que falham** (tz São Paulo, segunda 2026-11-30 a domingo 2026-12-06):
  - `test_empty_calendar_one_slot_per_day`: sem eventos, `duration=2h` → 5 slots, o primeiro `(30/11 08:00, 30/11 10:00)`.
  - `test_respects_buffer_around_events`: evento em 30/11 08:00–09:00, `duration=1h`, `max_slots=1` → `(30/11 09:15, 30/11 10:15)`.
  - `test_skips_blocked_weekdays`: `blocked_weekdays={0}` → nenhum slot em 30/11.
  - `test_rounds_start_to_quarter_hour`: evento 30/11 08:00–09:05 → o primeiro slot começa às 09:30 (09:05 + 15 min = 09:20, arredondado para 09:30).
  - `test_gap_too_small_is_skipped`: eventos 08:00–09:00 e 10:00–22:00 em 30/11, `duration=1h` → nenhum slot em 30/11, porque a lacuna 09:15–09:45 é curta demais.
  - `test_range_start_mid_day`: `range_start = 30/11 15:10` → o primeiro slot começa 30/11 15:15.
- [ ] **Step 2:** `uv run pytest tests/test_scheduling.py -v` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `uv run pytest -v` → PASS.
- [ ] **Step 5:** Commit `feat: add free slot finder`.

### Task 5: Interface de calendário e provedor Google

**Files:**
- Create: `src/zacretario/calendar/__init__.py`, `src/zacretario/calendar/base.py`, `src/zacretario/calendar/google.py`, `tests/calendar/test_google.py`

**Interfaces:**
- Produces:
  - `CalendarEvent` (`@dataclass(frozen=True)`): `id: str`, `title: str`, `start: datetime | date`, `end: datetime | date`, `all_day: bool`, `has_attendees: bool = False`. Para dia inteiro, `start`/`end` são `date` e `end` é **exclusivo** (convenção do Google).
  - `CalendarProvider(Protocol)`: `list_events(start: datetime, end: datetime) -> list[CalendarEvent]`; `create_event(title: str, start: datetime | date, end: datetime | date, all_day: bool) -> CalendarEvent`; `update_event(event_id: str, *, title: str | None = None, start: datetime | date | None = None, end: datetime | date | None = None, all_day: bool | None = None) -> CalendarEvent`; `delete_event(event_id: str) -> None`.
  - Erros: `CalendarError(Exception)`; `EventNotFoundError(CalendarError)`; `EventHasAttendeesError(CalendarError)`.
  - `GoogleCalendarProvider(service, calendar_id: str = "primary", tz: ZoneInfo)` em que `service` é o recurso do `googleapiclient.discovery.build("calendar", "v3", ...)`. `build_google_provider(refresh_token: str, settings: Settings) -> GoogleCalendarProvider` monta `google.oauth2.credentials.Credentials` com `token_uri="https://oauth2.googleapis.com/token"`, client id/secret e escopo `https://www.googleapis.com/auth/calendar.events`.
  - Regras: `list_events` usa `singleEvents=True`, `orderBy="startTime"` e ignora eventos cancelados. `has_attendees` é `True` se existir algum participante que não seja `self`. `create_event` envia `extendedProperties={"private": {"zacretario": "true"}}`. `update_event` e `delete_event` primeiro fazem `events().get`; se `has_attendees`, levantam `EventHasAttendeesError`; um 404 vira `EventNotFoundError`. Usar `patch` e `delete` com `sendUpdates="none"`.

- [ ] **Step 1: Testes que falham** com um `service` falso (`unittest.mock.MagicMock`, verificando os kwargs passados a `events().insert/patch/delete/list`):
  - `test_create_timed_event_payload`: `create_event("Dentista", 27/11 10:00 SP, 27/11 11:00 SP, False)` → o body tem `summary="Dentista"`, `start.dateTime="2026-11-27T10:00:00-03:00"`, `start.timeZone="America/Sao_Paulo"` e `extendedProperties.private.zacretario == "true"`.
  - `test_create_all_day_event_payload`: `date(2026,11,28)`–`date(2026,11,29)` → `start.date="2026-11-28"`, `end.date="2026-11-29"`.
  - `test_list_events_maps_fields`: uma resposta com um evento com hora, um de dia inteiro e um com `attendees=[{"email":"x","self":True},{"email":"y"}]` → os `CalendarEvent`s correspondentes, e `has_attendees` só no terceiro.
  - `test_update_refuses_event_with_attendees`: o `get` devolve um evento com outro participante → `EventHasAttendeesError`, e `patch` não é chamado.
  - `test_delete_uses_send_updates_none`.
  - `test_missing_event_raises_not_found`: o `get` levanta `HttpError` com status 404 → `EventNotFoundError`.
- [ ] **Step 2:** `uv run pytest tests/calendar -v` → FAIL.
- [ ] **Step 3:** Implementar `base.py` e `google.py`.
- [ ] **Step 4:** `uv run pytest -v` → PASS.
- [ ] **Step 5:** Commit `feat: add calendar provider interface and Google implementation`.

### Task 6: Registro de habilidades, TODOs e preferências

**Files:**
- Create: `src/zacretario/agent/__init__.py`, `src/zacretario/agent/registry.py`, `src/zacretario/agent/todo_tools.py`, `src/zacretario/agent/preference_tools.py`, `tests/agent/test_todo_tools.py`, `tests/agent/test_preference_tools.py`

**Interfaces:**
- Consumes: repositórios das Tasks 2–3; `CalendarProvider` (Task 5).
- Produces:
  - `ToolContext` (`@dataclass`): `owner: str`, `session: Session`, `calendar: CalendarProvider`, `tz: ZoneInfo`, `now: datetime`.
  - `ToolError(Exception)`: erro mostrado ao modelo como `is_error`.
  - `Tool` (`@dataclass(frozen=True)`): `name: str`, `description: str`, `input_schema: dict`, `handler: Callable[[ToolContext, dict], str]`.
  - `registry.register(tool: Tool) -> Tool`, `registry.all_tools() -> list[Tool]`, `registry.get_tool(name) -> Tool`, `registry.to_api_params(tools) -> list[dict]` (cada item com `name`, `description`, `input_schema` e `"strict": True`; schemas com `additionalProperties: false` e todos os campos em `required`; um campo opcional usa `"type": [..., "null"]`).
  - Os módulos de habilidades se registram quando são importados; `agent/__init__.py` importa todos, e é o **único** lugar a mudar para adicionar uma habilidade.
  - Habilidades (nome → input → retorno em texto pt-BR):
    - `add_todo` `{text}` → `"TODO #<id> criado: <text>"`.
    - `list_todos` `{}` → linhas `"#<id> <text>"` ou `"Nenhum TODO em aberto."`.
    - `complete_todo` `{todo_id: integer}` → `"TODO #<id> concluído: <text>"`; se não existir, `ToolError("TODO #<id> não encontrado")`.
    - `delete_todo` `{todo_id}` → `"TODO #<id> apagado"`; se não existir, `ToolError`.
    - `get_preferences` `{}` → `"Janela: 08:00–22:00. Dias bloqueados: nenhum"` (dias por extenso em pt-BR).
    - `update_preferences` `{day_start: "HH:MM"|null, day_end: "HH:MM"|null, blocked_weekdays: integer[]|null}` → a mesma string de `get_preferences` com os valores novos; um `ValueError` do repositório vira `ToolError`.

- [ ] **Step 1: Testes que falham** (chamar `get_tool(name).handler(ctx, input)` com a fixture `session` e um calendário `MagicMock`):
  - `test_add_and_list_todos_via_tools`.
  - `test_complete_unknown_todo_raises_tool_error`.
  - `test_tools_are_scoped_to_context_owner`: um TODO de `bruna` é invisível em `list_todos` com `owner="juliano"`.
  - `test_update_preferences_formats_result`: `{"day_start":"07:00","day_end":null,"blocked_weekdays":[6]}` → `"Janela: 07:00–22:00. Dias bloqueados: domingo"`.
  - `test_registry_api_params_are_strict`: todo item de `to_api_params(all_tools())` tem `strict is True` e `input_schema["additionalProperties"] is False`.
- [ ] **Step 2:** `uv run pytest tests/agent -v` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `uv run pytest -v` → PASS.
- [ ] **Step 5:** Commit `feat: add tool registry with todo and preference skills`.

### Task 7: Habilidades de calendário

**Files:**
- Create: `src/zacretario/agent/calendar_tools.py`, `tests/agent/test_calendar_tools.py`
- Modify: `src/zacretario/agent/__init__.py` (importar `calendar_tools`)

**Interfaces:**
- Consumes: `ToolContext`, `register`, `ToolError` (Task 6); `CalendarProvider`, os erros e `CalendarEvent` (Task 5); `find_free_slots` (Task 4); `get_availability` (Task 3).
- Produces (datas `YYYY-MM-DD` e horas `HH:MM` interpretadas em `ctx.tz`):
  - `create_event` `{title, date, start_time|null, end_time|null}` → sem `start_time`, evento de dia inteiro (`date` até `date+1`); sem `end_time`, `start + 1h`; `end_time` menor ou igual a `start_time` significa que termina no dia seguinte. Retorno: `"Evento criado (id <id>): <linha formatada>"`.
  - `list_events` `{start_date, end_date}` (inclusivos; o fim vira `end_date+1` às 00:00) → uma linha por evento, `"[<id>] qui 27/11 10:00–11:00 Dentista"`. Dia inteiro aparece como `"qui 27/11 (dia todo) ..."`, e evento com convidados recebe o sufixo `" (com convidados — não posso alterar)"`. Sem eventos: `"Nenhum compromisso no período."`.
  - `update_event` `{event_id, title|null, date|null, start_time|null, end_time|null}` → reaproveita as regras de horário de `create_event` quando `date` ou `start_time` mudam, preservando a duração original se só a data ou o início mudar.
  - `delete_event` `{event_id}`.
  - `find_free_slots` `{start_date, end_date, duration_minutes: integer, earliest_time|null, latest_time|null}` → ocupado = eventos **com hora** do período (dia inteiro não ocupa); disponibilidade = `get_availability`, com `earliest_time`/`latest_time` sobrescrevendo a janela só nesta busca; o início nunca é antes de `ctx.now`. Retorno: as linhas `"qui 27/11 14:00–16:00"`, ou `"Nenhum horário livre encontrado."`.
  - Os erros `EventHasAttendeesError`, `EventNotFoundError` e `CalendarError` viram `ToolError` com mensagem em pt-BR.
  - Helper compartilhado: `format_event(event: CalendarEvent, tz) -> str`, com dias da semana abreviados em pt-BR (`seg ter qua qui sex sáb dom`).

- [ ] **Step 1: Testes que falham** (um `FakeCalendar` em memória implementando `CalendarProvider` em `tests/agent/fakes.py`, reaproveitado depois):
  - `test_create_timed_event_defaults_to_one_hour`: `{"title":"Dentista","date":"2026-11-27","start_time":"10:00","end_time":null}` → o evento termina às 11:00 SP.
  - `test_create_all_day_event`: `start_time=null` → `all_day`, `end == date(2026,11,28)`.
  - `test_create_event_crossing_midnight`: `start_time="23:30"`, sem fim → o fim é 28/11 00:30.
  - `test_list_events_marks_attendees_and_all_day`.
  - `test_delete_event_with_attendees_returns_tool_error`.
  - `test_update_event_keeps_duration_when_moving_date`: um evento de 2 h movido para outra data continua com 2 h.
  - `test_find_free_slots_ignores_all_day_and_past`: `ctx.now = 30/11 15:10`; um evento de dia inteiro em 30/11 não bloqueia; o primeiro slot começa às 15:15.
- [ ] **Step 2:** `uv run pytest tests/agent/test_calendar_tools.py -v` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `uv run pytest -v` → PASS.
- [ ] **Step 5:** Commit `feat: add calendar skills`.

### Task 8: Prompt de sistema e loop do agente

**Files:**
- Create: `src/zacretario/agent/prompt.py`, `src/zacretario/agent/agent.py`, `tests/agent/test_agent.py`, `tests/agent/test_prompt.py`

**Interfaces:**
- Consumes: `Tool`, `ToolContext`, `ToolError`, `to_api_params`, `all_tools` (Task 6).
- Produces:
  - `build_system_prompt(user_name: str, now: datetime) -> str`, em pt-BR. Deve conter: a persona de secretário pessoal de `user_name`; a data e hora atuais com o dia da semana por extenso; as regras da spec §5 (classificação evento/TODO, defaults de evento, perguntar na ambiguidade real, **confirmar antes de apagar, cancelar ou alterar** e só executar após um "sim" explícito na mensagem seguinte, encaixes são só propostas, consulta sem período = 7 dias + todos os TODOs, agenda e TODOs em blocos separados); a regra de nunca inventar ids (sempre usar `list_events`/`list_todos` antes de alterar algo); o escopo restrito a agenda, tarefas e preferências, recusando com gentileza o que estiver fora (política da Meta); e o formato das respostas: curto, próprio para WhatsApp, `*negrito*` em vez de Markdown, 📅 para eventos e ✅ para TODOs.
  - `Agent(client: anthropic.Anthropic, model: str, tools: list[Tool], max_iterations: int = 8)` com `reply(ctx: ToolContext, user_name: str, history: list[tuple[str, str]], text: str) -> str`. `history` é uma lista de pares `(role, text)` em ordem cronológica e vira mensagens de texto simples, seguidas da mensagem nova.
  - A chamada é `client.beta.messages.create(model=..., max_tokens=16000, system=..., tools=to_api_params(tools), messages=..., output_config={"effort": "medium"}, betas=["server-side-fallback-2026-07-01"], fallbacks="default")`. O fallback server-side reexecuta a chamada num modelo alternativo quando o modelo principal recusa.
  - Loop manual: `end_turn` → junta os blocos `text`; `tool_use` → executa **todas** as chamadas e devolve todos os `tool_result` numa única mensagem `user` (`ToolError` ou qualquer `Exception` vira `is_error: True` com a mensagem, e a exceção inesperada é registrada em log); `refusal` → `"Desculpe, não posso ajudar com isso. Posso cuidar da sua agenda e das suas tarefas 🙂"`; `max_tokens`, ou estourar `max_iterations` → `AgentError`. O conteúdo do assistente é anexado inteiro (`response.content`) entre as iterações. Só o texto final é guardado no histórico persistente (Task 10).
  - `AgentError(Exception)`.

- [ ] **Step 1: Testes que falham** com um cliente falso (`FakeAnthropic` em `tests/agent/fakes.py`, que expõe `.beta.messages.create(**kwargs)`, devolve respostas roteirizadas feitas com `SimpleNamespace` e guarda os kwargs recebidos):
  - `test_plain_answer_returns_text`.
  - `test_executes_tool_and_returns_final_text`: 1ª resposta com `tool_use add_todo {"text":"Comprar ração"}`; 2ª resposta `end_turn` com o texto "✅ Anotado" → o retorno é "✅ Anotado"; o TODO existe no banco; a 2ª chamada recebeu um `tool_result` com `tool_use_id` correto.
  - `test_parallel_tool_calls_return_single_user_message`: dois `tool_use` na mesma resposta → a mensagem seguinte tem dois `tool_result` num único turno `user`.
  - `test_tool_error_is_reported_to_model`: `complete_todo` com id inexistente → `tool_result.is_error is True`, e o loop continua até o `end_turn`.
  - `test_refusal_returns_polite_message`.
  - `test_iteration_cap_raises_agent_error`: o fake devolve `tool_use` para sempre → `AgentError`.
  - `test_request_shape`: os kwargs têm `model`, `fallbacks="default"`, `output_config={"effort":"medium"}`, e o histórico vem antes da mensagem nova.
  - `test_prompt_contains_date_and_rules` (`test_prompt.py`): `build_system_prompt("Juliano", datetime(2026,11,24,9,0,tzinfo=SP))` contém `"terça-feira"`, `"24/11/2026"` e `"Juliano"`.
- [ ] **Step 2:** `uv run pytest tests/agent -v` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `uv run pytest -v` → PASS.
- [ ] **Step 5:** Commit `feat: add secretary agent loop and system prompt`.

### Task 9: Canal WhatsApp

**Files:**
- Create: `src/zacretario/channels/__init__.py`, `src/zacretario/channels/whatsapp.py`, `tests/channels/test_whatsapp.py`

**Interfaces:**
- Produces:
  - `IncomingMessage` (`@dataclass(frozen=True)`): `message_id: str`, `sender: str` (número do campo `from`), `type: str`, `text: str | None`.
  - `verify_signature(app_secret: str, body: bytes, signature_header: str | None) -> bool`: compara um HMAC-SHA256 hex com o header `sha256=<hex>` usando `hmac.compare_digest`; um header ausente ou malformado devolve `False`.
  - `parse_webhook(payload: dict) -> list[IncomingMessage]`: percorre `entry[].changes[].value.messages[]` e ignora `statuses` e qualquer `value` sem `messages`. Para `type == "text"`, o texto vem de `text.body`; nos outros tipos, `text=None`.
  - `split_message(text: str, limit: int = 4096) -> list[str]`: quebra preferencialmente em `\n` e corta no meio de uma linha só se ela sozinha passar do limite.
  - `MessageSender(Protocol)`: `send_text(to: str, text: str) -> None`.
  - `WhatsAppClient(access_token: str, phone_number_id: str, api_version: str, http: httpx.Client | None = None)` implementa `MessageSender`. Para cada parte de `split_message`, faz um POST em `https://graph.facebook.com/{api_version}/{phone_number_id}/messages` com o JSON `{"messaging_product":"whatsapp","to":to,"type":"text","text":{"body":part}}` e o header `Authorization: Bearer <token>`. Chama `raise_for_status()`.

- [ ] **Step 1: Testes que falham:**
  - `test_verify_signature_accepts_valid_and_rejects_invalid` (inclui header ausente e header sem o prefixo `sha256=`).
  - `test_parse_text_message`: um payload real da Meta (fixture em `tests/channels/payloads.py`) → `IncomingMessage("wamid.X", "5511999990000", "text", "Dentista quinta 10h")`.
  - `test_parse_ignores_status_updates`: um payload só com `statuses` → `[]`.
  - `test_parse_non_text_message`: `type == "audio"` → `text is None`.
  - `test_split_long_message`: 300 linhas de 20 caracteres → todas as partes `<= 4096`, `"\n".join(parts)` reconstitui o original, e nenhuma parte começa ou termina no meio de uma linha.
  - `test_send_text_posts_expected_payload`: usa `httpx.MockTransport`, verifica a URL, o header e o JSON.
- [ ] **Step 2:** `uv run pytest tests/channels -v` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `uv run pytest -v` → PASS.
- [ ] **Step 5:** Commit `feat: add WhatsApp channel adapter`.

### Task 10: Orquestração de mensagens

**Files:**
- Create: `src/zacretario/service.py`, `tests/test_service.py`

**Interfaces:**
- Consumes: `IncomingMessage`, `MessageSender` (Task 9); `Agent`, `AgentError` (Task 8); `ToolContext` (Task 6); `conversation.*` (Task 3); `CalendarProvider` (Task 5).
- Produces:
  - `Deps` (`@dataclass`): `settings: Settings`, `session_factory: sessionmaker`, `agent: Agent`, `sender: MessageSender`, `calendar_for: Callable[[Session, str], CalendarProvider]`, `clock: Callable[[], datetime]`.
  - `handle_message(message: IncomingMessage, deps: Deps) -> None`. Na ordem:
    1. `sender` fora de `allowed_users` → `logger.info` e retorno, sem resposta.
    2. `mark_processed` devolve `False` → retorno silencioso.
    3. `type != "text"` → envia `"Por enquanto eu só entendo mensagens de texto 🙂"`.
    4. Carrega o histórico, monta `ToolContext(owner=nome, ...)`, chama `agent.reply`, grava a mensagem do usuário e a resposta, e envia a resposta.
    5. Qualquer exceção nos passos 3–4 → `logger.exception` e envio de `"Tive um problema pra processar isso agora. Pode tentar de novo em instantes?"`. Uma falha nesse envio também só gera log. `handle_message` **nunca** propaga exceção.
  - O `owner` é o **nome** vindo de `allowed_users` (ex.: `"juliano"`), não o telefone.

- [ ] **Step 1: Testes que falham** (com um `FakeSender` que acumula `(to, text)`, um agente falso com `reply` controlável e a fixture `session`):
  - `test_unknown_number_is_ignored`: nada é enviado e o agente não é chamado.
  - `test_duplicate_message_processed_once`: a mesma `IncomingMessage` duas vezes → uma única resposta.
  - `test_non_text_gets_polite_notice`.
  - `test_reply_is_sent_and_history_saved`: depois do processamento, `recent_messages` tem `("user", texto)` e `("assistant", resposta)`.
  - `test_history_is_passed_to_agent`: numa segunda mensagem, o agente recebe a troca anterior em `history`.
  - `test_agent_failure_sends_apology`: o agente levanta `RuntimeError` → a mensagem de desculpas é enviada e nada é propagado.
- [ ] **Step 2:** `uv run pytest tests/test_service.py -v` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `uv run pytest -v` → PASS.
- [ ] **Step 5:** Commit `feat: add message handling service`.

### Task 11: App FastAPI e webhook

**Files:**
- Create: `src/zacretario/main.py`, `tests/test_main.py`

**Interfaces:**
- Consumes: `Deps`, `handle_message` (Task 10); `verify_signature`, `parse_webhook`, `WhatsAppClient` (Task 9); `Agent`, `all_tools` (Task 8/6); `build_google_provider`, `get_refresh_token` (Tasks 5/3).
- Produces:
  - `create_app(deps: Deps) -> FastAPI` com as rotas:
    - `GET /health` → `{"status": "ok"}`.
    - `GET /webhook`: os query params `hub.mode`, `hub.verify_token` e `hub.challenge`. Se o modo for `subscribe` e o token bater → `PlainTextResponse(challenge)`; senão → 403.
    - `POST /webhook`: lê o corpo bruto (`await request.body()`). Assinatura inválida → 401. Senão, `parse_webhook(json)` e, para cada mensagem, `background_tasks.add_task(handle_message, msg, deps)`. Responde sempre `{"status": "ok"}` com 200.
  - `build_deps(settings: Settings) -> Deps`: a fábrica real. `calendar_for(session, owner)` busca o refresh token com `get_refresh_token` e chama `build_google_provider`. Sem token → `RuntimeError("Google não autorizado para <owner>: rode scripts/authorize_google.py")`, que vira a mensagem de desculpas.
  - `app = create_app(build_deps(get_settings()))`, num módulo-nível protegido para não executar no import dos testes (ex.: a função `get_app()` usada pelo uvicorn com `--factory`). Comando de execução: `uv run uvicorn zacretario.main:get_app --factory`.

- [ ] **Step 1: Testes que falham** com `fastapi.testclient.TestClient` e `Deps` falsos:
  - `test_webhook_verification_ok_and_forbidden`.
  - `test_post_with_bad_signature_is_rejected`: → 401, e `handle_message` não é chamado.
  - `test_post_dispatches_messages`: um payload assinado corretamente → 200, e o `FakeSender` recebeu a resposta do agente falso (o `TestClient` executa as background tasks).
  - `test_post_status_update_returns_ok_without_reply`.
- [ ] **Step 2:** `uv run pytest tests/test_main.py -v` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `uv run pytest -v && uv run ruff check .` → PASS.
- [ ] **Step 5:** Commit `feat: add FastAPI webhook app`.

### Task 12: Autorização do Google e marco local (com o autor)

**Files:**
- Create: `scripts/authorize_google.py`, `docs/local-setup.md`

**Interfaces:**
- Consumes: `save_refresh_token` (Task 3), `Settings`.
- Produces: `uv run python scripts/authorize_google.py <owner>`. O script roda `InstalledAppFlow.from_client_config` com o client id/secret do `.env` e o escopo `calendar.events`, `run_local_server(port=0, access_type="offline", prompt="consent")`, e grava o refresh token com `save_refresh_token`. Rejeita um `owner` que não esteja nos valores de `allowed_users`.

Este é o marco local da spec (§8, "Contas e etapas de setup"). Ele depende de ações do autor que o executor **não pode** fazer: criar contas, aceitar termos e digitar senhas.

- [ ] **Step 1:** Escrever o script. Teste manual: com `owner` inválido, sai com código 1 e uma mensagem clara.
- [ ] **Step 2:** Preencher as seções de `docs/local-setup.md` (em inglês) criadas na Task 1, mantendo os cabeçalhos exatos. A seção `## Domain & DNS` explica como apontar um domínio/subdomínio para o IP da VPS Hostinger (registro `A`, painel DNS da Hostinger ou do registrador) e por que é preciso (HTTPS exigido pela Meta, emitido pelo Caddy). Passo a passo das demais:
  1. Criar o projeto Neon e copiar a `DATABASE_URL`; rodar `uv run alembic upgrade head`.
  2. Google Cloud: criar o projeto, ativar a Calendar API, configurar a tela de consentimento como **External**, **publicar como "In production"** sem verificação (senão o token expira em 7 dias) e criar credenciais OAuth "Desktop app".
  3. Rodar o script para cada usuário e aceitar o aviso de "app não verificado".
  4. Meta: criar o app de desenvolvedor do tipo Business com o produto WhatsApp, usar o **número de teste**, cadastrar os dois números como destinatários e criar o **token permanente de System User** (o token do painel expira em 24h). Copiar o phone number id e o app secret.
  5. Expor o servidor: `uv run uvicorn zacretario.main:get_app --factory --port 8000` + `cloudflared tunnel --url http://localhost:8000`.
  6. Configurar o webhook na Meta (URL `/webhook`, verify token, assinar o campo `messages`).
- [ ] **Step 3: Checkpoint com o autor.** Pedir que ele siga o guia e mande as mensagens de aceitação abaixo. Registrar o resultado de cada uma:
  - "Dentista, quinta-feira, 10h da manhã" → um evento de 1 h na próxima quinta, com confirmação.
  - "Comprar ração dos gatos" → um TODO.
  - "o que tenho pra fazer?" → agenda dos próximos 7 dias + TODOs, em blocos.
  - "comprei a ração" → o TODO concluído.
  - "cancela o dentista" → pede confirmação; só cancela depois do "sim".
  - "preciso de 2h pra estudar essa semana" → propõe horários; só cria depois da aprovação.
  - "meu horário é das 7h às 23h" → preferência salva.
  - "escreve um poema" → recusa educada.
  - Uma mensagem de áudio → o aviso de "só texto".

  **Layout das mensagens:** mostrar ao autor as confirmações e listas reais e ajustar a seção de formato em `prompt.py` até ele aprovar (spec §5).
- [ ] **Step 4:** Commit `feat: add Google authorization script and local setup guide` (+ os ajustes de prompt, num commit `chore: tune reply format with author`).

### Task 13: Documentação e portfólio

**Files:**
- Create: `README.md`, `docs/future-improvements.md`

- [ ] **Step 1:** `README.md` em **inglês**, enxuto:
  - o que é, com uma conversa de exemplo em pt-BR traduzida inline;
  - um diagrama ASCII do fluxo (spec §8);
  - as features;
  - o tech stack;
  - quick start apontando para `docs/local-setup.md` e `docs/deploy.md`;
  - como rodar os testes (`uv run pytest`; opcionalmente `TEST_DATABASE_URL` para um branch do Neon);
  - project structure;
  - a seção **"How it was built"**: desenvolvido com IA (brainstorm → design → plano → implementação com Claude Code), com links para `docs/superpowers/specs/` e `docs/superpowers/plans/`;
  - a nota de escopo sobre a política da Meta (assistente de tarefa específica).
- [ ] **Step 2:** `docs/future-improvements.md` com os itens da spec §9 (lista da casa compartilhada, áudio/imagens/encaminhadas, lembretes proativos, Outlook/iCloud, Telegram). Para cada item, indicar **qual ponto de extensão** recebe a mudança: o registro de habilidades, `CalendarProvider`, o adaptador de canal + `IncomingMessage.type`, ou o `owner`.
- [ ] **Step 3:** Revisar: nenhum segredo nem número real nos docs (`grep -rn "55[0-9]\{10,\}" --include=*.md .` não encontra números reais).
- [ ] **Step 4:** Commit `docs: add README and future improvements`.

### Task 14: Deploy na VPS Hostinger (marco 2, com o autor)

**Files:**
- Create: `deploy/zacretario.service`, `deploy/Caddyfile`, `docs/deploy.md`

Depende de o autor ter um **número dedicado** registrado na Meta e um **domínio ou subdomínio** apontando para a VPS (o Caddy precisa dele para emitir o HTTPS) — linkar `docs/local-setup.md#domain--dns`; `docs/deploy.md` também linka essa seção em vez de repeti-la.

- [ ] **Step 1:** `deploy/zacretario.service`: unidade systemd com o usuário `zacretario`, `WorkingDirectory=/opt/zacretario`, `EnvironmentFile=/opt/zacretario/.env`, `ExecStart=/opt/zacretario/.venv/bin/uvicorn zacretario.main:get_app --factory --host 127.0.0.1 --port 8000` e `Restart=always`.
- [ ] **Step 2:** `deploy/Caddyfile`: `<dominio> { reverse_proxy 127.0.0.1:8000 }`.
- [ ] **Step 3:** `docs/deploy.md` (em inglês), na VPS KVM 1 com Ubuntu:
  1. Criar o usuário e instalar uv, git e Caddy.
  2. Clonar em `/opt/zacretario`, `uv sync --frozen` e criar o `.env`.
  3. `alembic upgrade head`.
  4. Instalar a unit e o Caddyfile.
  5. `systemctl enable --now`.
  6. Trocar a URL do webhook na Meta para `https://<dominio>/webhook`.
  7. Migrar do número de teste para o número dedicado.
  8. Atualizar: `git pull && uv sync && alembic upgrade head && systemctl restart zacretario`.
  9. Ver logs com `journalctl -u zacretario -f`.
- [ ] **Step 4: Checkpoint com o autor:** repetir as mensagens de aceitação da Task 12 no ambiente de produção; `curl https://<dominio>/health` devolve `{"status":"ok"}`.
- [ ] **Step 5:** Commit `docs: add VPS deployment guide`.
