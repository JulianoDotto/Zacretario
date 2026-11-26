# Ferramentas do agente (Postgres Tool)

Cada ferramenta é um nó **Postgres Tool** ligado ao encaixe **Tool** do AI Agent, com a credencial
`Postgres Zacretário` e a operação **Execute Query**. Os textos de descrição vêm de
`src/zacretario/agent/todo_tools.py` e `preference_tools.py` (tag `v1-python`).

Regra de segurança: o `user_key` ($1) vem **sempre do gatilho**, nunca de `$fromAI`. A IA só escolhe
o conteúdo (texto, número do TODO, horários); ela não tem como mexer nos dados de outra pessoa.

Em **Options → Query Parameters**, use a expressão de lista indicada (um valor por `$n`, na ordem).
`$('When Executed by Another Workflow').first().json.user_key` aparece abreviado abaixo como `USER`.

---

## add_todo
Descrição: `Cria um TODO (tarefa sem horário) para o usuário.`

```sql
INSERT INTO todos (user_key, text) VALUES ($1, $2) RETURNING id, text
```
```
{{ [ $('When Executed by Another Workflow').first().json.user_key, $fromAI('text', 'Texto do TODO.', 'string') ] }}
```

## list_todos
Descrição: `Lista os TODOs em aberto do usuário, com o número (id) de cada um.`

```sql
SELECT id, text FROM todos WHERE user_key = $1 AND NOT done ORDER BY id
```
```
{{ [ $('When Executed by Another Workflow').first().json.user_key ] }}
```

## complete_todo
Descrição: `Marca um TODO como concluído. Use o id devolvido por list_todos. Sem linhas no resultado = TODO não encontrado.`

```sql
UPDATE todos SET done = true, done_at = now() WHERE user_key = $1 AND id = $2 AND NOT done RETURNING id, text
```
```
{{ [ $('When Executed by Another Workflow').first().json.user_key, $fromAI('todo_id', 'Número do TODO.', 'number') ] }}
```

## delete_todo
Descrição: `Apaga um TODO. Use o id devolvido por list_todos. Sem linhas no resultado = TODO não encontrado.`

```sql
DELETE FROM todos WHERE user_key = $1 AND id = $2 RETURNING id, text
```
```
{{ [ $('When Executed by Another Workflow').first().json.user_key, $fromAI('todo_id', 'Número do TODO.', 'number') ] }}
```

## get_preferences
Descrição: `Mostra a janela de horário e os dias bloqueados (0=segunda ... 6=domingo) para encaixar eventos.`

```sql
SELECT to_char(day_start, 'HH24:MI') AS day_start, to_char(day_end, 'HH24:MI') AS day_end, blocked_weekdays
FROM preferences WHERE user_key = $1
```
```
{{ [ $('When Executed by Another Workflow').first().json.user_key ] }}
```

## update_preferences
Descrição: `Altera a janela de horário e/ou os dias bloqueados. Deixe vazio o campo que não deve mudar.`

```sql
UPDATE preferences SET
  day_start        = COALESCE(NULLIF($2, '')::time,  day_start),
  day_end          = COALESCE(NULLIF($3, '')::time,  day_end),
  blocked_weekdays = COALESCE(NULLIF($4, '')::int[], blocked_weekdays)
WHERE user_key = $1
RETURNING to_char(day_start, 'HH24:MI') AS day_start, to_char(day_end, 'HH24:MI') AS day_end, blocked_weekdays
```
```
{{ [ $('When Executed by Another Workflow').first().json.user_key, $fromAI('day_start', 'Início do dia no formato HH:MM; vazio para não mudar.', 'string'), $fromAI('day_end', 'Fim do dia no formato HH:MM; vazio para não mudar.', 'string'), $fromAI('blocked_weekdays', 'Dias bloqueados no formato {5,6} (0=segunda ... 6=domingo); {} libera todos; vazio para não mudar.', 'string') ] }}
```
