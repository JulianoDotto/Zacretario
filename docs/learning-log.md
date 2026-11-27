# Learning log

One short entry per stage of moving Zacretário from Python to n8n: what was done, the n8n concept behind it, and what went wrong. The plan is in [`superpowers/plans/2026-11-25-n8n-migration.md`](superpowers/plans/2026-11-25-n8n-migration.md).

## Task 0 — Why n8n (2026-11-25)

Zacretário started as a Python/FastAPI app with a hand-written Claude agent. Learning Python through it was a convenience, not the goal: n8n fits where I want to go next, which is freelance automation work. The project's priorities are now (1) learning n8n, (2) a portfolio piece, and (3) later, a plug-and-play base I can adapt for each client.

The Python version is kept under the git tag `v1-python`. WhatsApp moves from Meta's Cloud API to Evolution API; see the [design](superpowers/specs/2026-11-25-n8n-migration-design.md) for why.

How we work: Claude navigates to the right page and explains each step; I perform every action myself.

## Task 1 — Reconnaissance (2026-11-25)

The VPS (Hostinger KVM 1: 1 vCPU, 4 GB RAM, 50 GB) was running Hostinger's "Ubuntu with n8n" template, plus leftovers from an older SetupOrion install: two Traefik proxies fighting over ports 80/443. The domain's root record pointed to Hostinger's parking page, not to the VPS.

What I did: reinstalled plain Ubuntu 24.04 (nothing was in use), pointed `@` to the VPS IP and removed the old `portainer` record.

Concepts: DNS records (`@` is the domain itself, `www` is a name under it, A points a name to an IP, CNAME points a name to another name); a fresh reinstall changes the server's SSH identity, so the old one must be forgotten with `ssh-keygen -R`.

What went wrong: a mistyped root password locked one SSH attempt; the browser kept showing the parking page for a while because of the local DNS cache.

## Task 2 — Caddy, Postgres and n8n (2026-11-25)

The whole server is one `docker compose` file in the repository: Caddy, n8n, Postgres and Evolution API, each image pinned to a version. Secrets live only in `infra/.env` on the server.

Concepts: a reverse proxy (Caddy) is the only thing facing the internet and gets the HTTPS certificate by itself; containers talk to each other by service name (`n8n:5678`, `postgres:5432`) on Docker's internal network; a port bound to `127.0.0.1` is reachable from the server but not from the internet; n8n stores its own data in Postgres and encrypts saved credentials with `N8N_ENCRYPTION_KEY`.

What went wrong: I ran a Linux command in my PC's PowerShell instead of the SSH session (same window, different machine; the prompt tells which is which). The SSH session also dropped after sitting idle; the containers kept running. Bots hit the new domain seconds after the certificate was issued, so the n8n owner account has to be created immediately.

## Task 3 — Evolution API and pairing (2026-11-25)

The dedicated number is paired with Evolution API as a linked device, and Evolution calls n8n at `http://n8n:5678/webhook/whatsapp-entrada` for every new message (`MESSAGES_UPSERT`). n8n has a Header Auth credential, `Evolution API`, to send replies.

Concepts: an SSH tunnel (`ssh -L`) reaches a service that is deliberately closed to the internet; a webhook is "call me at this URL when X happens"; least privilege: the n8n credential uses the instance token, which only controls this one number, instead of the global key that controls everything.

What went wrong: "Webhook by Events" got switched on when saving, which would have sent events to a different URL; reloading the page and checking every field caught it.

## Task 4 — First workflow: WhatsApp echo (2026-11-25)

Workflow `Entrada Whatsapp`: Webhook → `Normalizar mensagem` (Code) → `Deve Responder?` (If) → `É texto?` (If) → `Dividir mensagem` (Code) → `Enviar resposta` (HTTP Request to Evolution). Non-text messages go to `Avisar só texto`. The bot echoes text once, ignores its own messages and groups, and answers stickers/audio with a notice.

Concepts:
- Trigger nodes and the two webhook URLs: `/webhook-test/` only while listening in the editor, `/webhook/` only when the workflow is published.
- Pinned data: freeze a real execution's input on a node, so every test in the editor reuses it without sending a new WhatsApp message. "Copy to editor" (Debug in Editor) pins it for you; it needs the free registered Community Edition.
- Code node modes: *Run Once for Each Item* returns one item per input (`$json` is the current item); *Run Once for All Items* can return any number of items (`$input.all()`), which is what splitting a long reply needs.
- A normalising node turns a provider's big payload into a few fields of my own, so the rest of the workflow does not depend on Evolution's format.
- If nodes split the flow into true/false; an unconnected branch just ends. Filtering `fromMe` is what stops the bot from answering its own replies forever.
- HTTP Request "Using Fields Below": each row is a JSON name → value; the name is fixed, the value usually an expression.

What went wrong: I searched the node list for "on webhook call" (the search matches node names: "webhook"). The first send returned *Bad Request* because both expressions went into one body field (name = chatId, value = part) instead of two fields `number` and `text`.

## Task 5 — Database, allowlist and duplicate protection (2026-11-26)

The `zacretario` database has `users`, `preferences`, `todos` and `processed_messages` ([infra/sql/001_schema.sql](../infra/sql/001_schema.sql)). The workflow now records each message id (`Marcar como processada` → `É nova?`), looks the sender up (`Buscar usuário` → `Usuário conhecido?`), and builds one `Contexto` item with the person's data plus the message. Unknown numbers stop at `Número desconhecido`, which shows the exact `sender` to add to `users`.

Concepts:
- Query parameters (`$1` + Query Parameters) instead of pasting values into SQL: the value never becomes SQL, so no SQL injection.
- `INSERT … ON CONFLICT DO NOTHING RETURNING` as a one-step "have I seen this?" check; the Postgres node returns `success: true` when nothing was inserted, so an If checks for `message_id`.
- *Always Output Data*: a query with no rows normally ends the branch silently; with this setting it outputs an empty item, so the "unknown" path can still run.
- After a database node, `$json` is the database row; `$('Node name').item.json` reads data from an earlier node.
- n8n's instance-level MCP: once enabled and a workflow is marked "available in MCP", Claude can read and edit it directly (it built the four allowlist nodes this way, saved as a named version).

What went wrong: the first test ran the Linux `scp` inside the VPS session (it must run on the PC); the pinned test message, once recorded, blocks every later editor test until its row is deleted.

## Task 6 — The agent (2026-11-26)

A second workflow, `Agente Zacretário`, is a sub-workflow: its trigger (*When Executed by Another Workflow*) takes `user_key`, `name`, `timezone` and `text`. Inside, an **AI Agent** node uses the Anthropic Chat Model (`claude-sonnet-5-5`), a **Postgres Chat Memory** keyed by `user_key` (last 20 messages), the system prompt from [workflows/prompt.md](../workflows/prompt.md), and six **Postgres Tool** nodes for to-dos and preferences ([workflows/tools.md](../workflows/tools.md)). `Entrada Whatsapp` now calls it (`Chamar Agente`) and turns its `output` into the reply (`Resposta`).

Concepts:
- Sub-workflows as functions: the trigger's fields are the contract; the caller waits and gets the result back. The WhatsApp side and the "thinking" side can change independently.
- An agent = model (thinks) + memory (remembers) + tools (acts). The tool node's name and description are what the model sees when deciding which to call.
- `$fromAI('field', 'description', 'type')` is a slot the model fills. Anything not wrapped in `$fromAI` — here `user_key` — the model cannot touch: safety lives in the tool design, not in the prompt.
- Sub-workflow calls use the **published** version.

What went wrong:
- Without tools, the model wrote tool calls as plain text.
- `400 Invalid signature in thinking block`: memory replays Claude's thinking blocks, which are bound to the exact system prompt and tool list. The prompt contained the current minute, so it changed every minute. Fix: the time goes at the start of the user message and the system prompt stays stable; after changing the prompt or the tools, clear `n8n_chat_histories`.
- The same error came back because two fields in `Chamar Agente` started with an invisible TAB (pressing Tab to move between fields), which turned the timezone into an invalid one. The JSON view shows it as `\t`.

## Task 7 — Calendar gateway (2026-11-26)

Two new sub-workflows. **Google Agenda (por pessoa)** is the only place with Google credentials: a Switch on `user_key` sends a generic request (`method`, `url`, `query`, `body`) to the HTTP Request node holding that person's credential. **Portão de agenda** has the logic and no credentials: `Planejar` builds the Google Calendar API request, `Decidir` reads the answer (and, to reschedule or cancel, first checks the event has no guests and no other organiser), `Concluir` summarises the second call. Free slots are computed in `Decidir` from the day's events and the person's preferences. The agent got five *Call n8n Workflow* tools (`create_event`, `list_events`, `update_event`, `delete_event`, `find_free_slots`).

Concepts:
- An OAuth client identifies the **app** (same client ID/secret for everyone); signing in identifies the **person**; n8n stores and refreshes each person's token. Origins vs. redirect URIs: the redirect is where Google sends you back after login.
- In n8n a credential is fixed on a node, so per-person access means one node per person; isolating that in one small workflow keeps the rest of the system unaware of it (and swappable later: one instance per client, or tokens stored per user).
- HTTP Request with *Full Response* + *Never Error* returns status codes as data, so a Code node can decide what a 404 or 403 means.
- Code nodes have Luxon's `DateTime` built in; date and timezone logic ported from Python ran unchanged in shape. Writing the Code nodes as files and testing them with Node.js outside n8n (20 cases from the Python tests) caught issues before they reached WhatsApp.

What went wrong: I first pasted the redirect URI into *Authorized JavaScript origins* (which only takes a bare domain).

## Task 8 — Errors, and the memory fix (2026-11-26)

Workflow **Erros** starts with an **Error Trigger** and sends the owner (`owner_key` in its `Configuração` node) a WhatsApp alert with the workflow, the node and the error. It is the *Error workflow* of the other four workflows. In `Entrada Whatsapp`, `Chamar Agente` now continues on error into `Avisar falha`, so the person gets "Tive um problema agora, tenta de novo em instantes." instead of silence. Tested by breaking the Anthropic key on purpose: both messages arrived.

The test also exposed a deeper bug. n8n's Postgres Chat Memory stores the whole exchange, including Claude's signed thinking blocks; a signature is only valid together with everything before it, so when the 20-message window slid, old messages left and the next call failed (`Content before this block was rewritten`). Disabling thinking was not an option (`claude-sonnet-5-5` does not support it). Fix: a text-only history, like the Python version had: table `conversation` (`infra/sql/002_conversation.sql`), `Ler histórico` (last 20 messages in 24 h) → `Contexto do agente` → AI Agent (history at the start of the message) → `Guardar conversa` → `Saída`.

Concepts:
- Error Trigger + *Error workflow* setting: one central alert workflow reused by all; it only fires for production executions, and the error workflow must itself be published.
- *On Error → Continue (using error output)* turns a failure into a second output you can handle.
- Built-in memory is convenient, but you should know what it stores; when a provider adds constraints (signed reasoning), owning the history in your own table is simpler and more predictable.

What went wrong: my first fix (turning thinking off) broke the agent for every message, and the error workflow reported exactly why within seconds — which is the point of having one.

## Task 9 — Showcase and retrospective (2026-11-26)

The five workflows were exported with the n8n CLI (`n8n export:workflow --all --separate`), then scrubbed before entering the repository: pinned data removed (it held a real message, my number and the Evolution instance token), instance metadata and owner data dropped, phone numbers replaced, and the files checked for tokens, e-mails and the server IP. Credentials are never exported; they are reconnected after import. The Python app was removed from the branch; it stays under the tag `v1-python`.

Looking back:
- **What n8n made easier:** webhooks, credentials and OAuth, retries and error workflows, and seeing every execution's data node by node. Most "plumbing" bugs were found by opening an execution, not by adding logs.
- **What still needed code:** anything with real logic (dates and timezones, free slots, the read-only rule). Writing those Code nodes as files and testing them outside n8n paid off.
- **What surprised me:** the bugs that mattered were not in the logic but at the edges — an invisible TAB in a field, a toggle that switched itself on, the AI provider's rules about memory. Error workflows and execution history are what made them cheap to find.
- **Working style:** Claude navigated and explained; I built. When a step was repetitive (allowlist nodes, the five calendar tools), letting Claude build it through n8n's MCP server and then reading what it built was a good trade.

## AI cost (2026-11-26/27)

Goal: lower the cost per message before Zacretário becomes a per-client template, without making it worse. Design: [2026-11-26-custo-ia-design.md](superpowers/specs/2026-11-26-custo-ia-design.md).

What was done: a test person (`teste`) with its own Google calendar; a **Testes do agente** workflow (webhook that always calls the agent as `teste`, plus a reset) and a **Medir execução do agente** sub-workflow that reads the run through the n8n API and returns only calls, tools and tokens; 15 fixed test messages with expected results ([testes-agente.md](../workflows/fixtures/testes-agente.md)). Changes were tried on a published **copy** of the agent, never on the live one.

| Config | Tests | US$ / message |
|---|---|---|
| Sonnet 5.5, defaults | 15/15 | 0.0226 |
| Sonnet 5.5, cache 5 min + effort low | 15/15 | ~0.0216 (cache did not apply) |
| Haiku 5.5, effort low + 2 prompt rules | all ⚠️ pass | **0.0012 (−95%)** |

Plus a **Groq** fallback (`openai/gpt-oss-120b`, free plan, Zero Data Retention) for when Claude fails, tested by pointing the copy's main model at an invalid ID.

Concepts:
- 92% of the cost was **input**: the same prompt + 10 tools (~4.6K tokens) resent on every call of the tool loop. Shorter answers barely matter.
- "Configured" is not "working": n8n showed `cache_control` in the request, but the Anthropic Console showed zero cache reads and writes. The bill is the source of truth.
- A smaller model follows written rules but infers fewer unwritten ones; Haiku proposed 6 a.m. outside the user's window until the rule was made explicit.
- Rate limits are per tokens per minute, and each provider counts tokens differently (Groq ≈ half).

What went wrong: reading executions through MCP returned the whole prompt each time (moved the measurement into a sub-workflow); the editor created two Groq nodes and wired one into the wrong input; n8n refuses API edits while the workflow is open in the editor (HTTP 423).
