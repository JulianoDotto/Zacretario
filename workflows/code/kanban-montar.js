// Builds the input of "Decidir" from the Trello webhook and the board state.
// Reads the static data (seenActionIds, dispatched) without writing it; "Registrar" writes.
const SLOT_LISTS = ['Em andamento', 'Para teste'];

const action = $('Trello: algo mudou').item.json.action;
const board = $json;

const listName = {};
for (const list of board.lists || []) listName[list.id] = list.name;

const cards = (board.cards || []).map((c) => ({
  id: c.id,
  list: listName[c.idList] || c.idList,
  pos: c.pos,
  labels: (c.labels || []).map((l) => l.name),
}));

const data = $getWorkflowStaticData('global');
const inSlot = new Set(cards.filter((c) => SLOT_LISTS.includes(c.list)).map((c) => c.id));
// A dispatched card that left "Em andamento"/"Para teste" no longer holds the slot.
const dispatched = (data.dispatched || []).filter((id) => inSlot.has(id));

const d = action.data || {};
return {
  json: {
    action: {
      id: action.id,
      type: action.type,
      cardId: d.card?.id ?? null,
      listBefore: d.listBefore?.name ?? null,
      listAfter: d.listAfter?.name ?? null,
    },
    cards,
    seenActionIds: data.seenActionIds || [],
    dispatched,
  },
};
