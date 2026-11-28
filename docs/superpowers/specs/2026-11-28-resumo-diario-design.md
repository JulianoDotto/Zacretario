# Resumo do dia: design

**Data:** 28/11/2026 · **Tamanho:** mudança pequena, em dois cards

## Por quê

O Juliano esquece de abrir a agenda e quer saber logo de manhã o que tem para fazer. O resumo precisa chegar sozinho, todo dia, curto o bastante para ser lido de uma vez no WhatsApp.

## O que é

- Uma mensagem no WhatsApp, todo dia, com os compromissos de hoje e **todos os TODOs em aberto**, sem limite por enquanto. Os TODOs não têm data (`todos` em `infra/sql/001_schema.sql`).
- Sai às **07:00** por padrão, no fuso da pessoa (`users.timezone`). O horário fica guardado por pessoa.
- **Dia vazio também gera mensagem** ("agenda livre e nenhum TODO"). Se nada chegar, é sinal de que algo falhou.
- O resumo é gravado em `conversation` (role `assistant`), para o agente entender respostas como "concluí o 3".
- Formato do bot: 📅 para eventos, ✅ para TODOs (com o número), em blocos separados.

```
Bom dia, Teste! Seu dia (sex 28/11):

📅 Agenda
📅 09:00 Dentista

✅ TODOs em aberto
✅ 3. Comprar ração
```

## Abordagens

1. **Escolhida: um workflow agendado a cada 5 min, mais um sub-workflow que monta o texto sem IA.** O agendado escolhe quem deve receber o resumo naquela hora e já grava a data de hoje para essa pessoa (assim ela não recebe duas vezes). O texto sai de um Code node com testes. É barato, sempre igual e dá para testar no n8n-teste pela pessoa `teste`.
2. **Chamar o `Agente Zacretário` com "faça meu resumo".** Reaproveita o que o agente já faz, mas cada resumo vira uma chamada de LLM, o texto muda de um dia para o outro e é mais difícil de testar.
3. **Um gatilho fixo por pessoa.** Não deixa a pessoa escolher o horário sem editar o workflow. Descartada.

## Partes

**Card 1: mandar o resumo do dia às 7h**
- `infra/sql/003_resumo_diario.sql` (criar): `preferences.daily_summary_time time DEFAULT '07:00'` (NULL = desligado) e `preferences.daily_summary_sent_on date`.
- Sub-workflow `Resumo do dia` (criar): recebe `user_key` e devolve `text`. Lê os TODOs em aberto, pega os eventos de hoje pelo `Portão de agenda` (operação `list`) e monta o texto em `workflows/code/resumo-montar.js`. Se a agenda falhar, manda os TODOs mesmo assim, com uma linha avisando que não conseguiu ler a agenda.
- Workflow `Resumo diário` (criar): agendado a cada 5 min. Um `UPDATE … RETURNING` marca e devolve as pessoas que devem receber o resumo naquela hora (já passou do horário no fuso delas e ainda não receberam hoje; pessoas ativas; a pessoa `teste` fica de fora). Para cada uma: `Resumo do dia`, dividir o texto, enviar pela Evolution API e gravar em `conversation`.
- `Testes do agente`: um webhook manual `Resumo de teste` que chama o `Resumo do dia` com a pessoa `teste`.
- O envio pelo WhatsApp só pode ser testado na produção, porque o n8n-teste não alcança a Evolution API.

**Card 2: mudar o horário do resumo pela conversa**
- Ferramentas do agente para ler e mudar `daily_summary_time` ("me manda o resumo às 6h30"), no estilo de `get_preferences`/`update_preferences`, com o texto no `workflows/prompt.md` e no `workflows/tools.md`.

## Decisões minhas (podem ser revistas)

- A data de hoje é gravada **antes** de enviar: se o envio falhar, a pessoa não recebe o resumo de novo naquele dia, e o workflow `Erros` avisa. Isso evita mandar a mesma mensagem duas vezes.
- O resumo sai até 5 minutos depois do horário escolhido.

## Fora do escopo

- TODOs com data, e "do dia" querendo dizer só os de hoje.
- Desligar o resumo pela conversa.
- Limitar o tamanho da lista de TODOs.
