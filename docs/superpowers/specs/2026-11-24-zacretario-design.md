# Zacretário — Design

Data: 2026-11-24
Status: rascunho para aprovação

## 1. Intenção

O Zacretário é um secretário pessoal que vive numa conversa de WhatsApp. O usuário escreve em linguagem natural ("Dentista, quinta-feira, 10h da manhã", "Comprar ração dos gatos", "o que tenho pra fazer?") e o secretário registra compromissos no Google Calendar, mantém uma lista de TODOs, responde consultas e ajuda a encaixar atividades na agenda.

**Por quê:**
1. **Uso pessoal** do autor e da esposa: anotar coisas sem sair do WhatsApp.
2. **Portfólio no GitHub:** a mensagem central é *"eu consigo usar IA para desenvolver software e soluções"* — tanto IA dentro do produto (um agente com ferramentas) quanto IA no processo de desenvolvimento (specs, planos e implementação conduzidos com IA, registrados no repositório).
3. **Aprendizado:** o autor não domina Python/FastAPI e quer aprender com o projeto. O código deve ser idiomático e legível, sem truques.

## 2. Objetivos

- Receber mensagens de texto de dois números autorizados via **WhatsApp Cloud API oficial (Meta)**.
- Interpretar cada mensagem com um **LLM (Claude, via API da Anthropic) com tool use**; não há sintaxe de comandos.
- Habilidades (cada uma é uma ferramenta do agente):
  - **Registrar evento** no Google Calendar do usuário.
  - **Registrar TODO**.
  - **Listar agenda** (eventos) e **listar TODOs**, em blocos separados.
  - **Concluir TODO** ("comprei a ração").
  - **Corrigir / remarcar / cancelar evento** ("o dentista é na sexta", "cancela o dentista").
  - **Apagar TODO**.
  - **Planejar encaixe**: dado um pedido ("preciso de 2h pra estudar essa semana"), olhar a agenda e propor horários livres.
- Responder sempre com uma **confirmação** do que foi feito (ex.: "📅 Dentista: qui 27/11, 10h–11h").
- Código bonito, testado e documentado **na medida**, pronto para ser público no GitHub.

## 3. Não-objetivos (v1)

- Compartilhar eventos ou TODOs entre os dois usuários (possível no futuro; ver §9).
- Áudio, imagens, documentos ou mensagens encaminhadas: v1 é **somente texto**. Mensagens de outros tipos recebem uma resposta educada dizendo que só texto é suportado.
- Lembretes/notificações enviados pelo Zacretário — o próprio calendário (iPhone/Google) já notifica.
- Outlook ou iCloud Calendar. (O Google Calendar aparece no app Calendário do iPhone ao adicionar a conta Google.)
- Interface web, painel administrativo, multi-tenant, cadastro de novos usuários.
- Uso por terceiros / produção para público.

## 4. Anti-objetivos (seria fracasso mesmo funcionando)

- **Criar eventos errados em silêncio.** Na dúvida real, o secretário pergunta; a confirmação sempre mostra o que foi entendido.
- **Executar ação destrutiva sem confirmar** (apagar, cancelar, ou qualquer ação ambígua como "cancela a reunião" quando há duas).
- **Responder a números não autorizados** ou expor dados de um usuário para o outro.
- **Segredos no repositório** (chaves, tokens, números de telefone).
- Código "esperto" ou superengenheirado que um iniciante em Python não consiga ler — ou documentação inchada.

## 5. Regras de comportamento

**Classificação padrão (aplicada com bom senso pelo LLM, não à risca):**
- Mensagem com **dia e/ou hora** (data, dia da semana, "amanhã", "10h") → **evento** no calendário.
- Mensagem **sem** dia nem hora → **TODO**.

**Defaults de evento:**
- Dia sem hora ("Pagar IPVA sexta") → **evento de dia inteiro**.
- Hora sem dia ("Ligar pro João às 16h") → **próxima ocorrência** dessa hora (hoje se ainda não passou, senão amanhã).
- Dia da semana ("quinta") → **próxima** quinta (se hoje é quinta e a hora ainda não passou, hoje).
- Evento com hora e sem duração → **1 hora**.
- Fuso horário: **America/Sao_Paulo** (configurável).

**Ambiguidade e confirmação:**
- Se a intenção ou a data for genuinamente ambígua ("reunião com o Pedro"), **pergunta** antes de registrar.
- **Ações destrutivas** (apagar TODO, cancelar evento) e alterações em itens ambíguos pedem **confirmação** ("Cancelo 'Dentista' de qui 27/11 10h? (sim/não)").
- **Planos de encaixe** são apenas propostas; só viram eventos após aprovação do usuário.

**Consultas:**
- Linguagem livre: "o que tenho pra fazer?", "quais são meus compromissos?", "tenho algo amanhã?".
- Sem período informado → eventos dos **próximos 7 dias** + **todos os TODOs em aberto**.
- Com período ("amanhã", "essa semana", "sexta") → respeita o período.
- Agenda e TODOs em blocos separados.

**Quais eventos o secretário pode mexer** *(decisão do Claude)*:
- **Listar:** todos os eventos do calendário `primary` do usuário, inclusive os que ele não criou.
- **Alterar/cancelar:** qualquer evento do `primary` **sem outros participantes**, sempre com confirmação. Eventos que ele mesmo criou são marcados (ex.: `extendedProperties.private.zacretario=true`) para facilitar a busca.
- **Eventos com outros participantes** (reuniões de trabalho, convites): o secretário **não altera nem cancela**; avisa que isso deve ser feito no app do calendário, para nunca disparar convites ou cancelamentos para terceiros. Alterações usam `sendUpdates=none`.

**Horários disponíveis para encaixe** *(decisão do Claude)*:
- Janela padrão **08:00–22:00, todos os dias**.
- **Personalizável por cada usuário pela própria conversa** (ex.: "meu horário livre é das 7h às 23h", "não marca nada no domingo"). A preferência fica salva no banco por usuário; isso é mais uma ferramenta do agente (ler/alterar preferências).
- Folga mínima de **15 min** entre o encaixe e eventos existentes.
- O usuário pode sobrescrever no pedido ("de manhã", "só no fim de semana"); o LLM traduz isso em parâmetros da ferramenta.

**Layout das mensagens:** a definir durante a implementação junto com o autor (confirmações, listas). Começar com algo simples e legível usando emojis discretos (📅 evento, ✅ TODO).

## 6. Usuários e dados

- **Dois usuários**, identificados pelo número de WhatsApp, configurados via variável de ambiente (lista de números autorizados → nome do usuário).
- **Tudo separado:** cada usuário tem seu próprio Google Calendar e sua própria lista de TODOs. Nenhum usuário vê ou altera dados do outro.
- Mensagens de números fora da lista são **ignoradas** (sem resposta, sem chamada ao LLM), apenas registradas em log.

## 7. Abordagens consideradas (integração com WhatsApp)

| Abordagem | Prós | Contras |
|---|---|---|
| **A) WhatsApp Cloud API oficial (Meta)** — escolhida | Suportada, sem risco de ban, estável; conversas iniciadas pelo usuário sem custo na Meta; boa vitrine no portfólio | Setup burocrático (conta dev Meta, app, número dedicado); exige servidor público com HTTPS para o webhook |
| B) Biblioteca não oficial (Baileys / whatsapp-web.js) | Setup rápido via QR code | Viola os termos do WhatsApp, risco de ban; sessão instável; passa imagem de gambiarra |
| C) Intermediário pago (Twilio) | Boa documentação, setup um pouco mais amigável | Custo por mensagem sem vantagem real para 2 usuários |

Telegram foi descartado: o autor quer WhatsApp especificamente.

**Escolha do autor:** A — API oficial.

## 8. Arquitetura

**Stack (decidida pelo autor):** Python + FastAPI.
**Demais escolhas (do Claude, aceitas pelo autor):**
- **LLM:** Claude via API da Anthropic, com tool use. Modelo default `claude-sonnet-5-5`, configurável por variável de ambiente.
- **Calendário:** Google Calendar API, **somente o calendário `primary`** de cada usuário (confirmado pelo autor: nenhum dos dois precisa que outros calendários sejam consultados), com OAuth do próprio usuário autorizado uma única vez.
- **Banco de dados:** **PostgreSQL no Neon** (escolha do autor), para TODOs, preferências e histórico de conversa. Acesso via SQLAlchemy 2 + Alembic para migrações (sugestão), atrás de uma camada pequena de repositório.
- **Hospedagem:** **Hostinger** (o autor já tem conta), desde que seja um plano VPS — ver §10. Como o banco fica no Neon, o servidor não guarda estado em disco.

**Fluxo de uma mensagem:**

```
WhatsApp (usuário) ──► Meta Cloud API ──► POST /webhook (FastAPI)
                                               │ 1. valida assinatura (X-Hub-Signature-256)
                                               │ 2. responde 200 imediatamente
                                               │ 3. ignora duplicatas (id da mensagem) e números não autorizados
                                               ▼
                                        tarefa em background
                                               │ carrega histórico recente da conversa do usuário
                                               ▼
                                        Agente (Claude + ferramentas)
                                        ├─ calendar: criar/listar/atualizar/cancelar/buscar horários livres
                                        └─ todos:    criar/listar/concluir/apagar
                                               │
                                               ▼
                                  resposta ──► Meta Cloud API ──► WhatsApp (usuário)
```

**Componentes (módulos sugeridos):**
- `webhook` — rotas FastAPI: `GET /webhook` (verificação do token da Meta) e `POST /webhook` (recebimento).
- `whatsapp` — cliente para enviar mensagens e parsear o payload da Meta.
- `agent` — monta o prompt de sistema (persona de secretário, data/hora atual, fuso, regras da §5), define as ferramentas e roda o loop de tool use.
- `tools/calendar` — wrapper do Google Calendar (por usuário).
- `tools/todos` — repositório de TODOs no Postgres.
- `conversation` — histórico curto por usuário, para o contexto de perguntas e confirmações ("sim, pode cancelar").
- `config` — leitura de variáveis de ambiente (pydantic-settings).
- `scripts/authorize_google.py` — script local que roda o fluxo OAuth uma vez por usuário e grava o refresh token.

**Memória de conversa:** guardar as últimas N trocas por usuário (sugestão: ~20 mensagens ou últimas 24h) no Postgres, para que respostas como "sim" ou "a segunda opção" funcionem. Confirmações pendentes vivem nesse histórico; o LLM decide com base nele.

**Contas e etapas de setup:**
- Uma única **conta Meta (desenvolvedor/Business)**, do autor, e **um único número** para o Zacretário. A esposa não precisa de conta Meta nem de número novo: ela conversa com o Zacretário pelo próprio WhatsApp; o número dela só entra na allowlist. Cada usuário autoriza a própria conta Google uma vez.
- Ainda não existem conta Meta nem número dedicado. Por isso o plano começa por um **marco local**: o servidor roda no computador do autor, exposto por um túnel HTTPS (ex.: cloudflared ou ngrok), usando o **número de teste gratuito da Meta** com os dois números cadastrados como destinatários. Número definitivo e hospedagem vêm num marco posterior.

**Credenciais de longa duração** *(armadilhas conhecidas)*:
- **Meta:** o token temporário do painel expira em 24h; usar um **token permanente de System User** do Business Manager.
- **Google:** apps OAuth em status "Testing" têm refresh tokens que expiram em 7 dias. O app deve ser **publicado (In production) sem verificação**; cada usuário aceita a tela de aviso "app não verificado" uma vez. O README deve explicar isso.

**Segurança:**
- Validar a assinatura de cada webhook com o App Secret da Meta.
- Allowlist de números.
- Segredos somente em variáveis de ambiente; `.env.example` documentado; `.env`, banco e tokens no `.gitignore`.

**Política da Meta sobre IA:** desde 15/01/2026 os termos do WhatsApp Business proíbem *chatbots de IA de uso geral* (do tipo ChatGPT) na API; bots de IA com **tarefa específica** continuam permitidos, e não há exigência de usar a IA da Meta. Por isso o Zacretário deve se manter um **secretário de agenda e tarefas**: o prompt de sistema restringe o escopo a essas habilidades e recusa educadamente pedidos fora dele ("escreve um poema", "me explica física quântica"). Isso também é requisito de produto, não só de conformidade.

## 9. Futuro e modularidade

As ideias futuras ficam registradas em um documento próprio, `docs/future-improvements.md` (criado junto com o projeto), e não entram na v1. Lista inicial:
- Itens compartilhados do casal (ex.: lista da casa).
- Áudio (transcrição), imagens e mensagens encaminhadas.
- Lembretes proativos.
- Outros calendários (Outlook, iCloud) e outros canais (Telegram).

O código da v1 deve estar **pronto para receber essas melhorias** sem reescrita, via alguns pontos de extensão simples — sem frameworks de plugin:
- **Habilidades do agente** registradas num único lugar (cada ferramenta = schema + função); adicionar uma habilidade não exige mexer no loop do agente.
- **Calendário atrás de uma interface** (ex.: um `Protocol` `CalendarProvider`), com o Google como primeira implementação.
- **Canal de mensagens separado do agente**: o agente recebe texto e devolve texto; o WhatsApp é só o adaptador. Tratamento por tipo de mensagem (texto hoje; áudio depois) num ponto único.
- **Dono dos dados explícito:** cada TODO/preferência tem `owner`, para que um dono "casa" seja adicionável depois.

## 10. Deixado para o construtor

- Estrutura exata de pastas e nomes de módulos (desde que fique idiomática e legível e respeite os pontos de extensão da §9).
- **Hostinger:** precisa ser um plano **VPS** (processo Python sempre ligado + HTTPS público). Hospedagem compartilhada/web não serve. O autor tem o **VPS KVM 1** — atende com folga (o trabalho pesado é feito pelas APIs da Anthropic, Google e Meta).
- Detalhes do deploy na VPS Hostinger (Docker ou systemd, proxy reverso com HTTPS via Caddy ou Nginx + Let's Encrypt).
- Ferramentas de qualidade: sugestão `uv` para dependências, `ruff` para lint/format, `pytest` para testes.
- Formato exato do histórico de conversa e o valor de N.
- Estratégia de testes: unitários nas ferramentas (calendar com Google mockado, todos contra um Postgres de teste — container local ou branch do Neon) e no parsing do webhook; testes do agente com o LLM mockado verificando que as ferramentas certas são chamadas. Um pequeno conjunto opcional de testes "ao vivo" contra o LLM real para os exemplos-chave da §5.
- Tratamento de falhas externas (Google/Anthropic/Meta fora): responder ao usuário que algo deu errado e registrar em log; sem filas ou retries elaborados.

## 11. Documentação e portfólio

- **README em inglês** (decisão do autor, pensando no portfólio): o que é, conversa de exemplo, arquitetura em um diagrama simples, como configurar (Meta, Google, Anthropic, Neon) e rodar, como testar.
- Seção **"Como foi construído"**: o projeto foi desenhado e implementado com IA (brainstorm → design → plano → implementação). Os documentos em `docs/superpowers/` ficam versionados como evidência do processo.
- Comentários no código apenas onde o *porquê* não é óbvio. Como o autor está aprendendo Python/FastAPI, a implementação deve preferir construções explícitas e padrões idiomáticos a abstrações; explicações didáticas ficam na conversa durante a implementação, não espalhadas no código.
