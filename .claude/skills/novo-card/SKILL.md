---
name: novo-card
description: Use no fim de um brainstorming aprovado sobre uma melhoria do Zacretário, para transformar o design num card do Backlog no quadro Trello "Zacretário" (história de usuário, critérios de aceite, guia de desenvolvimento e checklist). Também quando o Juliano disser "novo card", "cria o card" ou "manda pro Backlog".
---

# Novo card

Transforma o design aprovado numa conversa num card do `Backlog`. Quem vai ler o card é o agente do Kanban, que roda no GitHub Actions sem esta conversa (veja `docs/kanban.md`). Então o card precisa se explicar sozinho: o que não estiver escrito nele, o agente não sabe.

## Antes de montar

1. **O design está aprovado?** Se a conversa não tiver um design que o Juliano aprovou, pare e sugira fechar o brainstorming primeiro (`superpowers:brainstorming`).
2. **Um card é uma mudança testável.** Se o design tiver partes que dá para testar separadas, proponha um card para cada uma, em ordem, e crie um de cada vez.
3. **Confira os nomes reais** que o guia vai citar, antes de escrevê-los:
   - workflows: o `name` e o `id` dos JSONs em `workflows/*.json` (os IDs são os mesmos na produção e no n8n-teste);
   - Code nodes: `workflows/code/*.js`, com os testes em `workflows/code/tests/` (`node --test workflows/code/tests/`);
   - prompts e ferramentas do agente: `workflows/prompt.md`, `workflows/prompt-extracao.md`, `workflows/tools.md`;
   - tabelas: `infra/sql/*.sql`.

   Se uma peça ainda não existe (um workflow novo, por exemplo), escreva "criar" e o nome proposto, nunca como se já existisse.

## Montar

Siga o [modelo-card.md](modelo-card.md) à risca: título no infinitivo, as cinco seções da descrição nesta ordem (**História de usuário**, **Contexto**, **Critérios de aceite**, **Guia de desenvolvimento**, **Fora do escopo**) e uma checklist `Critérios de aceite` com um item por critério.

No guia, use as armadilhas que já aconteceram neste projeto quando valerem para a mudança:
- sub-workflows rodam a versão **publicada**: depois de mudar um, publique no n8n-teste antes de testar quem o chama;
- endereço fixo num nó amarra o workflow a uma instância: a URL fica na credencial (Base URL), nunca no nó;
- o mesmo `id` de workflow nos dois n8n é o que deixa a promoção ser um import por cima: não recrie um workflow que já existe, edite;
- o webhook do WhatsApp fica fechado no n8n-teste: teste pelo `Testes do agente` com a pessoa `teste`, e na agenda de teste.

## Mostrar e pedir o "sim"

Mostre no chat o card inteiro, exatamente como vai para o Trello: o título, a descrição e os itens da checklist. Pergunte se pode criar. Só crie com um "sim" claro. Se ele pedir mudanças, ajuste e mostre de novo.

## Criar (MCP `trello`)

1. `list_boards` → o quadro `Zacretário`. `get_lists` → a lista com o nome exato `Backlog`. Procure pelo nome a cada vez, sem decorar IDs.
2. `create_card` na `Backlog`, com `pos: "bottom"`, o título e a descrição. Sem etiquetas: `Bloqueado` e `Na fila` são do agente e da regra de fila.
3. `trello_create_checklist` com o nome `Critérios de aceite`, e um `trello_create_check_item` por critério, na ordem.
4. **Confira:** com `get_card`, veja se a descrição tem as cinco seções e se a checklist tem o mesmo número de itens que os critérios. Se faltar algo, corrija antes de seguir.
5. Devolva o link do card (`url`).

**Não mova o card.** Quem leva o card para `Em andamento` (e com isso dispara o agente) é sempre o Juliano.
