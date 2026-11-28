---
name: testar-card
description: Use quando um card do quadro Trello "Zacretário" está em "Para teste" e o Juliano quer testá-lo ("testar o card", "/testar-card", um link trello.com/c/…). Lê o card e o PR do agente, conduz o teste de cada critério de aceite no n8n-teste no modo copiloto, marca a checklist, guia a promoção para a produção e move o card para "Pronto".
---

# Testar card

Fecha o ciclo do Kanban (`docs/kanban.md`): o agente deixou um PR e o card em `Para teste`; aqui o Juliano confere cada critério no **n8n-teste**, faz o merge e promove para a **produção**. Conduza no esqueleto do quack (📍, ✅/❌, 🧠, 👉 ou 🛠️, 🔍), uma etapa por critério, perguntando "Eu faço" ou "Claude faz". Segredos, logins, merge e qualquer ação na produção são sempre do Juliano, ou passam pelo "sim" dele.

## 1. Ler

1. **Card** (MCP `trello`): ache pelo link ou pelo nome no quadro `Zacretário`. Leia a descrição, a checklist "Critérios de aceite" e os comentários. O agente deixa o link do PR e o roteiro de teste num comentário.
2. **PR e branch:** `git fetch origin`, depois `git log --oneline origin/main..origin/<branch>` e `git diff --stat origin/main...origin/<branch>`. A branch é `card/<número>-<slug>`. Leia o diff inteiro antes de testar: é o que vai para a produção.
3. **Avisos.** Pare e conte ao Juliano antes de testar se:
   - **o PR partiu de uma `main` antiga:** `git merge-base --is-ancestor origin/main origin/<branch>` falha. Diga o que mudou na `main` desde então (`git log origin/<branch>..origin/main --oneline`) e se toca os mesmos arquivos. Se tocar, sugira devolver o card para `Em andamento`, para o agente refazer a partir da `main` nova;
   - **o n8n-teste tem outra versão do workflow:** para cada `workflows/*.json` do PR, compare com o workflow de mesmo `id` no MCP `n8n-teste` (nós, parâmetros, conexões). O teste só vale se os dois forem iguais.

## 2. Testar

- **Uma etapa por critério**, na ordem do card. Os que o agente já marcou também são conferidos, mais rápido: ele marca o que **acha** que validou.
- Use o roteiro do comentário do agente, mas confira de verdade (a execução no n8n-teste, a saída do teste, a linha no banco). Diga o que conferiu.
- Dados de teste: sempre a pessoa `teste`, o banco `zacretario_teste` e a agenda "Zacretário teste". SQL no banco de teste é o Juliano quem roda, na VPS (`cd /opt/zacretario/infra && docker compose exec postgres psql -U zacretario_teste -d zacretario_teste`). Você escreve o comando, sem dado real.
- Critério aprovado → marque o item na checklist do card.
- **Critério reprovado:**
  1. Comente no card o que falhou, com o que foi feito e o que apareceu, numa linha cada, sem dado pessoal.
  2. Pergunte se pode devolver o card para `Em andamento`. Com o "sim", mova. A escuta do n8n dispara o agente de novo, e ele retoma a mesma branch e o mesmo PR.
  3. Pare aqui.

## 3. Promover (só com o "ok" do Juliano para todos os critérios)

1. **Merge do PR:** é do Juliano, com "Create a merge commit". Depois, atualize a `main` local.
2. **Workflows:** para cada workflow do PR, siga o passo 7 de [Test n8n (for the Kanban agent)](../../../docs/setup.md#test-n8n-for-the-kanban-agent):
   - exporte do **n8n-teste** (`n8n export:workflow --id=<id>`) e importe na produção com o **mesmo `id`**;
   - promova sempre a partir do n8n-teste, **não** do JSON do repositório. O "Google Agenda (por pessoa)" do repositório não tem o ramo e a credencial de uma pessoa real, que existem nos dois n8n.
   - Workflow novo entra com o `id` que o n8n-teste criou.
3. **Publicar na produção:** só com o "sim" do Juliano, que é quem publica.
4. **Conferir na produção:** o `id` é o mesmo do n8n-teste e o workflow está publicado. Se o workflow mexe no bot, uma mensagem real ao bot recebe resposta. Se tem Schedule, a próxima execução aparece no horário.
5. **Fechar:** com o "ok", mova o card para `Pronto`. A escuta libera a vaga e dispara o próximo card `Na fila`, se houver: avise o Juliano.

## Nunca

- Publicar, importar ou apagar algo na produção sem o "sim" do Juliano.
- Fazer merge.
- Marcar um critério que não foi conferido.
- Pôr dado real (nome, telefone, evento) em comentário do card ou do PR: o repositório é público.
