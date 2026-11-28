# Setup

How to stand up Zacretário from zero on one VPS. Follow the sections in order. Each later section (WhatsApp, database, Google) is added as the project reaches it.

## VPS and n8n

What you get: a fresh Ubuntu server running four containers from [`infra/docker-compose.yml`](../infra/docker-compose.yml):

| Service | Reachable from | Purpose |
|---|---|---|
| `caddy` | the internet (80/443) | HTTPS certificate and reverse proxy to n8n |
| `n8n` | Caddy only | the workflows |
| `postgres` | containers only | one database each for n8n, Evolution API and Zacretário |
| `evolution` | the server itself (`127.0.0.1:8080`) | WhatsApp connection |

You need a VPS with Ubuntu 24.04 (1 vCPU and 4 GB of RAM are enough) and a domain whose DNS you control.

1. **DNS.** Create an `A` record for `@` pointing to the VPS IP, and a `CNAME` for `www` pointing to `@`. Wait until `nslookup <domain> 1.1.1.1` returns the VPS IP: Caddy can only get the certificate once the domain points to the server.
2. **Clean server.** Use a plain Ubuntu 24.04 image, not a provider template that already runs n8n or a proxy: two proxies fight over ports 80 and 443. After a reinstall, forget the old SSH identity on your PC with `ssh-keygen -R <IP>`.
3. **Docker and firewall** (on the server, as root):

   ```bash
   apt update && apt upgrade -y && apt install -y docker.io docker-compose-v2
   ufw allow OpenSSH && ufw allow 80,443/tcp && ufw --force enable
   mkdir -p /opt/zacretario
   ```

4. **Copy the infra folder** (from your PC, in the repository folder):

   ```bash
   scp -r infra root@<IP>:/opt/zacretario/
   ```

5. **Secrets** (on the server). This fills every empty value in `.env` with a random 64-character secret:

   ```bash
   cd /opt/zacretario/infra && cp .env.example .env
   for k in POSTGRES_PASSWORD N8N_DB_PASSWORD EVOLUTION_DB_PASSWORD ZACRETARIO_DB_PASSWORD N8N_ENCRYPTION_KEY EVOLUTION_API_KEY; do sed -i "s/^$k=$/$k=$(openssl rand -hex 32)/" .env; done
   chmod 600 .env && chmod +x postgres/init.sh
   ```

   Set `DOMAIN` in `.env` if it is not `dotton8n.com.br`. Save `N8N_ENCRYPTION_KEY` and `EVOLUTION_API_KEY` in a password manager: without the first, every credential stored in n8n is lost if the server is rebuilt; the second controls the WhatsApp number.

6. **Start:**

   ```bash
   docker compose up -d && docker compose ps
   ```

   All four services should be `Up` and Postgres `healthy`. `docker compose logs caddy` should show `certificate obtained successfully`. A few `502` errors right after the start are normal: n8n takes some seconds to boot.

7. **Create the n8n owner account right away.** Open `https://<domain>`: whoever fills in the "Set up owner account" form first owns the instance, and bots find new domains within seconds of the certificate being issued (certificates are published in public logs).

8. **Check from outside:**
   - `https://<domain>` opens n8n with a valid certificate; `https://www.<domain>` redirects to it.
   - `curl -X POST https://<domain>/webhook/whatsapp-entrada` returns `404`: the WhatsApp webhook only exists on the internal network.
   - `http://<IP>:8080` does not answer: Evolution API is not exposed.

Docker publishes ports past `ufw`, so the protection for Postgres and Evolution is that the compose file publishes no port for Postgres and binds Evolution to `127.0.0.1`. Keep it that way.

## WhatsApp (Evolution API)

Zacretário talks to WhatsApp through [Evolution API](https://github.com/EvolutionAPI/evolution-api), which connects a number the way WhatsApp Web does (a linked device, paired with a QR code).

> **Unofficial integration.** Evolution API is not Meta's official WhatsApp API. Using it goes against WhatsApp's Terms of Service and the number can be banned. Use a dedicated number, never your personal one, and keep the bot to answering people who write to it. See [why-n8n-evolution.md](why-n8n-evolution.md) for why the project accepts this.

You need a dedicated SIM with WhatsApp (or WhatsApp Business) active on a phone. That phone stays the main device: if it is off or offline for too long, WhatsApp unlinks the bot.

1. **Open the panel through an SSH tunnel** (on your PC). Evolution only listens on the server itself, so the tunnel brings its port to your machine. Keep the window open while you use the panel.

   ```bash
   ssh -o ServerAliveInterval=60 -L 8080:127.0.0.1:8080 root@<IP>
   ```

2. Open `http://localhost:8080/manager` and log in with Server URL `http://localhost:8080` and the `EVOLUTION_API_KEY` from `infra/.env` (`grep EVOLUTION_API_KEY /opt/zacretario/infra/.env`; run `clear` afterwards).
3. **Create the instance:** name `zacretario` (the workflows use this exact name), channel `Baileys`. Keep the generated token.
4. **Pair:** open the instance, show the QR code, and on the bot's phone go to WhatsApp → Linked devices → Link a device. The instance must show **Connected**.
5. **Webhook** (Events → Webhook):
   - Enabled: on
   - URL: `http://n8n:5678/webhook/whatsapp-entrada` (the container name, so the call stays on Docker's internal network)
   - Webhook by Events: **off** (otherwise the event name is appended to the URL and n8n never receives it)
   - Webhook Base64: off (media is fetched later, only for allowlisted people, by **Ler mídia**)
   - Events: only `MESSAGES_UPSERT`

   Save, reload the page and check that every value stuck.
6. **n8n credential:** in n8n, Credentials → Create credential → **Header Auth**, name `apikey`, value = the **instance token** (Dashboard of the instance), credential name `Evolution API`. Use the instance token rather than the global key: it can only operate this one instance.

Evolution API is licensed under Apache 2.0 with extra conditions: keep its logo and copyright in the manager, and state that the system uses Evolution API (this guide and the README do).

## Database

1. Create the tables, in order (on the server, in `/opt/zacretario/infra`; the SQL files arrived with the `infra` folder):

   ```bash
   docker compose exec -T postgres psql -U zacretario -d zacretario < sql/001_schema.sql
   docker compose exec -T postgres psql -U zacretario -d zacretario < sql/002_conversation.sql
   docker compose exec -T postgres psql -U zacretario -d zacretario < sql/003_resumo_diario.sql
   ```

2. In n8n, create the credential **Postgres Zacretário** (Postgres: host `postgres`, database and user `zacretario`, password `ZACRETARIO_DB_PASSWORD` from `infra/.env`, SSL disabled).

## Anthropic (Claude)

1. In the [Claude Console](https://console.anthropic.com/settings/keys), create an API key used only by n8n (Create key → "elsewhere", name `n8n-zacretario`). Copy it once and keep it in a password manager. Set a monthly spend limit in the Console: it caps the damage if the key leaks or the bot loops.
2. In n8n, Credentials → Create credential → **Anthropic**, paste the key and name it `Anthropic`.
3. In the agent, the **Anthropic Chat Model** uses `claude-haiku-5-5` with Options *Thinking Mode: Adaptive* and *Effort: Low*. This was chosen by measurement: Sonnet 5.5 passed 15/15 and Haiku 5.5 passed 14/15 with every safety test (⚠️) passing; the one failure (T08, a slot outside the person's window) passed after two explicit prompt rules and a code guard, retested on the affected tests only. About US$ 0.0226 vs US$ 0.0012 per message. See [workflows/fixtures/testes-agente.md](../workflows/fixtures/testes-agente.md). *Prompt Caching* is set but, on this n8n version, the Console showed no cache reads or writes.

## Groq (fallback)

If Claude fails (no credits, overload), the AI Agent repeats the call on Groq.

1. Create an account at [console.groq.com](https://console.groq.com). In **Settings → Data Controls**, enable **Global ZDR** so inputs and outputs are not stored. Create an API key named `n8n-zacretario`.
2. In n8n, Credentials → Create credential → **Groq**, paste the key.
3. In **AI Agent**, turn on **Enable Fallback Model** and connect a **Groq Chat Model** (`openai/gpt-oss-120b`) to the **Fallback Model** input (the second model input, not *Chat Model*).

The free plan allows about 8K tokens per minute. Groq counts roughly half the tokens Anthropic does for the same prompt, so a few messages per minute fit.

## Reading media (audio, images, PDFs)

The workflow **Ler mídia** reads what people send besides text:

- **Audio** is transcribed by Groq's Whisper (`whisper-large-v3-turbo`, Portuguese) with the same **Groq** credential as the fallback. The *Transcrever* node is an HTTP Request with *Predefined Credential Type → Groq*.
- **Images and PDFs** go to two **Anthropic** nodes (*image/analyze* and *document/analyze*, `claude-haiku-5-5`) with the extraction prompt in [workflows/prompt-extracao.md](../workflows/prompt-extracao.md).
- The file is fetched from Evolution (`/chat/getBase64FromMediaMessage`) with the whole message, because Evolution is set not to store messages and cannot find one by id.

In its settings, keep **Save successful production executions: off** (only failures are kept, for debugging) and **Error workflow: Erros**. Limits (5 min of audio, 3.75 MB per image (Anthropic's 5 MB limit counts the base64 text), 10 pages or 10 MB per PDF) live in the `Normalizar mensagem` Code node.

## Google Calendar

Each person connects their own Google account. In n8n a credential is fixed on a node, so the only place that holds Google credentials is the workflow **Google Agenda (por pessoa)**: a Switch on `user_key` with one HTTP Request node per person. Everything else (the agent tools and the **Portão de agenda** logic) only passes `user_key` along.

1. **Google Cloud project** (once): enable the Google Calendar API; on the OAuth consent screen choose **External** and **Publish app** so the status is **In production** (in "Testing", access expires after 7 days).
2. **OAuth client for n8n** (once): Google Auth Platform → Clients → Create client → **Web application**, name `n8n`. Leave *Authorized JavaScript origins* empty and add the redirect URI `https://<domain>/rest/oauth2-credential/callback` under **Authorized redirect URIs**. Keep the client ID and secret.
3. **One credential per person:** in n8n, Credentials → Create credential → **Google Calendar OAuth2 API**, paste the same client ID and secret, click **Sign in with Google** and let *that person* sign in. Google warns that the app is unverified: Advanced → Go to (app name). Name it `Google Calendar - <Name>`.

## Import the workflows

The exported workflows are in [workflows/](../workflows/), without credentials and without pinned data.

1. In n8n, import each file (Workflows → Create → Import from file), in this order: `google-agenda-por-pessoa.json`, `portao-de-agenda.json`, `erros.json`, `agente-zacretario.json`, `ler-midia.json`, `entrada-whatsapp.json`. Optional, for evaluations: `medir-execucao-do-agente.json`, then `testes-do-agente.json`. Duplicate the agent as a published test copy, point *Chamar Agente como teste* at it and *Medir* at the measuring workflow, and put the copy's id in *É da cópia de teste?*. It needs an **n8n API** credential, and the domain in the two HTTP nodes is this instance's. Keep **Testes do agente** unpublished; it also refuses anything that is not a manual run.
2. Open every node that shows a credential warning and pick the matching credential (`Evolution API`, `Postgres Zacretário`, `Anthropic`, `Groq`, `Google Calendar - <Name>`).
3. Workflows call each other by id, and imported workflows get new ids. Re-select the target workflow in: *Chamar Google* and *Chamar Google (2)* (Portão de agenda → Google Agenda (por pessoa)), the five calendar tools in the agent (→ Portão de agenda), *Chamar Agente* (Entrada Whatsapp → Agente Zacretário) and *Ler mídia* (Entrada Whatsapp → Ler mídia). In **Testes do agente**, also *Chamar Ler mídia*. Set **Erros** as the *Error workflow* in the settings of the other five.
4. **One branch per person** in **Google Agenda (por pessoa)**: for each person, a rule `user_key` equals `<key>` in **Qual pessoa?** and a copy of the **Agenda - Juliano** node using that person's credential. Without a branch, that person's agenda requests get "Esta pessoa ainda não conectou a agenda Google."
5. In **Erros**, set `owner_key` in *Configuração* to the owner's key (the one you will use in the next section).
6. Publish **Erros** first, then **Google Agenda (por pessoa)**, **Portão de agenda**, **Agente Zacretário** and **Ler mídia** (sub-workflows run their published version), then **Entrada Whatsapp** last.

## Add people

Only people in the `users` table get an answer.

1. Ask the person to send any message to the bot's number. The bot does not answer; in n8n, open that execution of **Entrada Whatsapp**: the **Número desconhecido** node shows their `sender` (phone digits, or an `@lid` id).
2. Add them, with their own preferences row (`key` is a short id used by the workflows, e.g. `ana`):

   ```bash
   docker compose exec -T postgres psql -U zacretario -d zacretario -c "INSERT INTO users (key, whatsapp_id, name) VALUES ('ana', '<sender>', 'Ana'); INSERT INTO preferences (user_key) VALUES ('ana');"
   ```

   Never commit real numbers; [infra/sql/seed.example.sql](../infra/sql/seed.example.sql) shows the format.
3. If the `key` is new, add their branch in **Google Agenda (por pessoa)** (see step 4 above) and publish it.

**Test person.** Agent evaluations run as the person `teste`, never as a real user: a fake `whatsapp_id` (`teste-sem-whatsapp`, so the bot never answers it) and its own Google calendar, "Zacretário teste", created in the owner's account. Put that calendar's ID (Google Calendar → Settings → the calendar → *Integrate calendar*) in `calendar_id` (see the end of [seed.example.sql](../infra/sql/seed.example.sql)), and in **Google Agenda (por pessoa)** connect the rule `teste` to the owner's node: same credential, different calendar.

## Test n8n (for the Kanban agent)

A second n8n, `n8n-teste`, runs on the same server for the Kanban agent ([docs/superpowers/specs/2026-11-28-kanban-trello-design.md](superpowers/specs/2026-11-28-kanban-trello-design.md)). It has its own databases (`n8n_teste`, `zacretario_teste`), its own encryption key and its own credentials, and no WhatsApp. It also has its own Docker network (`teste`), shared only with Postgres and Caddy: it cannot reach production n8n's internal webhooks (`http://n8n:5678/...`, where the WhatsApp entry lives) or Evolution API, and community packages are disabled on it. Changing a service's networks recreates its container, so applying this on a running server takes Postgres and Caddy down for a few seconds.

1. **DNS.** An `A` record `teste` pointing to the server's IP. Caddy gets the certificate by itself on the first request, so the record must exist first.
2. **Secrets.** In `/opt/zacretario/infra/.env`, add `N8N_TESTE_DB_PASSWORD`, `ZACRETARIO_TESTE_DB_PASSWORD` and `N8N_TESTE_ENCRYPTION_KEY`, each with a new `openssl rand -hex 32`, never the production values.
3. **Databases.** `postgres/init.sh` only runs on an empty volume, so on a server that already runs create them by hand, with the same `CREATE ROLE` / `CREATE DATABASE` as the script (load `.env` first with `set -a; . ./.env; set +a`, and pass the password as `psql -v password="$N8N_TESTE_DB_PASSWORD"`). Then apply `sql/001_schema.sql`, `sql/002_conversation.sql` and `sql/003_resumo_diario.sql` to `zacretario_teste` as the user `zacretario_teste`.
4. **Start.** `docker compose up -d n8n-teste`, then `docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile` (no downtime).
   Changing the `environment` of `postgres` (as adding the two passwords does) makes `up` recreate Postgres too: production loses its database connection for about ten seconds. Do it at a quiet hour.
5. **Owner and MCP.** Open `https://teste.<domain>`, create the owner account (its own password), and turn on **Settings → Instance-level MCP**. To use it from Claude Code: `claude mcp add --transport http --scope user n8n-teste https://teste.<domain>/mcp-server/http`, then authenticate in `/mcp`.

6. **Copy production into it, keeping the IDs.** Workflows call each other by ID and nodes point to credentials by ID, so the test copy must use the same IDs: then a workflow changed and tested here imports back into production with no edits.
   - **Credentials:** import a JSON list of `{"id", "name", "type", "data": {}}` with the production IDs and names (`docker compose cp` it into `n8n-teste`, then `n8n import:credentials --input=...`), and fill in the test values in the editor: Postgres → `zacretario_teste`, n8n API → Base URL `http://n8n-teste:5678/api/v1` and a key from the test n8n, new Anthropic and Groq keys named `n8n-teste`. **Evolution API keeps a fake key on purpose**: `n8n-teste` is on the same Docker network as Evolution, and the real key would let it send real WhatsApp messages. Credentials of other people (another person's Google) stay empty: they exist only so the workflows can be published.
   - **Workflows:** `n8n export:workflow --all --separate --output=/tmp/wf/` in `n8n`, `docker compose cp` the folder out and into `n8n-teste`, then `n8n import:workflow --separate --input=/tmp/wf`. They arrive unpublished. Publish the sub-workflows (sub-workflows run their published version); leave **Entrada Whatsapp** and **Testes do agente** unpublished.
   - **Test person:** copy the `teste` rows with `COPY (SELECT * FROM users WHERE key='teste') TO STDOUT` from `zacretario` piped into `COPY users FROM STDIN` on `zacretario_teste` (and the same for `preferences`).
   - Delete the temporary files in the server and in both containers afterwards (`docker compose exec -u root ... rm`).
7. **Promote a change back.** `n8n export:workflow --id=<id>` in `n8n-teste`, copy it into `n8n`, `n8n import:workflow --input=...` (it replaces the workflow with the same ID and unpublishes it), then publish it. The previous version stays in the workflow's history.

The WhatsApp entry webhook is closed in Caddy for `teste.<domain>` too, so a fake message from the internet cannot spend test API credits.

## Trello (Kanban board)

The board and the agent are described in [kanban.md](kanban.md).

1. **Board.** A private board `Zacretário` with the lists `Backlog`, `Em andamento`, `Para teste`, `Pronto` (in this order) and the labels `Bloqueado` and `Na fila`.
2. **API key and token.** At [trello.com/power-ups/admin](https://trello.com/power-ups/admin), create an app that **doesn't use Power-up capabilities** (otherwise an iframe URL is required). Under **Authorization → Trello Auth**, generate the API key, then the token. Keep both in a password manager: together they act as your Trello user, on all your boards. OAuth 2.0 on that page is not used.
   **For GitHub Actions, use a bot account instead:** create a second Trello account, invite it to the `Zacretário` board only (as a member), and generate its own key and token the same way while logged in as the bot. Those go into the `TRELLO_API_KEY` and `TRELLO_TOKEN` repository secrets, so a leak from the agent reaches this board and nothing else.
3. **Claude Code.** Add the MCP server with the values typed in the command itself (on Windows `npx` runs through `cmd /c`):

   ```powershell
   claude mcp add trello --scope user -e TRELLO_API_KEY=<key> -e TRELLO_TOKEN=<token> -- cmd /c npx -y atlassian-trello-mcp@1.7.2
   ```

   The version is pinned on purpose: a new version of third-party code holding the token only comes in when you decide. Version `1.7.2` only talks to `api.trello.com` and Trello attachments, and its telemetry stays off unless `APPLICATIONINSIGHTS_CONNECTION_STRING` is set. Trello's official MCP (`https://mcp.trello.com/v1`) only accepts interactive OAuth, so it cannot run on GitHub Actions.

## Trello listener (Kanban: card movido)

The production n8n listens to the board and starts the agent. The workflow is [workflows/kanban-card-movido.json](../workflows/kanban-card-movido.json), in the **Kanban** folder; its Code nodes are `workflows/code/kanban-montar.js`, `kanban-decidir.js` and `kanban-registrar.js`, tested with `node --test workflows/code/tests/`.

1. **Credentials** in production n8n, typed by you:
   - **Trello API** (`Trello account`): the same API key and token as the Trello MCP.
   - **GitHub API** (`GitHub account`): a fine-grained token for `JulianoDotto/Zacretario` only, with **Contents: Read and write** and nothing else. That is what `POST /repos/{owner}/{repo}/dispatches` requires. Give it an expiry and a calendar reminder: Contents write could also push to branches other than the protected `main`.
2. **Import and publish** `workflows/kanban-card-movido.json`. Publishing registers a Trello webhook on the board; unpublishing removes it. The export has no `webhookId`, so n8n makes a new webhook URL on import.
3. **What it does.** Every board event runs it; anything that is not a card changing lists (comments, labels, including its own) stops at the first Filter. It fetches the open cards in one `GET /1/boards/{id}`, decides with the one-card rule, and then dispatches `card-em-andamento`, adds `Na fila` with a comment, or removes `Na fila`.
4. **Memory.** The workflow's static data keeps the last 50 Trello action ids (a re-delivered webhook is ignored) and the dispatched cards still holding the slot. It is saved only by production executions. Two executions at the same moment can overwrite each other's memory; the agent's `concurrency` group on GitHub Actions makes a duplicate dispatch wait instead of running in parallel.

## Updating

Images are pinned. To update one, change its tag in `infra/docker-compose.yml`, copy the file to the server, and run `docker compose pull <service> && docker compose up -d <service>`. Read the release notes first, especially for Evolution API.
