// n8n Code node "Planejar" (Portão de agenda) — mode: Run Once for Each Item.
// Turns one agenda operation into the first Google Calendar API request.
// Input: the trigger item { user_key, operation, title, date, start_time, end_time,
//   event_id, start_date, end_date, duration_minutes, earliest_time, latest_time }
//   plus the person's row from "Ler usuário" (calendar_id, timezone).
// Output: { operation, args, tz, calendarId, request: { method, url, query, body } }
//   or { done: true, result } when the input is invalid.
// Ported from src/zacretario/agent/calendar_tools.py (tag v1-python).

const args = $('When Executed by Another Workflow').item.json;
const user = $('Ler usuário').item.json;
const tz = user.timezone || 'America/Sao_Paulo';
const calendarId = user.calendar_id || 'primary';
const base = `https://www.googleapis.com/calendar/v3/calendars/${encodeURIComponent(calendarId)}/events`;

const fail = (message) => ({ json: { done: true, result: `Erro: ${message}` } });
const blank = (value) => value === undefined || value === null || String(value).trim() === '';

function parseDate(text) {
  const day = DateTime.fromISO(String(text).trim(), { zone: tz });
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(text).trim()) || !day.isValid) {
    throw new Error(`Data inválida: "${text}" (use AAAA-MM-DD)`);
  }
  return day.startOf('day');
}

function parseTime(text) {
  const match = /^(\d{1,2}):(\d{2})$/.exec(String(text).trim());
  if (!match || Number(match[1]) > 23 || Number(match[2]) > 59) {
    throw new Error(`Hora inválida: "${text}" (use HH:MM)`);
  }
  return { hour: Number(match[1]), minute: Number(match[2]) };
}

// No end means one hour; an end at or before the start means the next day.
function timedRange(day, startTime, endTime) {
  const start = day.set(startTime);
  if (!endTime) return [start, start.plus({ hours: 1 })];
  let end = day.set(endTime);
  if (end <= start) end = end.plus({ days: 1 });
  return [start, end];
}

const listRequest = (from, to) => ({
  method: 'GET',
  url: base,
  query: {
    timeMin: from.toISO(),
    timeMax: to.toISO(),
    singleEvents: 'true',
    orderBy: 'startTime',
    maxResults: '250',
  },
  body: {},
});

let request;
try {
  switch (args.operation) {
    case 'create': {
      if (blank(args.title)) throw new Error('Informe o título do evento.');
      const day = parseDate(args.date);
      let start;
      let end;
      if (blank(args.start_time)) {
        start = { date: day.toISODate() };
        end = { date: day.plus({ days: 1 }).toISODate() };
      } else {
        const range = timedRange(
          day,
          parseTime(args.start_time),
          blank(args.end_time) ? null : parseTime(args.end_time),
        );
        start = { dateTime: range[0].toISO(), timeZone: tz };
        end = { dateTime: range[1].toISO(), timeZone: tz };
      }
      request = {
        method: 'POST',
        url: base,
        query: { sendUpdates: 'none' },
        body: {
          summary: args.title,
          start,
          end,
          extendedProperties: { private: { zacretario: 'true' } },
        },
      };
      break;
    }
    case 'list': {
      const from = parseDate(args.start_date);
      const to = parseDate(args.end_date).plus({ days: 1 });
      request = listRequest(from, to);
      break;
    }
    case 'update':
    case 'delete': {
      if (blank(args.event_id)) throw new Error('Informe o id do evento (use list_events).');
      // First fetch the event: we need its times and must check who organised it.
      request = { method: 'GET', url: `${base}/${encodeURIComponent(args.event_id)}`, query: {}, body: {} };
      break;
    }
    case 'free_slots': {
      if (!(Number(args.duration_minutes) > 0)) throw new Error('A duração deve ser maior que zero.');
      const now = DateTime.now().setZone(tz);
      const first = parseDate(args.start_date);
      const from = first > now ? first : now;
      const to = parseDate(args.end_date).plus({ days: 1 });
      request = listRequest(from, to);
      break;
    }
    default:
      throw new Error(`Operação desconhecida: ${args.operation}`);
  }
} catch (error) {
  return fail(error.message);
}

return { json: { done: false, operation: args.operation, args, tz, calendarId, request } };
