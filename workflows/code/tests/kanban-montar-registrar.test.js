// node --test workflows/code/tests/
// "Montar entrada" and "Registrar" around "Decidir", with the real Trello webhook format.
const test = require('node:test');
const assert = require('node:assert/strict');
const { runCodeNode, fixture } = require('./run-code-node');

// What "Buscar quadro" returns: GET /1/boards/{id}?cards=open&lists=open.
const board = (cards) => ({
  id: 'board-zacretario',
  lists: [
    { id: 'list-backlog', name: 'Backlog' },
    { id: 'list-em-andamento', name: 'Em andamento' },
    { id: 'list-para-teste', name: 'Para teste' },
    { id: 'list-pronto', name: 'Pronto' },
  ],
  cards,
});
const montar = (webhook, cards, staticData = {}) =>
  runCodeNode('kanban-montar.js', board(cards), { 'Trello: algo mudou': webhook }, staticData);

test('montar: lê o webhook real do Trello', () => {
  const out = montar(fixture('trello-update-card.json'), [
    { id: 'card-1', idList: 'list-backlog', pos: 2, labels: [] },
    { id: 'card-2', idList: 'list-em-andamento', pos: 1, labels: [{ id: 'l', name: 'Na fila', color: 'yellow' }] },
  ]);
  assert.deepEqual(out.action, {
    id: 'action-1',
    type: 'updateCard',
    cardId: 'card-1',
    listBefore: 'Em andamento',
    listAfter: 'Backlog',
  });
  assert.deepEqual(out.cards, [
    { id: 'card-1', list: 'Backlog', pos: 2, labels: [] },
    { id: 'card-2', list: 'Em andamento', pos: 1, labels: ['Na fila'] },
  ]);
  assert.deepEqual(out.seenActionIds, []);
  assert.deepEqual(out.dispatched, []);
});

test('montar: esquece o card disparado que saiu da vaga', () => {
  const out = montar(
    fixture('trello-update-card.json'),
    [
      { id: 'card-1', idList: 'list-backlog', pos: 1, labels: [] },
      { id: 'card-3', idList: 'list-para-teste', pos: 1, labels: [] },
    ],
    { dispatched: ['card-1', 'card-3'], seenActionIds: ['action-0'] },
  );
  assert.deepEqual(out.dispatched, ['card-3']);
  assert.deepEqual(out.seenActionIds, ['action-0']);
});

test('montar: ação sem mudança de lista vira listas nulas', () => {
  const webhook = fixture('trello-update-card.json');
  webhook.action.type = 'commentCard';
  delete webhook.action.data.listBefore;
  delete webhook.action.data.listAfter;
  const out = montar(webhook, []);
  assert.equal(out.action.listBefore, null);
  assert.equal(out.action.listAfter, null);
});

const registrar = (decision, input, staticData) =>
  runCodeNode('kanban-registrar.js', decision, { 'Montar entrada': input }, staticData);
const input = (overrides = {}) => ({
  action: { id: 'action-9', type: 'updateCard', cardId: 'card-1', listBefore: 'Backlog', listAfter: 'Em andamento' },
  cards: [],
  seenActionIds: ['action-8'],
  dispatched: ['card-3'],
  ...overrides,
});

test('registrar: guarda a ação e o card disparado', () => {
  const data = {};
  const out = registrar({ dispatch: 'card-1', queue: null, unqueue: null, reason: 'Vaga livre.' }, input(), data);
  assert.deepEqual(data.seenActionIds, ['action-8', 'action-9']);
  assert.deepEqual(data.dispatched, ['card-3', 'card-1']);
  assert.equal(out.cardId, 'card-1');
  assert.equal(out.dispatch, 'card-1');
});

test('registrar: grava a vaga já sem os cards que saíram', () => {
  const data = { dispatched: ['card-1', 'card-3'] };
  registrar({ dispatch: null, queue: null, unqueue: null, reason: 'x' }, input({ dispatched: ['card-3'] }), data);
  assert.deepEqual(data.dispatched, ['card-3']);
});

test('registrar: webhook repetido não entra de novo na lista', () => {
  const data = { seenActionIds: ['action-8'] };
  registrar({ dispatch: null, queue: null, unqueue: null, reason: 'duplicate' }, input(), data);
  assert.deepEqual(data.seenActionIds, ['action-8']);
});

test('registrar: guarda só as últimas 50 ações', () => {
  const seen = Array.from({ length: 50 }, (_, i) => `action-${i}`);
  const data = {};
  registrar({ dispatch: null, queue: null, unqueue: null, reason: 'x' }, input({ seenActionIds: seen }), data);
  assert.equal(data.seenActionIds.length, 50);
  assert.equal(data.seenActionIds[0], 'action-1');
  assert.equal(data.seenActionIds[49], 'action-9');
});
