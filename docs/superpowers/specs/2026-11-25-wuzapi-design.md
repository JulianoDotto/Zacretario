# Troca da WhatsApp Cloud API (Meta) pela WuzAPI — Design

Data: 2026-11-25
Status: substituído por [2026-11-25-n8n-migration-design.md](2026-11-25-n8n-migration-design.md) (nunca implementado)

## 1. Intenção

Substituir a WhatsApp Cloud API oficial da Meta pela [WuzAPI](https://github.com/asternic/wuzapi) como canal do Zacretário, e **documentar por que a troca foi feita**.

**Por quê:** sumir com a burocracia da Meta. A primeira configuração real (registrada em [`docs/meta-whatsapp-notes.md`](../../meta-whatsapp-notes.md)) passou por: publicação do app, assinatura da WABA, número de teste que não entrega no Brasil (130497), número da Meta bloqueado até aprovação do nome de exibição (131037), que na prática exige verificação de empresa com CNPJ, tokens que expiram e callback URL que muda a cada túnel. Para um projeto pessoal de dois usuários, esse custo não se paga.

A WuzAPI é um serviço REST em Go, licença MIT, sobre a biblioteca `whatsmeow` (protocolo multi-device do WhatsApp Web, **não oficial**). O número é conectado lendo um QR code, como no WhatsApp Web.

## 2. Objetivos

- O bot continua fazendo exatamente o que faz hoje, para os mesmos usuários, com as mesmas mensagens; só o canal muda.
- A Meta sai do código, da configuração (`.env.example`, `config.py`) e do caminho de setup/deploy.
- Um documento de decisão em `docs/` explica a troca: o problema, as opções consideradas, a escolha e os riscos aceitos. Ele vira uma seção curta no README.
- O webhook continua autenticado (HMAC da WuzAPI) e protegido contra duplicatas e números desconhecidos, como hoje.

## 3. Não-objetivos

- Manter a Meta como opção alternativa (descartado: ver §5).
- Novos tipos de mensagem (áudio, imagem), grupos, lembretes proativos. A troca *facilita* lembretes (não há janela de 24h nem templates), mas isso fica para depois; só atualizar a nota em `future-improvements.md`.
- Usar o número pessoal do usuário.

## 4. Anti-objetivos

- **Ligar o bot ao número pessoal** de alguém: o bot leria todas as conversas e responderia como a pessoa, e um banimento derrubaria o WhatsApp real dela.
- **Expor a WuzAPI à internet.** Ela controla a conta de WhatsApp inteira; quem chega nela manda mensagem como o bot.
- **Esconder o risco.** O README e o documento de decisão dizem claramente que a integração é não oficial e pode levar a banimento do número.
- O bot responder às próprias mensagens (laço infinito) ou a grupos.

## 5. Abordagens consideradas

| | Abordagem | A favor | Contra |
|---|---|---|---|
| **A (escolhida)** | Trocar de vez pela WuzAPI | Some toda a burocracia; um canal só, código simples | Risco de banimento; protocolo não oficial pode quebrar; mais um serviço na VPS |
| B | Os dois canais, escolhidos por variável de ambiente | Meta como plano B; mostra o canal trocável | Dois adaptadores para manter, testar e documentar — mantém justamente o que se quer eliminar |
| C | Ficar na Meta e registrar um chip próprio (item 6 das notas) | Oficial; resolve o 131037 | Não tira a burocracia, só remove o último bloqueio dela |

O usuário escolheu **A**.

## 6. Decisões tomadas

**Pelo usuário:**
- Abordagem A, troca completa.
- Documentar o processo e o motivo da troca.
- **Situação atual:** nada está na VPS; tudo roda local. O chip dedicado nunca foi registrado na Meta (o teste parou no erro 131037 com o número fornecido pela Meta). Portanto **não há migração**: `deploy.md` e `local-setup.md` são guias de instalação do zero, e o chip pode ser pareado direto por QR code. O app da Meta pode ser apagado pelo usuário quando quiser; isso não faz parte do trabalho.

**Pelo Claude (propostas, podem ser corrigidas):**
- **Número dedicado** (um chip só para o bot), não o pessoal. O fluxo continua o de hoje: os usuários mandam mensagem para o bot.
- **WuzAPI roda em Docker na mesma VPS**, publicada só em `127.0.0.1:8080`. O FastAPI chama a WuzAPI em `http://127.0.0.1:8080`; a WuzAPI chama o webhook em `http://127.0.0.1:8000/webhook`. Nada disso passa pela internet.
- **Consequência no deploy: Caddy, domínio e DNS deixam de ser necessários**, porque ninguém de fora precisa chamar o webhook. As seções correspondentes saem do caminho principal de `deploy.md`/`local-setup.md` (e `deploy/Caddyfile` é removido); o firewall passa a abrir só a porta 22. O pareamento por QR code e a administração da WuzAPI são feitos por túnel SSH (`ssh -L 8080:127.0.0.1:8080`).
- **Localmente também não há mais túnel** (`cloudflared`): a WuzAPI roda no `docker-compose.yml` ao lado do Postgres de teste e chama o app na máquina host.
- **Uma instância pareada por vez.** O WhatsApp aceita vários dispositivos vinculados, então uma WuzAPI local e a da VPS pareadas ao mesmo número receberiam e responderiam tudo em dobro. As docs dizem explicitamente: para rodar localmente, desparear (ou parar) a da VPS antes, e vice-versa. Os testes automatizados não dependem da WuzAPI.
- **Banco da WuzAPI:** SQLite no volume do container (padrão dela), separado do Neon. É só o estado da sessão do WhatsApp.
- **Formato do webhook: JSON** (`WEBHOOK_FORMAT=json`), assinado com HMAC-SHA256 sobre o corpo cru (cabeçalho `x-hmac-signature`).
- **Assinatura obrigatória:** o app recusa (401) webhook sem assinatura válida, como hoje.
- **Assinatura de eventos:** só `Message`.
- **Filtros no parser:** ignorar mensagens enviadas pelo próprio número (`IsFromMe`), mensagens de grupo, reações e eventos que não são mensagem.
- **Versão da WuzAPI fixada** (tag ou digest da imagem), não `latest`, para atualizações conscientes.
- **Documento de decisão** em inglês, como o resto de `docs/`: `docs/why-wuzapi.md`. `meta-whatsapp-notes.md` fica, como evidência histórica, com um aviso no topo apontando para o documento novo.

## 7. O que muda no código

O resto do app conhece só `IncomingMessage` e `MessageSender`; o agente, o serviço, os repositórios e o banco não mudam.

- `src/zacretario/channels/whatsapp.py`: novo conteúdo para a WuzAPI.
  - `verify_signature(hmac_key, body, header)`: HMAC-SHA256 hexadecimal do corpo cru, comparado em tempo constante. Confirmar contra a WuzAPI se o hex vem com ou sem prefixo.
  - `parse_webhook(payload) -> list[IncomingMessage]`: lê o evento `Message`. Remetente, id e texto ficam em `event.Info` / `event.Message`; **os caminhos exatos não estão na documentação e precisam ser confirmados com um payload real** (capturado e salvo como fixture em `tests/channels/payloads.py`). O texto pode vir em `conversation` ou `extendedTextMessage.text`.
  - `WhatsAppClient.send_text`: `POST {base_url}/chat/send/text` com cabeçalho `Token` e corpo `{"Phone": ..., "Body": ...}`. `split_message` continua.
  - Remetente: o WhatsApp está migrando para identificadores `@lid` que não são o telefone, e isso pode ser o caso normal, não a exceção. Decisão (do Claude): `IncomingMessage` passa a ter **dois campos**: `sender` (identificador usado para achar o dono: o telefone quando a WuzAPI o fornecer, seja pelo JID `@s.whatsapp.net` ou pelo campo alternativo do evento; senão o LID) e `reply_to` (o JID exatamente como chegou, usado no envio). `ALLOWED_USERS` aceita telefones **e** LIDs como chave. Mensagem de remetente desconhecido continua sendo ignorada com o log `Ignoring message from unknown number …`, que já mostra o valor exato a copiar para `ALLOWED_USERS` — o mesmo recurso que hoje resolve o caso do 9º dígito. `service.py` passa a responder para `reply_to`.
- `src/zacretario/main.py`: sai o `GET /webhook` (desafio da Meta); o `POST /webhook` passa a ler `x-hmac-signature`. O resto do fluxo (200 rápido, tarefa em segundo plano) continua.
- `src/zacretario/config.py` e `.env.example`: saem `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_API_VERSION`. Entram `WUZAPI_URL` (padrão `http://127.0.0.1:8080`), `WUZAPI_USER_TOKEN` e `WUZAPI_HMAC_KEY` (mín. 32 caracteres).
- `service.py`: a docstring de `resolve_owner` cita a Cloud API; ajustar o texto. A tolerância ao 9º dígito continua necessária.
- Testes: `tests/channels/` reescrito para os payloads da WuzAPI; `test_main.py` e `test_config.py` ajustados. Os demais não mudam.

## 8. O que muda na infraestrutura e nas docs

- `docker-compose.yml`: serviço `wuzapi` (imagem com versão fixada, porta `127.0.0.1:8080:8080`, volume para os dados, variáveis `WUZAPI_ADMIN_TOKEN`, `WUZAPI_GLOBAL_ENCRYPTION_KEY`, `WEBHOOK_FORMAT=json`). Para o app no host ser alcançável de dentro do container localmente, usar `host.docker.internal` (Docker Desktop no Windows) — na VPS, `network_mode: host` ou equivalente; o builder escolhe e documenta.
- `docs/local-setup.md`: a seção "Meta / WhatsApp" vira "WhatsApp (WuzAPI)": subir o container, criar o usuário com o token de admin, configurar webhook e HMAC, conectar e ler o QR code com o chip dedicado. A seção do túnel sai.
- `docs/deploy.md`: instalar Docker, subir a WuzAPI, parear por túnel SSH; sair Caddy/domínio/passo 8 da Meta; firewall só porta 22; "Updating" cobre atualizar a imagem da WuzAPI.
- `docs/why-wuzapi.md` (novo): contexto, as barreiras da Meta (resumo com link para as notas), as três opções da §5, a escolha, os riscos aceitos (banimento, quebra de protocolo, serviço extra) e o que fazer se o número for banido (reparear outro chip; voltar à Meta está no histórico do git).
- `README.md`: diagrama e "Tech stack" trocam Meta por WuzAPI; "Features" troca "webhook signature check" pelo equivalente; nova seção curta "Why not the official WhatsApp API?" apontando para `why-wuzapi.md`, com o aviso de risco.
- `docs/future-improvements.md`: atualizar "Proactive reminders" (sem janela de 24h/templates) e "Observability" (os itens da Graph API deixam de valer; trocar por logar o corpo de erro da WuzAPI e o status da sessão).
- `deploy/zacretario.service`: só o comentário/descrição, se citarem a Meta.
- `PRIVACY.md`: revisar a menção à Meta.

## 9. Riscos aceitos

- **Banimento do número** por uso fora dos Termos do WhatsApp. Mitigação: número dedicado, só dois usuários, só responde a quem escreve, sem envio em massa.
- **Quebra por mudança de protocolo:** a conexão pode cair até a WuzAPI/whatsmeow atualizar. Mitigação: versão fixada e um passo de atualização documentado.
- **Sessão desconectada** (celular do chip sem uso por muito tempo, logout): o bot para de receber. Mitigação: documentar como verificar `GET /session/status` e reparear.

## 10. Deixado para quem implementar

- Confirmar com um payload real os campos de remetente, id, tipo e texto, e o formato exato do cabeçalho HMAC.
- Como o container alcança o app no host em cada ambiente (Windows local e VPS Linux).
- Ordem dos commits e o nível de detalhe dos passos nas docs, seguindo o estilo atual (passo a passo numerado, links para a seção exata).
