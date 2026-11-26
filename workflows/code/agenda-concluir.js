// n8n Code node "Concluir" (Portão de agenda) — mode: Run Once for Each Item.
// Summarises the Google response to the second request (PATCH or DELETE).
// Input $json: the HTTP response from "Google Agenda (por pessoa)": { statusCode, body }.

const plan = $('Planejar').item.json;
const { operation, args, tz } = plan;
const status = Number($json.statusCode);
const body = $json.body || {};

const WEEKDAYS = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom'];
const formatDay = (dt) => `${WEEKDAYS[dt.weekday - 1]} ${dt.toFormat('dd/MM')}`;
const parseWhen = (field) =>
  field.dateTime ? DateTime.fromISO(field.dateTime).setZone(tz) : DateTime.fromISO(field.date, { zone: tz });

function formatEvent(item) {
  const start = parseWhen(item.start);
  const end = parseWhen(item.end);
  const when = item.start.date
    ? `${formatDay(start)} (dia todo)`
    : `${formatDay(start)} ${start.toFormat('HH:mm')}–${end.toFormat('HH:mm')}`;
  return `${when} ${item.summary || '(sem título)'}`;
}

let result;
if (status === 404 || status === 410) {
  result = 'Evento não encontrado.';
} else if (!(status >= 200 && status < 300)) {
  result = `Erro no calendário: ${body.error?.message || `HTTP ${status}`}`;
} else if (operation === 'update') {
  result = `Evento atualizado (id ${body.id}): ${formatEvent(body)}`;
} else {
  result = `Evento ${args.event_id} apagado.`;
}

return { json: { done: true, result } };
