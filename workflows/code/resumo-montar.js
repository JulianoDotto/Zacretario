// n8n Code node 'Montar resumo' (Resumo do dia) — mode: Run Once for Each Item.
// Builds the morning WhatsApp summary.
// Input $json: { name, today (like 'sex 28/11'), agenda (text from 'Portão de agenda', operation list),
//   todos: [{ id, text }] }.
// Output: { text }.
const { name, today } = $json;
const todos = ($json.todos || []).filter((t) => t && t.id !== undefined && t.id !== null);
const agenda = String($json.agenda ?? '').trim();

const agendaFailed = agenda === '' || agenda.startsWith('Erro');
const agendaEmpty = !agendaFailed && agenda.startsWith('Nenhum compromisso');

const header = `Bom dia, ${name}! Hoje é ${today}.`;

if (agendaEmpty && todos.length === 0) {
  return { json: { text: `${header} Sua agenda está livre e você não tem TODOs em aberto.` } };
}

const blocks = [header];

if (agendaFailed) {
  blocks.push('Não consegui ler sua agenda agora.');
} else if (agendaEmpty) {
  blocks.push('📅 Agenda livre hoje.');
} else {
  // Each line is "[google-id] sex 28/11 09:00–10:00 Title": drop the id and the day.
  const lines = agenda.split('\n').map((line) =>
    line
      .replace(/^\[[^\]]*\]\s*/, '')
      .replace(/^(seg|ter|qua|qui|sex|sáb|dom) \d{2}\/\d{2}\s*/, '')
      .trim(),
  );
  blocks.push(['📅 Agenda de hoje:', ...lines.filter(Boolean).map((l) => `📅 ${l}`)].join('\n'));
}

if (todos.length === 0) {
  blocks.push('✅ Nenhum TODO em aberto.');
} else {
  blocks.push(['✅ TODOs em aberto:', ...todos.map((t) => `✅ ${t.id}. ${t.text}`)].join('\n'));
}

return { json: { text: blocks.join('\n\n') } };
