# Modelo do card

O card tem três partes: o **título**, a **descrição** (Markdown, com as cinco seções abaixo, nesta ordem e com estes nomes) e a **checklist** `Critérios de aceite`.

## Título

Curto e no infinitivo, dizendo o que muda para quem usa. Exemplos: `Lembrar compromisso 1 h antes`, `Aceitar áudio no lugar de texto`.

## Descrição

```markdown
## História de usuário
Como <pessoa>, quero <coisa>, para <motivo>.

## Contexto
<Como funciona hoje e o que muda. Duas a cinco linhas.>

## Critérios de aceite
1. <Um comportamento que dá para verificar, com entrada e resultado esperado.>
2. <…>

## Guia de desenvolvimento
**Workflows e arquivos:**
- <workflow `Nome exato` (`workflows/arquivo.json`) ou arquivo `workflows/code/x.js`: o que muda nele>

**Passos:**
1. <em ordem; código de Code node começa pelo teste em `workflows/code/tests/`>
2. <…>

**Armadilhas:**
- <o que já deu errado neste projeto e vale para esta mudança>

**Como testar no n8n-teste:**
- <o que rodar (por exemplo, o workflow `Testes do agente` com a pessoa `teste`) e o que deve aparecer>

## Fora do escopo
- <o que este card não faz, para o agente não ir além>
```

## Checklist `Critérios de aceite`

Um item por critério, no mesmo texto e na mesma ordem da seção **Critérios de aceite**. O agente marca o que conseguiu validar, e o Juliano marca o resto no teste.

## Regras do texto

- **Critério verificável:** "ao mandar `amanhã 9h dentista`, o bot cria o evento às 9h" serve; "funcionar bem" não serve.
- **Só nomes reais:** todo workflow, arquivo, nó ou tabela citado no guia existe no repositório hoje.
- **Nada de dados pessoais nem segredos:** o repositório é público, e o texto do card vai parar no PR e nos logs do Actions. Use a pessoa `teste`, nunca nomes, telefones ou eventos reais, e cite credenciais pelo nome, nunca pelo valor.
