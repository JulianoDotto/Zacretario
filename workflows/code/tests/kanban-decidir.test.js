// node --test workflows/code/tests/
const test = require('node:test');
const assert = require('node:assert/strict');
const { runCodeNode } = require('./run-code-node');

const EM = 'Em andamento';
const TESTE = 'Para teste';

const card = (id, list, pos, labels = []) => ({ id, list, pos, labels });
const move = (cardId, listBefore, listAfter, id = `act-${cardId}`) => ({
  id,
  type: 'updateCard',
  cardId,
  listBefore,
  listAfter,
});
const run = ({ action, cards, seenActionIds = [], dispatched = [] }) =>
  runCodeNode('kanban-decidir.js', { action, cards, seenActionIds, dispatched });
const nothing = (out) => {
  assert.equal(out.dispatch, null);
  assert.equal(out.queue, null);
  assert.equal(out.unqueue, null);
};

test('vaga livre', () => {
  const out = run({ action: move('A', 'Backlog', EM), cards: [card('A', EM, 1)] });
  assert.equal(out.dispatch, 'A');
  assert.equal(out.queue, null);
  assert.equal(out.unqueue, null);
});

test('vaga ocupada por card em teste', () => {
  const out = run({
    action: move('A', 'Backlog', EM),
    cards: [card('A', EM, 1), card('B', TESTE, 1)],
    dispatched: ['B'],
  });
  assert.equal(out.dispatch, null);
  assert.equal(out.queue, 'A');
  assert.equal(typeof out.reason, 'string');
  assert.notEqual(out.reason, '');
});

test('vaga ocupada por card bloqueado', () => {
  const out = run({
    action: move('A', 'Backlog', EM),
    cards: [card('B', EM, 1, ['Bloqueado']), card('A', EM, 2)],
    dispatched: ['B'],
  });
  assert.equal(out.dispatch, null);
  assert.equal(out.queue, 'A');
});

test('card já rodando, mesmo que o novo fique mais alto', () => {
  const out = run({
    action: move('A', 'Backlog', EM),
    cards: [card('A', EM, 1), card('C', EM, 2)],
    dispatched: ['C'],
  });
  assert.equal(out.dispatch, null);
  assert.equal(out.queue, 'A');
});

test('dois cards juntos, ninguém disparado: o de menor pos vence nas duas execuções', () => {
  const cards = [card('A', EM, 2), card('C', EM, 1)];
  const deC = run({ action: move('C', 'Backlog', EM), cards });
  assert.equal(deC.dispatch, 'C');
  assert.equal(deC.queue, null);
  const deA = run({ action: move('A', 'Backlog', EM), cards });
  assert.equal(deA.dispatch, null);
  assert.equal(deA.queue, 'A');
});

test('card bloqueado volta para Em andamento', () => {
  const out = run({
    action: move('A', 'Backlog', EM),
    cards: [card('A', EM, 1, ['Bloqueado'])],
    dispatched: [],
  });
  assert.equal(out.dispatch, 'A');
  assert.equal(out.queue, null);
});

test('reprovado no teste volta de Para teste para Em andamento', () => {
  const out = run({
    action: move('A', TESTE, EM),
    cards: [card('A', EM, 1)],
    dispatched: ['A'],
  });
  assert.equal(out.dispatch, 'A');
  assert.equal(out.queue, null);
});

test('de Em andamento para Para teste: o card continua com a vaga', () => {
  const out = run({
    action: move('A', EM, TESTE),
    cards: [card('A', TESTE, 1), card('C', EM, 1, ['Na fila'])],
    dispatched: ['A'],
  });
  nothing(out);
});

test('liberou a vaga: dispara o Na fila mais alto', () => {
  const out = run({
    action: move('B', TESTE, 'Pronto'),
    cards: [card('B', 'Pronto', 1), card('A', EM, 2, ['Na fila']), card('C', EM, 1, ['Na fila'])],
    dispatched: [],
  });
  assert.equal(out.dispatch, 'C');
  assert.equal(out.unqueue, 'C');
  assert.equal(out.queue, null);
});

test('voltou para o Backlog: dispara a fila', () => {
  const out = run({
    action: move('B', TESTE, 'Backlog'),
    cards: [card('B', 'Backlog', 1), card('A', EM, 1, ['Na fila'])],
    dispatched: [],
  });
  assert.equal(out.dispatch, 'A');
  assert.equal(out.unqueue, 'A');
});

test('liberou, mas outro card ainda segura a vaga', () => {
  const out = run({
    action: move('B', EM, 'Backlog'),
    cards: [card('B', 'Backlog', 1), card('D', TESTE, 1), card('A', EM, 1, ['Na fila'])],
    dispatched: ['D'],
  });
  nothing(out);
});

test('liberou sem fila', () => {
  const out = run({
    action: move('B', TESTE, 'Pronto'),
    cards: [card('B', 'Pronto', 1)],
    dispatched: [],
  });
  nothing(out);
});

test('card da fila sai de Em andamento: perde o Na fila', () => {
  const out = run({
    action: move('A', EM, 'Backlog'),
    cards: [card('A', 'Backlog', 1, ['Na fila']), card('C', EM, 1)],
    dispatched: ['C'],
  });
  assert.equal(out.unqueue, 'A');
  assert.equal(out.dispatch, null);
  assert.equal(out.queue, null);
});

test('reordenar na mesma lista', () => {
  const out = run({
    action: move('A', EM, EM),
    cards: [card('A', EM, 1), card('C', EM, 2)],
    dispatched: ['C'],
  });
  nothing(out);
});

test('movimento fora da vaga', () => {
  const out = run({
    action: move('A', 'Backlog', 'Pronto'),
    cards: [card('A', 'Pronto', 1), card('C', EM, 1, ['Na fila'])],
  });
  nothing(out);
});

test('webhook repetido', () => {
  const out = run({
    action: move('A', 'Backlog', EM, 'act-1'),
    cards: [card('A', EM, 1)],
    seenActionIds: ['act-0', 'act-1'],
  });
  nothing(out);
  assert.equal(out.reason, 'duplicate');
});

test('ação que não é mudança de lista', () => {
  for (const action of [
    { id: 'c1', type: 'commentCard', cardId: 'A', listBefore: null, listAfter: null },
    { id: 'l1', type: 'addLabelToCard', cardId: 'A', listBefore: null, listAfter: null },
    { id: 'u1', type: 'updateCard', cardId: 'A', listBefore: null, listAfter: null },
  ]) {
    nothing(run({ action, cards: [card('A', EM, 1)] }));
  }
});

test('card que não está no quadro (webhook forjado) não dispara', () => {
  const out = run({ action: move('X', 'Backlog', EM), cards: [] });
  nothing(out);
  assert.equal(out.reason, 'Card fora do quadro.');
});
