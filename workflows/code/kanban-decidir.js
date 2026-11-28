// n8n Code node "Decidir" (Kanban: card movido) — mode: Run Once for Each Item.
// Applies the "one card at a time" rule: there is one n8n-teste, so one card
// holds the slot from "Em andamento" until it leaves "Para teste".
// Input $json:
//   action: { id, type, cardId, listBefore, listAfter }  (list names; null when the list did not change)
//   cards: [{ id, list, pos, labels }]                   (open cards, state after the action)
//   seenActionIds: string[]                              (Trello may deliver a webhook twice)
//   dispatched: string[]                                 (cards already sent to the agent, still in the slot)
// Output: { dispatch, queue, unqueue, reason } — card ids or null.

const EM_ANDAMENTO = 'Em andamento';
const PARA_TESTE = 'Para teste';
const NA_FILA = 'Na fila';
const SLOT_LISTS = [EM_ANDAMENTO, PARA_TESTE];

const { action, cards = [], seenActionIds = [], dispatched = [] } = $json;
const out = (dispatch, queue, unqueue, reason) => ({ json: { dispatch, queue, unqueue, reason } });

if (seenActionIds.includes(action.id)) return out(null, null, null, 'duplicate');

const { cardId, listBefore, listAfter } = action;
if (action.type !== 'updateCard' || !listBefore || !listAfter) {
  return out(null, null, null, 'Não é uma mudança de lista.');
}
if (listBefore === listAfter) return out(null, null, null, 'Mudou só a posição na lista.');

const inSlot = (list) => SLOT_LISTS.includes(list);
const queued = (c) => c.labels.includes(NA_FILA);
const byPos = (a, b) => a.pos - b.pos;
const actionCard = cards.find((c) => c.id === cardId);

// The slot is taken by someone else: a card in "Para teste", or a dispatched
// card still in "Em andamento" (running or "Bloqueado").
const others = cards.filter((c) => c.id !== cardId);
const slotTaken = others.some(
  (c) => c.list === PARA_TESTE || (c.list === EM_ANDAMENTO && dispatched.includes(c.id)),
);

// Entering "Em andamento" from anywhere else (Backlog, or back from "Para teste").
if (listAfter === EM_ANDAMENTO) {
  if (slotTaken) {
    return out(
      null,
      cardId,
      null,
      'Na fila: outro card está usando o n8n-teste. Este começa sozinho quando a vaga liberar.',
    );
  }
  // Two cards dragged together: both executions see the same board and the
  // highest one (lowest pos) wins in both, so only one is dispatched.
  const first = cards
    .filter((c) => c.list === EM_ANDAMENTO && (c.id === cardId || !queued(c)))
    .sort(byPos)[0];
  if (first && first.id !== cardId) {
    return out(null, cardId, null, 'Na fila: outro card entrou junto e está mais alto na lista.');
  }
  return out(cardId, null, null, 'Vaga livre.');
}

// Leaving the slot (to Backlog, Pronto or any list outside it).
if (inSlot(listBefore) && !inSlot(listAfter)) {
  if (actionCard && queued(actionCard)) {
    return out(null, null, cardId, 'Saiu da fila sem ter começado.');
  }
  if (slotTaken) return out(null, null, null, 'Outro card ainda está com a vaga.');
  const next = cards.filter((c) => c.list === EM_ANDAMENTO && queued(c)).sort(byPos)[0];
  if (!next) return out(null, null, null, 'Vaga livre e fila vazia.');
  return out(next.id, null, next.id, 'Vaga liberada: começa o próximo da fila.');
}

// "Em andamento" → "Para teste" keeps the slot; moves outside the slot do not touch it.
return out(null, null, null, 'Não mexe na vaga.');
