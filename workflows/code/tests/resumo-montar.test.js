// node --test workflows/code/tests/
// "Montar resumo" of the daily summary: greeting + agenda block + TODO block.
const test = require('node:test');
const assert = require('node:assert/strict');
const { runCodeNode } = require('./run-code-node');

const montar = (input) => runCodeNode('resumo-montar.js', input);
const base = { name: 'Teste', today: 'sex 28/11' };

test('dia com eventos e TODOs: dois blocos, sem o id do Google', () => {
  const out = montar({
    ...base,
    agenda: '[abc123def] sex 28/11 09:00–10:00 Dentista\n[xyz789] sex 28/11 (dia todo) Feriado',
    todos: [
      { id: 3, text: 'Comprar pão' },
      { id: 7, text: 'Pagar conta' },
    ],
  });
  assert.equal(
    out.text,
    [
      'Bom dia, Teste! Hoje é sex 28/11.',
      '',
      '📅 Agenda de hoje:',
      '📅 09:00–10:00 Dentista',
      '📅 (dia todo) Feriado',
      '',
      '✅ TODOs em aberto:',
      '✅ 3. Comprar pão',
      '✅ 7. Pagar conta',
    ].join('\n'),
  );
  assert.ok(!out.text.includes('abc123def'));
});

test('dia vazio: mensagem curta', () => {
  const out = montar({ ...base, agenda: 'Nenhum compromisso no período.', todos: [] });
  assert.equal(out.text, 'Bom dia, Teste! Hoje é sex 28/11. Sua agenda está livre e você não tem TODOs em aberto.');
});

test('só TODOs: agenda livre em uma linha', () => {
  const out = montar({ ...base, agenda: 'Nenhum compromisso no período.', todos: [{ id: 1, text: 'Ligar' }] });
  assert.equal(
    out.text,
    ['Bom dia, Teste! Hoje é sex 28/11.', '', '📅 Agenda livre hoje.', '', '✅ TODOs em aberto:', '✅ 1. Ligar'].join('\n'),
  );
});

test('só eventos: sem TODOs em uma linha', () => {
  const out = montar({ ...base, agenda: '[a1] sex 28/11 14:30–15:30 Reunião', todos: [] });
  assert.equal(
    out.text,
    ['Bom dia, Teste! Hoje é sex 28/11.', '', '📅 Agenda de hoje:', '📅 14:30–15:30 Reunião', '', '✅ Nenhum TODO em aberto.'].join('\n'),
  );
});

test('erro da agenda: traz os TODOs e avisa', () => {
  for (const agenda of ['Erro: Data inválida', 'Erro no calendário: HTTP 500']) {
    const out = montar({ ...base, agenda, todos: [{ id: 2, text: 'Ligar' }] });
    assert.ok(out.text.includes('Não consegui ler sua agenda agora.'));
    assert.ok(out.text.includes('✅ 2. Ligar'));
    assert.ok(!out.text.includes('Erro'));
  }
});

test('erro da agenda sem TODOs: avisa e diz que não há TODOs', () => {
  const out = montar({ ...base, agenda: 'Erro: x', todos: [] });
  assert.ok(out.text.includes('Não consegui ler sua agenda agora.'));
  assert.ok(out.text.includes('Nenhum TODO em aberto.'));
});

test('agenda ausente conta como erro', () => {
  const out = montar({ ...base, todos: [] });
  assert.ok(out.text.includes('Não consegui ler sua agenda agora.'));
});
