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
| base | T01 | ✅ | 2 | list_events, list_todos | 9.311 | 0 | 0 | 189 | 0,0205 |

**Primeira leitura (26/11):** cada chamada envia cerca de 4.600 tokens (prompt + 10 ferramentas) e recebe poucas centenas. Quase todo o custo é **entrada repetida**, e é isso que o cache barateia.
