# Testes do agente

Conjunto fixo de mensagens para avaliar o **Agente Zacretário** ao mudar modelo, esforço, cache ou ferramentas. Ver o [design](../../docs/superpowers/specs/2026-11-26-custo-ia-design.md).

## Como rodar

- Tudo roda como a pessoa **`teste`**: sem WhatsApp, com agenda Google própria ("Zacretário teste") e dados separados no banco. O workflow **Testes do agente** fixa `user_key = 'teste'`, então nenhum teste roda como outra pessoa.
- **Rodar uma mensagem:** execute **Testes do agente** em modo manual, pelo gatilho **Mensagem de teste**, com o corpo `{"text": "..."}`. Isso pode ser feito pelo editor (com o webhook de teste escutando) ou pelo MCP do n8n (`execute_workflow`, `executionMode: manual`). O workflow fica **sem publicar**, para a URL de produção não ficar aberta na internet.
- **Ler o resultado:** a execução do **Testes do agente** traz a resposta (`output`). O nó *Chamar Agente como teste* aponta para a sub-execução do Agente, e é lá que os dados do nó *Anthropic Chat Model* mostram, por chamada, `promptTokens`, `completionTokens` e as ferramentas usadas.
- **Os testes rodam a versão publicada do Agente** (sub-workflows sempre rodam a versão publicada). Por isso, mudanças em teste (Fase 2, Haiku) vão para uma **cópia** do Agente, sem atingir a Bruna nem o Juliano.

### Reset (antes de cada rodada)

1. Executar **Testes do agente** pelo gatilho **Resetar teste**. Ele apaga o histórico e os TODOs e volta as preferências ao padrão (08:00–22:00, sem dias bloqueados), sempre só para `teste`. A resposta deve ser `conversa: 0, todos: 0`.
2. Apagar os eventos da agenda "Zacretário teste" nos próximos 14 dias, pelo conector do Google Agenda (`list_events` + `delete_event` nessa agenda) ou à mão no Google Agenda.

## Testes

Rodar em ordem: alguns dependem dos anteriores (T10 cancela o evento do T02). ⚠️ = anti-objetivo: se falhar, a configuração está reprovada.

| # | Mensagem | Esperado |
|---|---|---|
| T01 | `o que eu tenho pra fazer?` | Agenda dos próximos 7 dias **e** TODOs, em blocos separados. Os dois vazios, cada um dito em uma linha. |
| T02 | `dentista sexta às 15h` | Evento *Dentista* na **próxima sexta** (hoje, se hoje for sexta e ainda não passou das 15h), das 15:00 às 16:00. Confirma em 1 ou 2 linhas com 📅. |
| T03 | `ligar pro João às 8h` | Evento às 08:00, hoje se ainda não passou, senão amanhã, com 1 hora de duração. |
| T04 | `pagar IPVA dia 30` | Evento de **dia inteiro** no próximo dia 30. |
| T05 ⚠️ | `academia quinta às 23h` | Na **próxima quinta**. Se hoje for quinta e ainda não passou das 23h, **hoje**. Data errada reprova. |
| T06 | `comprar ração do gato` | **TODO**, não evento. Confirma com ✅. |
| T07 | `tenho algo amanhã?` | Lista só os eventos de amanhã (ou diz que não há). |
| T08 | `acha um horário pra correr essa semana, de manhã` | Usa os horários livres e **só propõe**, sem criar nenhum evento. |
| T09 | `não marca nada no domingo` | Atualiza as preferências (domingo bloqueado) e confirma. |
| T10 ⚠️ | `cancela o dentista` | **Pergunta antes**, mostrando o evento (por exemplo "Cancelo *Dentista* de sex … 15:00? (sim/não)"), e **não apaga**. |
| T11 ⚠️ | `sim` | Agora apaga o *Dentista* e confirma. |
| T12 ⚠️ | `apaga o TODO da ração` → depois `não` | Primeiro pergunta. No `não`, diz que não fez nada e o TODO continua lá. |
| T13 | `já comprei a ração` | Marca o TODO como concluído, **sem** pedir confirmação. |
| T14 | `me escreve um poema sobre o mar` | Recusa com gentileza em uma frase e lembra o que sabe fazer. |
| T15 | `marca reunião com o Pedro` | Pergunta **quando**, sem criar nada. |

Em todos os testes: português do Brasil, sem ids nem nomes de ferramentas, *negrito* com um asterisco, datas como `sex 27/11 15:00`.

## Preços (US$ por milhão de tokens)

| Modelo | Entrada | Saída | Cache lido | Cache gravado (5 min) |
|---|---|---|---|---|
| Sonnet 5.5 | 2,00 | 10,00 | 0,10 | 2,50 |
| Haiku 5.5 | 0,10 | 0,50 | conferir | conferir |

Custo de uma mensagem = soma, em todas as chamadas do laço, de entrada × preço + saída × preço (+ cache, quando houver).

## Resultados

Os tokens são somados por mensagem (todas as chamadas ao modelo). "passou?" é marcado pelo Juliano.

| Rodada | Teste | Passou? | Chamadas | Ferramentas | Entrada | Cache lido | Cache gravado | Saída | US$ |
|---|---|---|---|---|---|---|---|---|---|
| isolamento | "marca teste de isolamento amanhã às 10h" | ✅ (só na agenda de teste) | 2 | create_event | 9.376 | 0 | 0 | 170 | 0,0205 |
| base | T01 | ✅ | 2 | list_events, list_todos | 9.311 | 0 | 0 | 196 | 0,0206 |
| base | T02 | ✅ | 2 | create_event | 9.601 | 0 | 0 | 196 | 0,0212 |
| base | T03 | ✅ | 2 | create_event | 9.743 | 0 | 0 | 234 | 0,0218 |
| base | T04 | ✅ | 2 | create_event | 9.897 | 0 | 0 | 225 | 0,0220 |
| base | T05 ⚠️ | ✅ | 2 | create_event | 10.088 | 0 | 0 | 302 | 0,0232 |
| base | T06 | ✅ | 2 | add_todo | 9.984 | 0 | 0 | 78 | 0,0207 |
| base | T07 | ✅ | 2 | list_events | 10.182 | 0 | 0 | 148 | 0,0218 |
| base | T08 | ✅ | 2 | get_preferences, find_free_slots | 10.716 | 0 | 0 | 485 | 0,0263 |
| base | T09 | ✅ | 3 | get_preferences, update_preferences | 16.109 | 0 | 0 | 315 | 0,0354 |
| base | T10 ⚠️ | ✅ | 2 | list_events | 10.974 | 0 | 0 | 140 | 0,0233 |
| base | T11 ⚠️ | ✅ | 3 | list_events, delete_event | 16.719 | 0 | 0 | 223 | 0,0357 |
| base | T12a ⚠️ | ✅ | 2 | list_todos | 10.713 | 0 | 0 | 58 | 0,0220 |
| base | T12b ⚠️ | ✅ | 1 | — | 5.315 | 0 | 0 | 42 | 0,0111 |
| base | T13 | ✅ | 3 | list_todos, complete_todo | 16.090 | 0 | 0 | 110 | 0,0333 |
| base | T14 | ✅ | 1 | — | 5.293 | 0 | 0 | 80 | 0,0114 |
| base | T15 | ✅ | 1 | — | 5.328 | 0 | 0 | 62 | 0,0113 |
| **base** | **total (16 mensagens)** | **15/15** | **32** | | **166.063** | 0 | 0 | **2.894** | **0,3611** |
| sonnet-low | T01 | ✅ | 2 | list_events, list_todos | 9.311 | 0 | 0 | 208 | — |
| sonnet-low | T02 | ✅ | 2 | create_event | 9.592 | 0 | 0 | 162 | — |
| sonnet-low | T03 | ✅ | 2 | create_event | 9.749 | 0 | 0 | 205 | — |
| sonnet-low | T04 | ✅ | 2 | create_event | 9.832 | 0 | 0 | 162 | — |
| sonnet-low | T05 ⚠️ | ✅ | 2 | create_event | 9.978 | 0 | 0 | 195 | — |
| sonnet-low | T06 | ✅ | 2 | add_todo | 9.958 | 0 | 0 | 92 | — |
| sonnet-low | T07 | ✅ | 2 | list_events | 10.179 | 0 | 0 | 146 | — |
| sonnet-low | T08 | ✅ | 2 | find_free_slots | 10.544 | 0 | 0 | 403 | — |
| sonnet-low | T09 | ✅ | 2 | update_preferences | 10.568 | 0 | 0 | 223 | — |
| sonnet-low | T10 ⚠️ | ✅ | 2 | list_events | 10.984 | 0 | 0 | 117 | — |
| sonnet-low | T11 ⚠️ | ✅ | 3 | list_events, delete_event | 16.738 | 0 | 0 | 201 | — |
| sonnet-low | T12a ⚠️ | ✅ | 2 | list_todos | 10.711 | 0 | 0 | 54 | — |
| sonnet-low | T12b ⚠️ | ✅ | 1 | — | 5.310 | 0 | 0 | 40 | — |
| sonnet-low | T13 | ✅ | 3 | list_todos, complete_todo | 16.114 | 0 | 0 | 110 | — |
| sonnet-low | T14 | ✅ | 1 | — | 5.303 | 0 | 0 | 105 | — |
| sonnet-low | T15 | ✅ | 1 | — | 5.371 | 0 | 0 | 60 | — |
| **sonnet-low** | **total (16 mensagens)** | **15/15** | **31** | | **160.242** (total, com cache) | 0 | 0 | **2.483** | **0,3453** |

**Primeira leitura (26/11):** cada chamada envia cerca de 4.600 tokens (prompt + 10 ferramentas) e recebe poucas centenas. Quase todo o custo é **entrada repetida**, e é isso que o cache barateia.

**Linha de base (26/11, Sonnet 5.5, opções padrão):** todos os 15 testes passaram, inclusive os ⚠️. A média ficou em **US$ 0,0226 por mensagem**, com 2 chamadas por mensagem. **92% do custo é entrada**, quase toda o mesmo prompt + ferramentas repetidos a cada chamada.

Observações:
- T03: "às 8h" já tinha passado, então foi para amanhã, e o bot explicou o porquê.
- T09: atualizou a preferência e refez a lista de horários tirando o domingo, sem chamar `find_free_slots` de novo. Ficou certo, mas ele filtrou de cabeça.
- Mensagens sem ferramenta (T12b, T14, T15) custam a metade: uma chamada só.

**Fase 1 — Sonnet 5.5 + cache 5 min + effort low (26/11):** 15/15 de novo, inclusive os ⚠️. Saída caiu 14% (2.483 contra 2.894 tokens), e o T09 usou 2 chamadas em vez de 3. A requisição sai com `cache_control: {type: ephemeral, ttl: 5m}`, `thinking: adaptive` e `effort: low` (conferido nos dados da execução).

**Limitação da medição:** o n8n soma os tokens de cache no `promptTokens`, então a coluna "Entrada" é o total e não mostra o que veio do cache. Estimativa, supondo que o prefixo de ~4.500 tokens (ferramentas + prompt de sistema) seja lido do cache em 30 das 31 chamadas: ~135 mil lidos a US$ 0,10/M, ~21 mil gravados a US$ 2,50/M, saída a US$ 10/M, **≈ US$ 0,09 na rodada, ≈ US$ 0,006 por mensagem (−75%)**. **Precisa ser confirmado no console da Anthropic** (Usage, tokens "cache read" de 26/11).

**Conferido no console da Anthropic (26/11):** gravação e leitura de cache do dia = **US$ 0**. O cache **não pegou**: a rodada custou o mesmo que sem cache (≈ US$ 0,32 de entrada + US$ 0,025 de saída ≈ **US$ 0,345**, −4% contra a base, só pelo effort low). A requisição registrada pelo n8n mostra `cache_control` no topo, mas nada foi gravado. Hipótese: a versão do n8n/LangChain não repassa esse campo para a API. A estimativa de −75% acima **não vale**.
