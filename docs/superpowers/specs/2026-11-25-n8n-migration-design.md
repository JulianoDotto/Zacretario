# Zacretário no n8n — Design

Data: 2026-11-25
Status: rascunho para aprovação
Substitui: [`2026-11-25-wuzapi-design.md`](2026-11-25-wuzapi-design.md) (troca de canal no app Python; nunca implementado)

## 1. Intenção e porquê

Reconstruir o Zacretário como workflows do **n8n** self-hosted na VPS da Hostinger (`dotton8n.com.br`), com o WhatsApp via **Evolution API** no lugar da Cloud API da Meta. O app Python/FastAPI é aposentado.

**Por quê (nas palavras do usuário, em ordem de prioridade):**
1. **Aprender n8n.** É o objetivo principal de todo passo. Aprender Python era só conveniência; n8n é o que serve aos objetivos futuros dele.
2. **Vitrine para o currículo.** O repositório continua sendo portfólio.
3. **Futuro:** um esboço "plug and play" para freelances de automação, trocando só a configuração de cliente para cliente (um usuário por cliente em vez de ele + Bruna). **Fica para depois**, mas nada agora deve impedir isso.

## 2. Como vamos trabalhar ("piloto automático")

Decidido pelo usuário: o Claude usa o **Claude in Chrome** para chegar até a página certa (painel da Hostinger, editor do n8n, painel da Evolution) e diz o que fazer e por quê; **o usuário executa cada ação** (cliques, campos, criação de nós). Depois, o Claude relê a página para conferir. Vale para a infra e para os workflows.

Consequências:
- O Claude não cria, edita nem publica workflows sozinho, nem muda configurações. Ler é livre (páginas, conectores da Hostinger e do n8n em modo leitura, se o usuário conectá-los).
- Senhas, chaves de API e tokens o usuário digita; o Claude nunca os recebe no chat.
- O plano de implementação é escrito como **roteiro guiado**: cada passo diz a página, a ação do usuário, o porquê (o conceito de n8n por trás) e como conferir. Não há "código a escrever" no sentido do app Python.

## 3. Objetivos

- O bot faz no WhatsApp o mesmo que hoje: eventos (criar, listar, remarcar, cancelar, achar horários livres), TODOs (adicionar, listar, concluir, apagar), preferências de horário, confirmação antes de ações destrutivas, memória curta da conversa, recusa do que está fora do escopo, só texto. O comportamento de referência é o README e o prompt atual (`src/zacretario/agent/prompt.py`), que é reaproveitado quase inteiro.
- Mesmas proteções: só números permitidos respondem, mensagens duplicadas são ignoradas, o bot ignora as próprias mensagens e grupos, eventos com convidados ou de outro organizador são somente leitura.
- Tudo que muda de cliente para cliente (nomes, telefones, ID da agenda, fuso, modelo) fica num **lugar só de configuração**, nunca espalhado dentro dos nós.
- O repositório mostra a migração: workflows exportados, documentação de instalação e o registro das decisões.

## 4. Não-objetivos

- O template multi-cliente "plug and play" em si (empacotamento, instalação automática por cliente). Só o hábito da configuração centralizada entra agora.
- Áudio, imagem, grupos, lembretes proativos (a Evolution facilita lembretes, fica para `future-improvements.md`).
- Manter o app Python funcionando em paralelo.
- API oficial da Meta.

## 5. Anti-objetivos

- **O Claude construir no lugar do usuário.** Se o usuário termina sem saber refazer, falhou, mesmo que o bot funcione.
- Ligar o bot a um número pessoal (lê todas as conversas; banimento derruba o WhatsApp real).
- Expor a Evolution API sem proteção: quem a alcança manda mensagem como o bot.
- Credenciais, telefones ou chaves no repositório (inclusive nos JSONs exportados).
- Esconder que a integração com o WhatsApp é não oficial e pode levar a banimento.

## 6. Abordagens consideradas

**Canal de WhatsApp (escolha do usuário: Evolution API).**

| | Abordagem | A favor | Contra |
|---|---|---|---|
| **A (escolhida)** | Evolution API em Docker na VPS | Padrão do mercado brasileiro de n8n (o que aparece nos freelances); integração com n8n e muito material em português; "instâncias" combinam com um cliente por instância no futuro | Não oficial (banimento); mais pesada (precisa de Postgres, Redis opcional); licença Apache 2.0 com condições extras (não remover logo/copyright do painel; aviso visível de que a Evolution é usada); a versão 2.4 em teste traz registro num servidor de licenças |
| B | WuzAPI | MIT sem condições; leve; pesquisa já feita | Pouco usada com n8n; ensina menos do mercado |
| C | Cloud API oficial da Meta | Oficial | A burocracia que travou o projeto (erro 131037) |

Custo de software: zero nas duas não oficiais; os custos são a VPS (já paga), tokens do Claude e o chip.

**Divisão do trabalho** (escolha do usuário: piloto automático, §2). Descartados: Claude constrói e explica depois (aprende pouco); usuário faz tudo sem navegação assistida (lento sem ganho de aprendizado).

## 7. Decisões

**Do usuário:** n8n; Evolution API; aprendizado acima de tudo; modo piloto automático; template multi-cliente fica para depois.

**Do Claude (propostas, podem ser corrigidas):**

- **Ponto de partida (já decidido em conversa anterior):** nada do app Python está na VPS nem em produção; tudo rodou só localmente. Não há dados a migrar do Neon: começa do zero. **O n8n ainda não está configurado na VPS**: a instalação é do zero, sem nada a preservar.
- **Chip dedicado (do usuário):** autenticado na Anatel em 2026-11-25, pronto para uso. Para parear na Evolution, ele precisa primeiro estar ativo no app WhatsApp (ou WhatsApp Business) de um celular. Os testes usam mensagens reais; uma mensagem real capturada vira o payload fixado ("pin data") no n8n para testar sem precisar mandar mensagem a cada ajuste.
- **Code nodes (JavaScript): sim, com certeza (do usuário)** — "code nodes certos podem gerar até produtos diferentes". Cada um vem explicado no roteiro e escrito para ser reaproveitável. Candidatos: achar horários livres (o algoritmo de `scheduling.py`: janela de preferência, folga de 15 min, no máximo um horário por dia, dias bloqueados), a checagem de organizador/convidados, a divisão de mensagens longas e, se preciso, a leitura do payload.
- **Primeiro passo é reconhecimento:** ver o que já existe na VPS (n8n instalado? como: template da Hostinger, Docker Compose, Traefik/Caddy? versão? banco do n8n?) e o DNS do domínio. O resto da infra se adapta ao que existir.
- **Evolution API em Docker** na mesma VPS, versão estável fixada (2.3.x, não `latest`, não a 2.4 de teste), na mesma rede Docker do n8n. O n8n chama a Evolution pelo nome do container; a Evolution chama o webhook do n8n pela rede interna. A porta da Evolution **não fica aberta na internet**; o painel (QR code) é acessado por túnel SSH. As condições de licença são cumpridas mantendo o painel intacto e citando a Evolution no README.
- **Banco:** um Postgres na VPS (o que a Evolution exige), com um banco separado `zacretario` para TODOs, preferências, deduplicação e memória do chat. Sai o Neon — menos serviços, e um cliente futuro recebe tudo numa VPS só.
- **Workflows** (nomes provisórios):
  1. **Entrada WhatsApp:** Webhook ← Evolution (evento de mensagem recebida) → filtros (não é do próprio número, não é grupo, é texto) → deduplicação por id da mensagem (insert com conflito ignorado) → busca o usuário na configuração (desconhecido: para e registra o identificador no log da execução, para copiar à configuração) → chama o Agente → envia a resposta pela Evolution (dividindo mensagens longas).
  2. **Agente:** nó AI Agent com Anthropic Chat Model (`claude-sonnet-5-5`, como hoje), Postgres Chat Memory por usuário (janela de ~20 mensagens), prompt do `prompt.py` adaptado, ferramentas abaixo.
  3. **Ferramentas:** Postgres (TODOs, preferências) e Google Calendar via um **"portão de agenda"** (abaixo). Remarcar e cancelar **verificam organizador e convidados antes** (regra do commit `69977b8`).
- **Cada pessoa com a própria conta Google, um agente só (decisão do usuário: nada de compartilhar contas; chamada do Claude: como).** No n8n a credencial fica presa ao nó, não muda conforme quem escreve. Então as ferramentas de agenda do agente não usam o nó do Google Calendar direto: chamam um sub-workflow **"Portão de agenda"** com `{usuário, operação, parâmetros}`. Lá dentro, um Switch pelo usuário leva a **um nó HTTP Request por pessoa**, cada um com a credencial Google OAuth2 daquela pessoa, chamando a API do Google Calendar com método e URL montados pela operação. Toda a lógica (prompt, memória, regras, horários livres) fica num lugar só; o que é de cada pessoa é uma credencial + um ramo. Adicionar alguém = conectar a conta dela + um ramo no Switch + uma linha em `users`. Para um cliente de freelance, é o mesmo esboço com um ramo só. Descartados: um workflow inteiro copiado por pessoa (mudar o prompt vira mudar N cópias) e guardar tokens OAuth no banco e renová-los à mão (refaz o que o n8n já faz, com mais risco).
  4. **Tratamento de erro:** Error Trigger que avisa o usuário dono (mensagem curta) quando uma execução falha.
- **Configuração central:** tabela `users` no banco `zacretario` (telefone/LID, nome, ID da agenda, fuso, horários padrão) + credenciais do n8n. Nada disso dentro dos nós.
- **Repositório:** o código Python é preservado numa tag (`v1-python`) e sai do `main`. O `main` passa a ter `workflows/*.json` (exportados sem credenciais), `infra/` (compose da Evolution, se for nosso), docs de instalação reescritas e um README que conta a história (Python → n8n, Meta → Evolution). `docs/meta-whatsapp-notes.md` fica como histórico; o spec da WuzAPI fica marcado como substituído.
- **Exportação para o git:** ao fim de cada etapa, o usuário exporta o workflow no n8n (ou o Claude lê via conector, se conectado) e o Claude revisa o JSON para não haver segredo antes de o usuário aprovar o commit.
- **Diário de aprendizado:** `docs/learning-log.md`, uma entrada curta por etapa (o que foi feito, o conceito de n8n aprendido, o que deu errado). Serve ao aprendizado e à vitrine.
- **Ordem sugerida das etapas:** reconhecimento da VPS → instalar n8n (domínio, HTTPS) → Evolution e Postgres no ar, número pareado → "eco" (webhook recebe e responde a mesma mensagem) → banco e configuração → agente só com TODOs → portão de agenda e Google Calendar → regras de segurança e confirmação → erros → exportação/docs/README. Cada etapa termina com algo funcionando no WhatsApp.

## 8. Riscos aceitos

- Banimento do número (uso não oficial). Mitigação: chip dedicado, dois usuários, só responde a quem escreve.
- Quebra por mudança no protocolo do WhatsApp até a Evolution atualizar. Mitigação: versão fixada e passo de atualização documentado.
- Mudança de licença da Evolution (servidor de licenças na 2.4). Mitigação: versão fixada; reavaliar antes de atualizar.
- VPS KVM 1 com n8n + Evolution + Postgres (+ Redis): conferir uso de memória no reconhecimento.

## 9. Deixado para quem construir

- Detalhes da instalação conforme o que o reconhecimento encontrar (proxy reverso, rede Docker, versão do n8n).
- Formato exato do payload da Evolution (remetente, `@lid`, id, texto) — confirmar com uma mensagem real.
- Como o agente recebe "agora" e o fuso (expressão no prompt) e a divisão de mensagens longas.
- O nível de detalhe de cada passo do roteiro, seguindo o estilo das docs atuais (passos numerados, links para a seção exata).
