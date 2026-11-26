# Custo da IA do Zacretário — Design

Data: 2026-11-26
Status: rascunho para aprovação
Tamanho: mudança pequena (configuração no n8n + um conjunto de testes)

## 1. Intenção e porquê

Diminuir o que o agente do Zacretário gasta de créditos na Anthropic, sem piorar o trabalho dele.

**Por quê (nas palavras do usuário):**
1. **Custo por cliente** quando o Zacretário virar produto.
2. **Não estourar o limite logo de cara**, enquanto o uso é só dele e da Bruna.
3. **Ferramentas novas vão chegar**, e cada uma aumenta o texto enviado em toda chamada. O custo tem que aguentar esse crescimento.
4. **Continuar funcionando** se os créditos acabarem ou a Anthropic falhar.

## 2. Como é hoje

- O único uso da IA é o nó *Anthropic Chat Model* do workflow "Agente Zacretário", com **Claude Sonnet 5.5** (US$ 2 por milhão de tokens de entrada, US$ 10 por milhão de saída).
- As opções do nó estão vazias. Por isso valem os padrões do modelo: **raciocínio adaptativo ligado, esforço *high*** (o raciocínio é cobrado como saída) e **sem cache**.
- Cada mensagem do WhatsApp gera de 1 a 4 chamadas ao modelo, uma por volta do laço do agente. Toda chamada reenvia o prompt de sistema, as 10 ferramentas e até 20 mensagens do histórico.

## 3. Objetivos, não objetivos, anti-objetivos

**Objetivos**
- Baixar o custo por mensagem e **medir** a diferença, de antes e depois.
- Ter um **conjunto de testes** reaproveitável, para escolher modelo e esforço com base em dado e para testar ferramentas novas.
- **Fallback grátis no Groq**, para quando o Claude der erro.

**Não objetivos**
- Mudar o que o bot faz ou o prompt, a não ser o mínimo que um teste mostrar necessário.
- Montar um sistema de testes automatizado com nota calculada. A avaliação é humana, lendo lado a lado.

**Anti-objetivos** (fracasso, mesmo que fique mais barato)
- O bot apagar, cancelar ou alterar algo **sem pedir confirmação**.
- Errar datas ("sexta", "amanhã às 16h").
- Os testes mexerem na agenda real ou nos TODOs reais do Juliano ou da Bruna.
- Mandar conversas para um provedor que treina modelos com elas, o que contradiz o `PRIVACY.md`.

## 4. Caminhos considerados

| Caminho | Troca | Decisão |
|---|---|---|
| 1. Ajuste fino no Sonnet (cache + esforço menor) | Risco baixo, corte médio | Fase 1 |
| 2. Trocar direto para o Haiku 5.5 | Cerca de 20× mais barato, mas o risco só aparece no uso | Descartado sozinho |
| **3. Caminho 1, depois Haiku só se passar nos testes** | Corte seguro agora e o grande só se for comprovado | **Escolhido pelo usuário** |

Para o fallback, foram considerados o Groq grátis, o Gemini grátis (treina com os dados, contradiz o `PRIVACY.md`) e os modelos grátis do OpenRouter (instáveis, provedor desconhecido). **O usuário escolheu o Groq grátis.**

## 5. O design

### 5.1 Ambiente de teste isolado (decisão do Claude)
- Uma pessoa de teste na tabela `users` (`key = 'teste'`, com um `whatsapp_id` falso que nunca recebe mensagem), apontando para uma **agenda Google separada**, "Zacretário teste", criada na conta do Juliano (`calendar_id` próprio).
- No workflow "Google Agenda (por pessoa)", `teste` usa a mesma credencial do Juliano. Como o `calendar_id` é outro, nada toca a agenda principal.
- Os TODOs, as preferências e o histórico ficam separados pelo próprio `user_key`.

### 5.2 Conjunto de testes
- Um arquivo `workflows/fixtures/testes-agente.md` com cerca de 15 mensagens que cobrem: criar evento (com dia, com hora, dia inteiro), TODO, consulta sem período, consulta com período, encaixe, preferência, cancelar (tem que **pedir confirmação**), confirmar com "sim", pedido fora do escopo, pedido ambíguo, data relativa no limite ("quinta", quando hoje é quinta). Cada teste traz **o que se espera**.
- Os testes rodam o workflow "Agente Zacretário" direto, com `user_key = 'teste'`, pelo MCP do n8n ou pelo editor.
- Para cada rodada ficam registrados a resposta, as ferramentas chamadas e os **tokens** (as execuções do n8n mostram o uso de tokens). A planilha ou tabela de resultados fica junto do arquivo de testes.
- Os resultados são vistos lado a lado, e quem decide se passou é o usuário.

### 5.3 Fase 0: linha de base
Rodar o conjunto com a configuração atual (Sonnet 5.5, padrões). O resultado é o custo de referência por mensagem e o comportamento de referência.

### 5.4 Fase 1: ajuste fino no Sonnet
No *Anthropic Chat Model*:
- **Prompt caching: 5 min** (decisão do Claude). Paga 1,25× para gravar e cerca de 1/20 do preço para ler. Ele acerta pelo menos nas voltas seguintes do mesmo laço e nas mensagens trocadas em poucos minutos. A opção de 1 h custa 2× para gravar e só compensaria com conversas espaçadas, o que pode ser revisto depois com os números.
- **Raciocínio: adaptativo, esforço *low*.** Se falhar em algum teste, sobe para *medium*. Não usar "disabled", que o Sonnet 5.5 rejeita com erro 400.
- Rodar o conjunto e comparar com a Fase 0.

### 5.5 Fase 2: Haiku 5.5
Mesmo nó, modelo `claude-haiku-5-5`, com cache e o esforço que venceu na Fase 1. Rodar o conjunto. **Só troca de vez se passar em todos os testes dos anti-objetivos** (confirmação, datas). Se falhar, fica o Sonnet da Fase 1 e o resultado é registrado como decisão.

### 5.6 Fallback no Groq
- No AI Agent, ligar **Enable Fallback Model** e conectar um *Groq Chat Model* com uma credencial do Groq. A chave é digitada pelo usuário.
- O fallback entra em qualquer erro do modelo principal: falta de crédito, sobrecarga, instabilidade.
- O modelo do Groq será escolhido na execução, entre os grátis atuais que chamam ferramentas bem, **depois de conferir os termos** (não treinar com os dados).
- Teste: rodar 3 ou 4 testes do conjunto forçando o fallback (por exemplo, com o modelo principal apontando para um ID inválido por alguns minutos), incluindo o de cancelar. Se o Groq pular a confirmação, isso fica anotado como risco conhecido do modo fallback.

### 5.7 Limite de gasto
O usuário define um **limite mensal de gasto** no console da Anthropic. A conta é dele, então quem faz é ele.

### 5.8 Registro
- Atualizar `workflows/prompt.md` ou a doc de setup com a configuração final do nó (cache, esforço, modelo, fallback).
- Uma entrada no `docs/learning-log.md` com os números de antes e depois.
- Reexportar o workflow alterado e limpar dados sensíveis, como foi feito na migração.

## 6. Fica para quem constrói
- O texto exato dos cerca de 15 testes.
- Qual modelo do Groq usar.
- O formato da tabela de resultados.
