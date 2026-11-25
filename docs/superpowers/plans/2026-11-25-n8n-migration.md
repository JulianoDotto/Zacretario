# Zacretário no n8n — Plano de implementação (roteiro guiado)

> **Para quem executa:** este plano roda no modo **piloto automático** (spec §2), não em subagentes. O Claude, na sessão principal, navega com o **Claude in Chrome** até a página indicada, explica o passo e o conceito, **o usuário executa a ação**, e o Claude relê a página/execução para conferir. Arquivos do repositório (compose, SQL, Code nodes, docs) o Claude escreve e explica; comandos na VPS o usuário roda. Senhas, chaves e tokens o usuário digita e nunca aparecem no chat. Passos usam checkbox (`- [ ]`).

**Objetivo:** o Zacretário responde no WhatsApp como hoje, agora como workflows do n8n self-hosted com Evolution API, e o repositório vira a vitrine dessa versão.

**Arquitetura:** uma VPS com Docker Compose: Caddy (HTTPS) → n8n; Postgres com três bancos (`n8n`, `evolution`, `zacretario`); Evolution API só na rede interna. Evolution → webhook interno do n8n → workflow **Entrada WhatsApp** → sub-workflow **Agente Zacretário** (AI Agent + ferramentas) → resposta pela Evolution. A agenda passa pelo sub-workflow **Portão de agenda**, com um ramo e uma credencial Google por pessoa.

**Tecnologias:** n8n (versão fixada), Evolution API v2.3.x (fixada), PostgreSQL 16, Caddy 2, Docker Compose, Anthropic (`claude-sonnet-5-5`), Google Calendar API v3, JavaScript nos Code nodes.

**Spec:** [`docs/superpowers/specs/2026-11-25-n8n-migration-design.md`](../specs/2026-11-25-n8n-migration-design.md)

## Restrições globais

- Comportamento de referência: `README.md` (seções Example/Features) e `src/zacretario/agent/prompt.py`. As respostas continuam em pt-BR, com os mesmos formatos (📅/✅, `qui 26/11 10:00`, *negrito* com um asterisco).
- Nada de segredo, telefone real ou ID de agenda real no repositório, inclusive nos JSONs exportados e nos payloads de exemplo (usar `5511900000000`).
- Tudo que muda por pessoa/cliente fica na tabela `users` + credenciais do n8n, nunca fixo dentro de um nó.
- O `user_key` que as ferramentas usam vem sempre do workflow (entrada), **nunca de um parâmetro escolhido pela IA** (`$fromAI`).
- Imagens Docker com versão fixada, nunca `latest`. Evolution na 2.3.x estável (não a 2.4 de teste).
- A porta da Evolution não fica exposta à internet; o painel dela só por túnel SSH.
- Fuso: `America/Sao_Paulo`. Modelo: `claude-sonnet-5-5`. Memória: janela de 20 mensagens.
- Mensagem que não é texto recebe exatamente: `Por enquanto eu só entendo mensagens de texto 🙂`.
- Mensagens longas são divididas em partes de até 4096 caracteres, quebrando por linha (mesma regra de `split_message`).
- Cada etapa termina com uma entrada em `docs/learning-log.md`: o que foi feito, o conceito de n8n aprendido, o que deu errado.
- Commits só com aprovação do usuário, terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Foco da revisão

1. **Laço do bot consigo mesmo:** a resposta enviada pelo bot volta como evento `fromMe` → precisa ser ignorada (teste na Task 4).
2. **Mesma mensagem entregue duas vezes** (reenvio da Evolution, reexecução) → só a primeira é processada (Task 5).
3. **Remetente como `@lid` ou com/sem o 9º dígito** → se não bater com `users`, é ignorado e o identificador exato aparece na execução para copiar (Task 5).
4. **IA tentando mexer nos dados de outra pessoa** ("apaga os TODOs da Bruna") → as ferramentas só enxergam o `user_key` de quem escreveu (Tasks 6 e 7).
5. **POST falso no webhook pela internet** → o caminho do webhook da Entrada não responde de fora; só a Evolution, pela rede interna, alcança (Task 2, conferido na Task 4).

---

### Task 0: Preparar o repositório

**Arquivos:** nenhum (git).

- [ ] **Passo 1:** Claude cria a tag `v1-python` no commit atual e o branch `feat/n8n` a partir de `feat/v1` (usuário aprova os comandos). Conferir: `git tag -l v1-python` lista a tag.
- [ ] **Passo 2:** Claude cria `docs/learning-log.md` com o título e uma entrada "Task 0 — por que n8n" (2–3 linhas, palavras do usuário). Commit `docs: start the n8n learning log`.

### Task 1: Reconhecimento da VPS e do domínio

**Arquivos:** `docs/learning-log.md` (entrada).

- [ ] **Passo 1 (Chrome):** Claude abre o hPanel → VPS. Usuário lê para o Claude: sistema operacional, IP, plano (RAM/disco), se há firewall da Hostinger ativo. Opcional: o usuário conecta o conector da Hostinger para o Claude ler esses dados.
- [ ] **Passo 2 (Chrome):** hPanel → Domínios → `dotton8n.com.br` → DNS. Conferir se existe registro A de `@` apontando para o IP da VPS; se não, **o usuário cria** (conceito: DNS precisa apontar antes de o Caddy pedir o certificado).
- [ ] **Passo 3 (terminal do usuário):** `ssh root@<IP>` e depois `cat /etc/os-release; free -h; df -h /; docker --version`. Conferir: Ubuntu/Debian, ≥ 3 GB de RAM livres no total, Docker presente ou não.
- [ ] **Passo 4:** se o sistema não for Ubuntu 22.04/24.04 ou houver lixo de outra instalação, o Claude propõe reinstalar o SO pelo hPanel (ação destrutiva: confirmar com o usuário antes). Registrar o resultado no learning log.

### Task 2: Infra base — Caddy, Postgres e n8n no ar

**Arquivos:**
- Criar: `infra/docker-compose.yml`, `infra/Caddyfile`, `infra/.env.example`, `infra/postgres/init.sql`
- Criar: `docs/setup.md` (seção "VPS e n8n")

**Produz:** serviços `caddy`, `postgres`, `n8n` na rede `zacretario`; bancos `n8n`, `evolution`, `zacretario`; n8n em `https://dotton8n.com.br`.

- [ ] **Passo 1:** Claude escreve `infra/docker-compose.yml`:
  - `postgres:16-alpine`, volume `pgdata`, `init.sql` montado em `/docker-entrypoint-initdb.d/`, sem porta publicada.
  - `n8nio/n8n:<versão estável atual, fixada>` com `DB_TYPE=postgresdb`, `DB_POSTGRESDB_HOST=postgres`, `DB_POSTGRESDB_DATABASE=n8n`, `N8N_HOST=dotton8n.com.br`, `N8N_PROTOCOL=https`, `WEBHOOK_URL=https://dotton8n.com.br/`, `GENERIC_TIMEZONE=America/Sao_Paulo`, `TZ=America/Sao_Paulo`, `N8N_ENCRYPTION_KEY` (do `.env`), volume `n8n_data`, sem porta publicada.
  - `caddy:2-alpine` com portas 80/443 e volume de certificados.
  - Todos os valores secretos vêm de `infra/.env` (não versionado; `.env.example` com placeholders).
- [ ] **Passo 2:** `infra/postgres/init.sql` cria os usuários/bancos `n8n`, `evolution`, `zacretario` (senhas via variáveis; o script lê do ambiente ou o usuário edita na VPS — Claude decide e explica).
- [ ] **Passo 3:** `infra/Caddyfile`: `dotton8n.com.br` → `reverse_proxy n8n:5678`, **e** `respond /webhook/whatsapp-entrada* 404` antes do proxy (Foco 5).
- [ ] **Passo 4 (terminal do usuário):** instalar Docker se faltar, firewall `ufw allow 22,80,443/tcp`, clonar o repositório na VPS, criar `infra/.env` com segredos gerados por `openssl rand -hex 32`, `docker compose up -d`.
- [ ] **Passo 5 — conferir:** `docker compose ps` mostra os 3 serviços `running`; `https://dotton8n.com.br` abre a tela de criar conta do n8n com cadeado válido; `curl -X POST https://dotton8n.com.br/webhook/whatsapp-entrada` devolve 404.
- [ ] **Passo 6 (Chrome):** usuário cria a conta de dono do n8n (a senha ele digita). Claude mostra rapidamente: Workflows, Credentials, Executions, Settings.
- [ ] **Passo 7:** `docs/setup.md` seção "VPS e n8n", learning log, commit `feat: n8n infrastructure with Caddy and Postgres`.

### Task 3: Evolution API no ar e número pareado

**Arquivos:** Modificar `infra/docker-compose.yml`, `infra/.env.example`, `docs/setup.md` (seção "WhatsApp (Evolution API)").

**Produz:** serviço `evolution` em `http://evolution:8080` (rede interna); instância `zacretario` conectada; credencial do n8n **"Evolution API"** (Header Auth, cabeçalho `apikey`).

- [ ] **Passo 1:** Claude confirma a última tag estável 2.3.x da imagem oficial da Evolution e adiciona o serviço: `DATABASE_PROVIDER=postgresql`, `DATABASE_CONNECTION_URI` para o banco `evolution`, `CACHE_REDIS_ENABLED=false`, `CACHE_LOCAL_ENABLED=true`, `AUTHENTICATION_API_KEY` do `.env`, `SERVER_URL=http://localhost:8080`, porta publicada **só** em `127.0.0.1:8080:8080`. Confirmar nas notas da versão se ela exige registro no servidor de licenças; se exigir, parar e conversar com o usuário.
- [ ] **Passo 2 (terminal do usuário):** `docker compose up -d evolution`; no PC, `ssh -L 8080:127.0.0.1:8080 root@<IP>`.
- [ ] **Passo 3 (Chrome):** Claude abre `http://localhost:8080/manager`; usuário entra com a API key, cria a instância `zacretario` (integração Baileys) e lê o QR code com o celular do chip (WhatsApp ativo nele antes).
- [ ] **Passo 4 (Chrome):** na instância, webhook: URL `http://n8n:5678/webhook/whatsapp-entrada`, evento `MESSAGES_UPSERT`, "webhook by events" desligado, base64 desligado.
- [ ] **Passo 5 — conferir:** o painel mostra a instância `open`; `curl -H "apikey: …" http://127.0.0.1:8080/instance/connectionState/zacretario` (na VPS) devolve `"state":"open"`.
- [ ] **Passo 6 (Chrome):** no n8n, usuário cria a credencial "Evolution API" (Header Auth, nome `apikey`).
- [ ] **Passo 7:** `docs/setup.md` (incluindo o aviso de que a integração é não oficial e a condição de licença da Evolution), learning log, commit `feat: Evolution API service and pairing guide`.

### Task 4: Workflow "Entrada WhatsApp" — eco

**Arquivos:** Criar `workflows/code/normalizar-mensagem.js`, `workflows/code/dividir-mensagem.js`, `workflows/fixtures/messages-upsert-texto.json` (payload real anonimizado).

**Produz:** o Code node **Normalizar mensagem**, que devolve
`{ messageId: string, chatId: string, sender: string, text: string|null, fromMe: boolean, isGroup: boolean, isText: boolean }`;
o Code node **Dividir mensagem**: `{ text } → [{ part: string }]`, até 4096 caracteres por parte.

- [ ] **Passo 1 (Chrome):** usuário cria o workflow "Entrada WhatsApp" com um nó Webhook (POST, caminho `whatsapp-entrada`, responde imediatamente). Ativa o workflow. Manda "oi" do celular pessoal para o número do bot.
- [ ] **Passo 2 — conferir:** em Executions aparece a execução; o Claude lê o payload, salva a versão anonimizada como fixture e o usuário fixa o dado ("Pin data") no Webhook (conceito: pin data permite testar sem mandar mensagem).
- [ ] **Passo 3:** Claude escreve `normalizar-mensagem.js` a partir do payload real (texto em `message.conversation` ou `message.extendedTextMessage.text`; grupo = `remoteJid` terminando em `@g.us`; `sender` = o telefone quando o payload o trouxer, senão o `@lid`). Usuário cola no Code node e executa com o pin data. Conferir: a saída tem os 7 campos com os valores do fixture.
- [ ] **Passo 4:** nó IF "Deve responder?": `fromMe = false` **e** `isGroup = false`; ramo falso termina. Nó IF "É texto?": falso → HTTP Request para a Evolution com o texto `Por enquanto eu só entendo mensagens de texto 🙂`.
- [ ] **Passo 5:** ramo texto → `dividir-mensagem.js` → HTTP Request `POST http://evolution:8080/message/sendText/zacretario`, credencial "Evolution API", corpo `{ "number": chatId, "text": part }`, devolvendo o próprio texto (eco).
- [ ] **Passo 6 — conferir no WhatsApp:**
  - "oi" → o bot responde "oi" **uma vez só** (Foco 1: a resposta `fromMe` não gera outro eco).
  - uma figurinha ou áudio → aviso de só texto.
  - mensagem num grupo com o bot → nada.
  - `curl -X POST https://dotton8n.com.br/webhook/whatsapp-entrada` de fora → 404 (Foco 5).
- [ ] **Passo 7:** learning log, commit `feat: WhatsApp entry workflow (echo)`.

### Task 5: Banco `zacretario`, configuração e proteções

**Arquivos:** Criar `infra/sql/001_schema.sql`, `infra/sql/seed.example.sql`.

**Produz** (schema usado pelas tasks seguintes):
- `users(key text primary key, whatsapp_id text unique not null, name text not null, calendar_id text not null default 'primary', timezone text not null default 'America/Sao_Paulo', active boolean not null default true)`
- `preferences(user_key text primary key references users(key), day_start time not null default '08:00', day_end time not null default '22:00', blocked_weekdays int[] not null default '{}')` — dias com 0 = segunda, como hoje.
- `todos(id serial primary key, user_key text not null references users(key), text text not null, done boolean not null default false, created_at timestamptz not null default now(), done_at timestamptz)`
- `processed_messages(message_id text primary key, received_at timestamptz not null default now())`
- Credencial do n8n **"Postgres Zacretário"** (banco `zacretario`).

- [ ] **Passo 1:** Claude escreve o schema e o seed de exemplo (números falsos). Usuário aplica com `docker compose exec -T postgres psql -U … zacretario < infra/sql/001_schema.sql` e insere as linhas reais dele e da Bruna **direto na VPS** (não no repositório).
- [ ] **Passo 2 (Chrome):** usuário cria a credencial "Postgres Zacretário" (host `postgres`).
- [ ] **Passo 3:** na Entrada, depois de "Deve responder?": Postgres "Marcar como processada": `INSERT INTO processed_messages(message_id) VALUES ($1) ON CONFLICT DO NOTHING RETURNING message_id`; sem linha → termina. Conferir: executar o mesmo pin data duas vezes → a segunda para nesse nó (Foco 2). Limpar a linha de teste depois.
- [ ] **Passo 4:** Postgres "Buscar usuário": `SELECT * FROM users WHERE whatsapp_id = $1 AND active`; sem linha → nó No Op "Número desconhecido" (o `sender` fica visível na execução para copiar). Conferir: mandar de um número fora de `users` → para em "Número desconhecido" e mostra o identificador exato (Foco 3).
- [ ] **Passo 5:** learning log, commit `feat: zacretario database, allowlist and dedup`.

### Task 6: Workflow "Agente Zacretário" com TODOs e preferências

**Arquivos:** Criar `workflows/prompt.md` (prompt de `prompt.py` adaptado).

**Consome:** `users`, `todos`, `preferences` (Task 5); Entrada (Task 4).
**Produz:** sub-workflow "Agente Zacretário" com Execute Workflow Trigger de entradas `{ user_key: string, name: string, timezone: string, text: string }` e saída `{ output: string }`.

- [ ] **Passo 1:** Claude adapta o prompt: `{user_name}` → `{{ $json.name }}`; `{now}` → expressão com Luxon no fuso de `timezone` com dia da semana em pt-BR; remove nomes de ferramentas que mudarem. Guarda em `workflows/prompt.md`.
- [ ] **Passo 2 (Chrome):** usuário monta: Trigger → AI Agent (system message = prompt) com Anthropic Chat Model (credencial "Anthropic", `claude-sonnet-5-5`) e Postgres Chat Memory (credencial "Postgres Zacretário", chave de sessão `{{ $json.user_key }}`, janela 20).
- [ ] **Passo 3:** ferramentas Postgres Tool: `add_todo`, `list_todos`, `complete_todo`, `delete_todo`, `get_preferences`, `update_preferences`. Em todas, `user_key` vem de `{{ $('Execute Workflow Trigger').item.json.user_key }}`; só texto, id e campos de preferência vêm de `$fromAI` (Foco 4). As descrições das ferramentas são as do Python (`todo_tools.py`, `preference_tools.py`).
- [ ] **Passo 4:** na Entrada, trocar o eco: "Buscar usuário" → Execute Workflow "Agente Zacretário" → Dividir mensagem → envio.
- [ ] **Passo 5 — conferir no WhatsApp:**
  - "Comprar ração dos gatos" → `✅ TODO adicionado: …`
  - "o que tenho pra fazer?" → bloco de TODOs (agenda ainda indisponível, uma linha).
  - "apaga a ração" → pede confirmação; "sim" → apaga; mandar "não" em outro teste → nada é apagado.
  - "escreve um poema" → recusa.
  - "apaga os TODOs da Bruna" → só enxerga os seus (Foco 4).
  - "não marca nada no domingo" → `preferences.blocked_weekdays` contém 6.
- [ ] **Passo 6:** learning log, commit `feat: agent workflow with todos and preferences`.

### Task 7: Portão de agenda e ferramentas do Google Calendar

**Arquivos:** Criar `workflows/code/montar-requisicao-agenda.js`, `workflows/code/checar-somente-leitura.js`, `workflows/code/horarios-livres.js`.

**Produz:** sub-workflow "Portão de agenda", entradas `{ user_key: string, calendar_id: string, timezone: string, operation: 'create'|'list'|'update'|'delete'|'freebusy', params: object }`, saída `{ ok: boolean, result?: object, error?: string }`. Credenciais **"Google Calendar – Juliano"** e **"Google Calendar – Bruna"** (Google Calendar OAuth2 API).

- [ ] **Passo 1 (Chrome):** Google Cloud Console, projeto OAuth já usado no Python: adicionar o redirect `https://dotton8n.com.br/rest/oauth2-credential/callback`. No n8n, o usuário cria a credencial dele; a Bruna entra com a própria conta na credencial dela (cada um digita o próprio login).
- [ ] **Passo 2:** `montar-requisicao-agenda.js` transforma `operation + params` em `{ method, url, qs, body }` da API v3 (`events.insert`, `events.list` com `singleEvents=true&orderBy=startTime`, `events.patch`, `events.delete`, `freeBusy.query`), com horários no fuso recebido.
- [ ] **Passo 3:** Portão: Trigger → montar → para `update`/`delete`: buscar o evento antes e `checar-somente-leitura.js` (organizador não é `self` **ou** há convidados → `{ ok:false, error:'evento com outros participantes' }`) → Switch por `user_key` → um HTTP Request por pessoa ("Predefined credential type" = Google Calendar OAuth2, cada um com sua credencial) → resposta resumida.
- [ ] **Passo 4:** `horarios-livres.js` porta `src/zacretario/scheduling.py`: janela `day_start–day_end` das preferências, folga de 15 min antes/depois de cada compromisso, passo de 15 min, no máximo um horário por dia, pula dias bloqueados. Claude mostra os casos de teste de `tests/` correspondentes e o usuário roda o Code node com esses dados fixados; mesmos resultados.
- [ ] **Passo 5:** no Agente, ferramentas "Call n8n Workflow Tool" `create_event`, `list_events`, `update_event`, `delete_event`, `find_free_slots` (`user_key`, `calendar_id` e `timezone` vêm do Trigger; só `params` vem de `$fromAI`). Descrições das de `calendar_tools.py`.
- [ ] **Passo 6 — conferir no WhatsApp (os dois usuários):**
  - "Dentista, quinta-feira, 10h da manhã" → `📅 Dentista: qui … 10:00–11:00` na agenda **de quem mandou**.
  - "pagar IPVA sexta" → evento de dia inteiro.
  - "cancela o dentista" → confirmação → "sim" → cancelado.
  - tentar remarcar um convite de outra pessoa → recusa explicando que é pelo app da agenda.
  - "preciso de 2h pra estudar essa semana" → propostas; só cria depois do "sim".
  - Bruna manda "o que tenho amanhã?" → vê só a agenda dela.
- [ ] **Passo 7:** `docs/setup.md` (Google), learning log, commit `feat: calendar gateway with per-person Google credentials`.

### Task 8: Workflow de erros

**Arquivos:** nenhum novo além do export.

- [ ] **Passo 1 (Chrome):** workflow "Erros": Error Trigger → HTTP Request para a Evolution mandando ao dono (whatsapp_id do Juliano vindo de `users` com `key='juliano'`) `⚠️ Zacretário falhou em <workflow> / <nó>. Veja Executions.` Nas configurações da Entrada, do Agente e do Portão, "Error workflow" = Erros.
- [ ] **Passo 2:** na Entrada, se o Agente falhar, a pessoa recebe `Tive um problema agora, tenta de novo em instantes.` (o nó do Agente com "Continue on fail" + IF).
- [ ] **Passo 3 — conferir:** desativar temporariamente a credencial Anthropic (trocar a chave por uma inválida), mandar mensagem → a pessoa recebe o aviso e o Juliano recebe o alerta; restaurar a chave.
- [ ] **Passo 4:** learning log, commit `feat: error workflow`.

### Task 9: Vitrine — exportação, docs, README e aposentar o Python

**Arquivos:**
- Criar: `workflows/*.json` (Entrada WhatsApp, Agente Zacretário, Portão de agenda, Erros), `docs/why-n8n-evolution.md`
- Modificar: `README.md`, `docs/future-improvements.md`, `PRIVACY.md`, `docs/setup.md`, `.gitignore`
- Remover: `src/`, `tests/`, `migrations/`, `scripts/`, `deploy/`, `pyproject.toml`, `uv.lock`, `alembic.ini`, `docker-compose.yml` (raiz), `docs/local-setup.md`, `docs/deploy.md`

- [ ] **Passo 1 (Chrome):** usuário baixa cada workflow (Download) para `workflows/`. Claude varre os JSONs por telefones, IDs de agenda, e-mails e chaves (`grep -E "55[0-9]{10,11}|@gmail|apikey|sk-ant"`); nada pode aparecer. IDs de credenciais podem ficar (não são segredos).
- [ ] **Passo 2:** `docs/why-n8n-evolution.md`: Python → n8n (aprendizado e freelances), Meta → Evolution (burocracia, opções da spec §6, custo e licença), riscos aceitos (spec §8), o que fazer se o número for banido.
- [ ] **Passo 3:** README: diagrama novo (WhatsApp → Evolution → n8n: Entrada → Agente → Portão/Postgres), stack, "Getting started" apontando para `docs/setup.md`, seção "How it was built" mencionando a tag `v1-python` e o learning log, aviso de integração não oficial e crédito à Evolution API (condição de licença). Exemplo de conversa mantido.
- [ ] **Passo 4:** `future-improvements.md` (lembretes proativos sem janela de 24h; template por cliente com um ramo no Portão), `PRIVACY.md` (Meta → Evolution/n8n), remover os arquivos Python e as docs antigas; `docs/meta-whatsapp-notes.md` ganha aviso no topo apontando para `why-n8n-evolution.md`.
- [ ] **Passo 5 — conferir:** todos os links do README e de `docs/` resolvem (`grep -o "](\([^)]*\))"` + checagem dos caminhos); um teste final no WhatsApp com os exemplos do README.
- [ ] **Passo 6:** learning log (retrospectiva), commit `feat!: Zacretário runs on n8n; retire the Python app`. Push e PR ficam a critério do usuário.
