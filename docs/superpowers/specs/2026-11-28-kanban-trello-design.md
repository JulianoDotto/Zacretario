# Kanban no Trello com agente do Claude — Design

Data: 2026-11-28
Status: rascunho para aprovação
Tamanho: projeto (ambiente de teste do n8n, escuta do Trello no n8n, agente no GitHub Actions, criação e teste de cards no Claude Code)

## 1. Intenção e porquê

Hoje uma melhoria do Zacretário nasce numa conversa com o Claude (brainstorming → spec → plano) e é executada na mesma sessão, no modo copiloto. A ideia é separar as três fases num quadro Kanban do Trello:

1. **Criar** o card conversando com o Claude, como hoje.
2. **Desenvolver** sem ninguém olhando: mover o card dispara um agente na nuvem que implementa e entrega.
3. **Testar** quando o Juliano quiser, no modo copiloto, e só então promover para o que está no ar.

Por que (leitura do Claude a partir do projeto, não dita pelo Juliano nesta conversa): o projeto existe para aprender n8n, para portfólio ("uso IA para construir software e soluções") e, no futuro, para virar um modelo de atendimento a clientes freelance. Um fluxo Kanban → agente → PR → teste mostra exatamente isso, com cada peça visível (workflow do n8n, YAML do GitHub, logs, PRs).

## 2. O quadro

Um quadro do Trello só para o Zacretário, com quatro listas, nesta ordem:

| Lista | Quem coloca o card ali | O que acontece |
|---|---|---|
| **Backlog** | o Claude, no fim de um brainstorming no Claude Code | o card fica esperando |
| **Em andamento** | o Juliano, arrastando | o agente é disparado, pega o card e implementa |
| **Para teste** | o agente, ao terminar | o card espera o teste, sem prazo e sem depender do agente |
| **Pronto** | o Juliano (ou o Claude, depois do "ok" dele na sessão de teste) | fim |

## 3. Objetivos, não objetivos, anti-objetivos

**Objetivos**
- Criar um card a partir de uma conversa no Claude Code, com **história de usuário**, **critérios de aceite** e **guia de desenvolvimento**.
- Mover o card para "Em andamento" dispara o agente sem o PC do Juliano ligado.
- O agente entrega **uma branch com PR** e um comentário no card (link do PR, resumo, como testar), e move o card para "Para teste".
- O agente trabalha no n8n de **teste**, nunca no de produção.
- Testar um card numa sessão nova do Claude Code, no modo copiloto, a partir só do card e do PR.

**Não objetivos**
- Quadro para outros projetos (é só o Zacretário).
- O agente fazer merge, publicar em produção ou mexer no n8n de produção.
- WhatsApp no ambiente de teste.
- Ambientes pagos do n8n (Business/Enterprise).

**Anti-objetivos** (fracasso, mesmo que funcione)
- Um erro do agente derrubar o assistente que o Juliano e a Bruna usam.
- Segredo aparecer em log público, em commit ou no chat.
- O fluxo virar caixa-preta: o Juliano não entender o que cada peça faz (aprender é a prioridade).
- Alguém de fora conseguir disparar o agente ou dar ordens a ele.

## 4. Abordagens consideradas

**Onde o agente roda**

| | Como dispara | Ponto fraco | Portfólio |
|---|---|---|---|
| PC do Juliano | script agendado no Windows consulta o Trello e roda `claude -p` | PC ligado; atraso da consulta | fraco |
| Claude Code na nuvem (rotinas) | n8n chama a URL de disparo da rotina | recurso novo; configuração fora do repo | médio |
| **GitHub Actions** ✅ | n8n chama `repository_dispatch` do GitHub | mais peças para montar | forte: YAML versionado, logs, PRs |

Escolhido pelo Juliano: **GitHub Actions**, com o n8n escutando o Trello.

**O que o agente pode fazer no n8n**

| | Risco para produção | O agente valida o que fez? |
|---|---|---|
| Só no repositório (JSON exportado) | nenhum | não |
| Cópia `[card-N]` no n8n de produção | médio: mesmas credenciais reais | sim |
| Acesso total ao n8n de produção | alto | sim |
| **Segunda instância de n8n (teste)** ✅ | nenhum: credenciais e banco próprios | sim |

O n8n gratuito não tem ambientes. Escolhido pelo Juliano: **segunda instância na mesma VPS**. A VPS (KVM 1: 1 vCPU, 4 GB de RAM, 50 GB de disco) usa hoje ~1,5 GB de RAM, ~2% de CPU e ~6 GB de disco (métricas da Hostinger, 27 e 28/11/2026), então cabe.

**Conexão do Claude com o Trello:** por **servidor MCP**, decisão do Juliano. Vale para o Claude Code local (criar e testar cards) e para o agente (ler, comentar e mover o card).

## 5. Decisões

### 5.1 Ambiente de teste (n8n-teste)
- Novo serviço `n8n-teste` no [infra/docker-compose.yml](../../../infra/docker-compose.yml), com a mesma imagem fixada do `n8n` (`n8nio/n8n:2.49.6`), **chave de criptografia própria** e **bancos próprios** no mesmo Postgres: `n8n_teste` (dados do n8n) e `zacretario_teste` (dados do app, criados com `infra/sql/*.sql` e o seed de exemplo).
- Subdomínio `teste.dotton8n.com.br` no Caddy, com DNS na Hostinger. Login do n8n com uma conta só do teste.
- **Sem Evolution / WhatsApp.** Os workflows rodam por disparo manual e pelo `testes-do-agente.json` que já existe, com mensagens simuladas (`workflows/fixtures/`).
- Credenciais do teste: uma agenda Google **de teste** (não a do Juliano nem a da Bruna), uma chave da Anthropic (pode ser a mesma conta, com limite) e o banco `zacretario_teste`. Nada de credencial de produção no teste.
- O **MCP do n8n-teste** fica ligado, com token próprio. Os workflows que o agente usar são marcados como "Available in MCP".
- Os workflows de produção são copiados uma vez para o teste como ponto de partida, **mantendo os mesmos IDs de workflow** (os nós `Execute Workflow` apontam por ID, por exemplo `EjM0rSdJ3ZA0IrEJ` = "Portão de agenda") e criando as credenciais de teste **com o mesmo ID e o mesmo nome** das de produção, só que com valores de teste. Assim, o JSON que o agente exporta do teste importa na produção sem ajuste, e `workflows/` segue como fonte da verdade. Na promoção, o JSON do PR é importado na produção por cima do workflow de mesmo ID. *(Decisão do Claude: o construtor confirma que a importação do n8n 2.49.6, pela CLI `n8n import:*`, preserva esses IDs.)*

### 5.2 Escuta do Trello (n8n de produção)
- Workflow novo **"Kanban: card movido"**, numa pasta "Kanban" do n8n de **produção**. Produção é a instância que fica sempre de pé, e o agente não tem acesso a ela, então ele não consegue quebrar a própria escuta. *(Decisão do Claude.)*
- **Trello Trigger** (webhook do Trello) no quadro → filtro: o card **mudou de lista** e a lista nova é "Em andamento" → confere a vaga (regra "um card por vez" da 5.3) → **HTTP Request** para `POST /repos/JulianoDotto/Zacretario/dispatches` com `event_type: card-em-andamento` e `client_payload: { card_id }`. A mesma escuta trata a liberação da vaga e dispara o próximo card "Na fila".
- A credencial do GitHub no n8n é um **token fine-grained** limitado a este repositório, com a permissão mínima que o `repository_dispatch` exige.

### 5.3 Agente (GitHub Actions)
- Arquivo `.github/workflows/kanban-agente.yml`, disparado **só** por `repository_dispatch` do tipo `card-em-andamento`. Nenhum gatilho por issue, comentário ou PR (o repositório pode ser público, e qualquer pessoa comenta).
- Roda o Claude Code com a action oficial `anthropics/claude-code-action`, autenticado com **token da assinatura** (`claude setup-token` → segredo `CLAUDE_CODE_OAUTH_TOKEN`).
- MCPs do agente: **Trello** e **n8n-teste**. Segredos no GitHub: `CLAUDE_CODE_OAUTH_TOKEN`, credenciais do Trello e token do MCP do n8n-teste.
- **Um card por vez, do início até o teste** (decisão do Juliano). Existe um só n8n-teste, então só um card pode ocupá-lo. Um card **ocupa a vaga** enquanto está em "Em andamento" (rodando ou "Bloqueado") ou em "Para teste".
  - O controle fica na escuta do n8n (5.2). Se um card entra em "Em andamento" com a vaga ocupada, o n8n não dispara o agente: põe a etiqueta **"Na fila"** e comenta o motivo.
  - Quando um card vai para "Pronto", ou sai de "Em andamento"/"Para teste" de volta para o Backlog, o n8n dispara o card "Na fila" mais antigo e tira a etiqueta dele.
  - O `concurrency` do GitHub Actions fica como segunda trava, caso cheguem dois disparos juntos.
- Passos do agente:
  1. Lê o card pelo `card_id` e comenta "Comecei" com o link da execução.
  2. Cria a branch `card/<número>-<slug>` a partir da **`main`** e abre o PR para a `main`.
  3. Implementa seguindo o guia do card: código em `workflows/code/` com testes (`workflows/code/tests/`), workflows no **n8n-teste** pelo MCP, depois exporta o JSON para `workflows/`.
  4. Roda os testes que existem e valida o workflow no n8n-teste.
  5. Abre o PR (sem merge), com resumo, o que testou e como testar.
  6. Comenta no card o link do PR, o resumo e o roteiro de teste, e move o card para **"Para teste"**.
- **Se travar ou falhar:** comenta no card o que bloqueou, põe a etiqueta **"Bloqueado"** e deixa o card em "Em andamento". Ele nunca move para "Para teste" algo que não passou nos próprios testes.
- **Limites:** tempo máximo de execução e número máximo de turnos do agente, para não gastar a assinatura num loop.
- **Card bloqueado de novo em "Em andamento":** tirar o card de "Em andamento" e devolver dispara uma nova execução, que **retoma a branch e o PR do card**, se existirem, e tira a etiqueta "Bloqueado". O filtro do n8n aceita qualquer entrada em "Em andamento". *(Decisão do Claude.)*
- **Logs públicos:** o repositório `JulianoDotto/Zacretario` é **público** (conferido em 28/11/2026). Os logs do Actions e o texto dos PRs ficam visíveis para qualquer pessoa. O agente roda sem saída detalhada nem modo debug, nunca imprime segredos nem dados pessoais (agendas, telefones), e os PRs trazem só o que o card já diz. O seed de teste não tem dados reais. Em repositório público, os minutos dos runners padrão do Actions não têm custo.

### 5.4 Criar e testar cards (Claude Code local)
- MCP do Trello configurado no Claude Code do Juliano.
- Duas **skills do projeto** em `.claude/skills/` *(decisão do Claude: deixa o formato do card e o roteiro de teste versionados e iguais toda vez)*:
  - **`novo-card`:** fecha um brainstorming criando o card no Backlog, no formato da 5.5.
  - **`testar-card`:** numa sessão nova, lê o card e o PR, monta o roteiro e conduz o teste no modo copiloto (n8n-teste primeiro). Com o "ok" do Juliano, guia a **promoção**: o Juliano faz o merge do PR e importa ou publica o workflow em produção. Depois move o card para "Pronto".
- A promoção para produção é sempre do Juliano. O Claude guia, mas não publica.

### 5.5 Formato do card
- **Título:** curto, no infinitivo ("Lembrar compromisso 1 h antes").
- **Descrição:**
  - **História de usuário:** "Como <pessoa>, quero <coisa>, para <motivo>."
  - **Contexto:** como funciona hoje e o que muda.
  - **Critérios de aceite:** lista verificável, que vira o roteiro de teste.
  - **Guia de desenvolvimento:** workflows e arquivos a mexer, passos em ordem, armadilhas conhecidas, como testar no n8n-teste.
  - **Fora do escopo.**
- **Checklist** no card com os critérios de aceite. O agente marca o que conseguiu validar, e o Juliano marca o resto no teste.

## 6. Como vamos construir

No **modo copiloto**, como o resto do projeto. O Juliano executa as etapas com o Claude guiando, e o Claude executa as repetições quando o Juliano escolher. Segredos, logins e consentimentos (tokens do Trello, do GitHub e da Anthropic; OAuth; senhas) são sempre digitados pelo Juliano, no destino.

**Pré-requisito (decisão do Juliano):** fechar a `feat/n8n` com PR e merge na `main`. Hoje a `main` ainda tem o app antigo em Python, e todo o n8n só existe na `feat/n8n`. Depois do merge, a `main` é a base dos cards e o destino dos PRs do agente, e a promoção de um card começa pelo merge do PR dele.

Ordem natural (o plano detalha): merge da `feat/n8n` → n8n-teste → MCP do Trello e quadro → skill `novo-card` → escuta no n8n → agente no Actions → skill `testar-card` → um card de verdade ponta a ponta.

## 7. Riscos aceitos
- **Google do teste é a conta do Juliano** (decisão dele, 28/11/2026). A credencial "Google Calendar - Juliano" do n8n-teste autoriza a conta pessoal, e a pessoa `teste` só usa a agenda "Zacretário teste". Como o agente tem acesso total ao n8n-teste, ele **poderia** montar um workflow que lê as agendas reais. A alternativa recusada era uma conta Google só de teste, com apenas a agenda de teste compartilhada. O prompt do agente (5.3) proíbe ler agendas que não sejam a de teste.
- O agente consome a cota da assinatura do Claude. Os limites da 5.3 seguram o pior caso.
- O n8n-teste pode ficar diferente da produção com o tempo. A skill `testar-card` avisa quando o workflow do PR partiu de uma versão antiga.
- A qualidade do que o agente entrega depende do card. Um card ruim gera PR ruim, e o teste pega.
- Prompt injection pelo texto do card: só o Juliano escreve no quadro, que é privado.

## 8. Deixado para quem construir
- Qual servidor MCP do Trello usar: um mantido, que leia e escreva cards, comentários, listas e etiquetas. O mesmo servidor no Claude Code local e no Actions.
- Versão exata da `claude-code-action` e o prompt do agente (a partir da 5.3 e da 5.5).
- Valores de tempo máximo e de turnos, o formato do slug e os textos dos comentários.
- Como copiar os workflows para o n8n-teste e trocar as credenciais.
- Como o agente localiza a lista "Para teste" (por nome ou por ID guardado em variável do repositório).
