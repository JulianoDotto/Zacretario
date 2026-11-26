// n8n Code node "Decidir" (Portão de agenda) — mode: Run Once for Each Item.
// Reads the Google response to the first request and either finishes
// ({ done: true, result }) or prepares a second request for update/delete
// ({ done: false, request }) after checking the event is ours to change.
// Input $json: the HTTP response from "Google Agenda (por pessoa)": { statusCode, body }.
// Ported from calendar_tools.py, calendar/google.py and scheduling.py (tag v1-python).

const plan = $('Planejar').item.json;
const { operation, args, tz } = plan;
const status = Number($json.statusCode);
const body = $json.body || {};

const WEEKDAYS = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom'];
const READ_ONLY =
  'Este evento tem outros participantes ou foi organizado por outra pessoa, então não posso alterá-lo nem cancelá-lo.';
const blank = (value) => value === undefined || value === null || String(value).trim() === '';
const done = (result) => ({ json: { done: true, result } });

const formatDay = (dt) => `${WEEKDAYS[dt.weekday - 1]} ${dt.toFormat('dd/MM')}`;
const formatRange = (start, end) => `${formatDay(start)} ${start.toFormat('HH:mm')}–${end.toFormat('HH:mm')}`;

function parseWhen(field) {
  return field.dateTime
    ? DateTime.fromISO(field.dateTime).setZone(tz)
    : DateTime.fromISO(field.date, { zone: tz });
}

// Not safely ours to edit: another organiser, or any guest other than us.
// The API omits "self" when it is false, so a missing key means someone else.
function hasAttendees(item) {
  const organizer = item.organizer;
  const bySomeoneElse = organizer !== undefined && !organizer.self;
  return bySomeoneElse || (item.attendees || []).some((attendee) => !attendee.self);
}

function formatEvent(item) {
  const start = parseWhen(item.start);
  const end = parseWhen(item.end);
  const when = item.start.date ? `${formatDay(start)} (dia todo)` : formatRange(start, end);
  const suffix = hasAttendees(item) ? ' (com convidados — não posso alterar)' : '';
  return `${when} ${item.summary || '(sem título)'}${suffix}`;
}

function parseDate(text) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(text).trim())) throw new Error(`Data inválida: "${text}" (use AAAA-MM-DD)`);
  return DateTime.fromISO(String(text).trim(), { zone: tz }).startOf('day');
}

function parseTime(text) {
  const match = /^(\d{1,2}):(\d{2})$/.exec(String(text).trim());
  if (!match || Number(match[1]) > 23 || Number(match[2]) > 59) throw new Error(`Hora inválida: "${text}" (use HH:MM)`);
  return { hour: Number(match[1]), minute: Number(match[2]) };
}

function timedRange(day, startTime, endTime) {
  const start = day.set(startTime);
  if (!endTime) return [start, start.plus({ hours: 1 })];
  let end = day.set(endTime);
  if (end <= start) end = end.plus({ days: 1 });
  return [start, end];
}

// New start/end for an event, keeping its duration when only the day or the start changes.
function newTimes(item) {
  const newDay = blank(args.date) ? null : parseDate(args.date);
  const startTime = blank(args.start_time) ? null : parseTime(args.start_time);
  const endTime = blank(args.end_time) ? null : parseTime(args.end_time);
  const start = parseWhen(item.start);
  const end = parseWhen(item.end);

  if (item.start.date) {
    if (startTime) {
      const [s, e] = timedRange(newDay || start, startTime, endTime);
      return { start: { dateTime: s.toISO(), timeZone: tz, date: null }, end: { dateTime: e.toISO(), timeZone: tz, date: null } };
    }
    if (endTime) throw new Error('Evento de dia inteiro não tem horário de fim; informe start_time.');
    const days = end.diff(start, 'days').days;
    return {
      start: { date: newDay.toISODate(), dateTime: null },
      end: { date: newDay.plus({ days }).toISODate(), dateTime: null },
    };
  }

  const duration = end.diff(start);
  const day = (newDay || start).startOf('day');
  const begin = day.set(startTime || { hour: start.hour, minute: start.minute });
  const [s, e] = endTime ? timedRange(day, { hour: begin.hour, minute: begin.minute }, endTime) : [begin, begin.plus(duration)];
  return { start: { dateTime: s.toISO(), timeZone: tz, date: null }, end: { dateTime: e.toISO(), timeZone: tz, date: null } };
}

// One free slot per day (at most 5), 15-minute buffer around events, 15-minute steps.
function freeSlots(items) {
  const prefs = $('Ler usuário').item.json;
  const window = {
    start: parseTime(blank(args.earliest_time) ? prefs.day_start || '08:00' : args.earliest_time),
    end: parseTime(blank(args.latest_time) ? prefs.day_end || '22:00' : args.latest_time),
  };
  if (window.start.hour * 60 + window.start.minute >= window.end.hour * 60 + window.end.minute) {
    throw new Error('O horário inicial deve ser anterior ao final.');
  }
  const blocked = new Set((prefs.blocked_weekdays || []).map(Number)); // 0 = Monday
  const duration = { minutes: Number(args.duration_minutes) };
  const buffer = { minutes: 15 };
  const rangeStart = DateTime.fromISO(plan.request.query.timeMin).setZone(tz);
  const rangeEnd = DateTime.fromISO(plan.request.query.timeMax).setZone(tz);

  const busy = items
    .filter((item) => item.start.dateTime)
    .map((item) => [parseWhen(item.start).minus(buffer), parseWhen(item.end).plus(buffer)])
    .sort((a, b) => a[0] - b[0]);

  const roundUp = (moment) => {
    const midnight = moment.startOf('day');
    const steps = Math.ceil(moment.diff(midnight, 'minutes').minutes / 15);
    return midnight.plus({ minutes: steps * 15 });
  };

  const slots = [];
  for (let day = rangeStart.startOf('day'); day < rangeEnd && slots.length < 5; day = day.plus({ days: 1 })) {
    if (blocked.has(day.weekday - 1)) continue;
    const windowStart = DateTime.max(day.set(window.start), rangeStart);
    const windowEnd = DateTime.min(day.set(window.end), rangeEnd);
    let cursor = windowStart;
    for (const [busyStart, busyEnd] of [...busy, [windowEnd, windowEnd]]) {
      const gapEnd = DateTime.min(busyStart, windowEnd);
      const start = roundUp(cursor);
      if (start.plus(duration) <= gapEnd) {
        slots.push([start, start.plus(duration)]);
        break;
      }
      cursor = DateTime.max(cursor, busyEnd);
    }
  }
  return slots;
}

if (status === 404) return done('Evento não encontrado.');
if (!(status >= 200 && status < 300)) {
  return done(`Erro no calendário: ${body.error?.message || `HTTP ${status}`}`);
}

try {
  switch (operation) {
    case 'create':
      return done(`Evento criado (id ${body.id}): ${formatEvent(body)}`);
    case 'list': {
      const items = (body.items || []).filter((item) => item.status !== 'cancelled');
      if (items.length === 0) return done('Nenhum compromisso no período.');
      return done(items.map((item) => `[${item.id}] ${formatEvent(item)}`).join('\n'));
    }
    case 'update': {
      if (hasAttendees(body)) return done(READ_ONLY);
      const changesTime = !blank(args.date) || !blank(args.start_time) || !blank(args.end_time);
      if (!changesTime && blank(args.title)) return done('Erro: nada para alterar; informe título, data ou horário.');
      const patch = {};
      if (!blank(args.title)) patch.summary = args.title;
      if (changesTime) Object.assign(patch, newTimes(body));
      return {
        json: {
          done: false,
          request: { method: 'PATCH', url: plan.request.url, query: { sendUpdates: 'none' }, body: patch },
        },
      };
    }
    case 'delete':
      if (hasAttendees(body)) return done(READ_ONLY);
      return {
        json: {
          done: false,
          request: { method: 'DELETE', url: plan.request.url, query: { sendUpdates: 'none' }, body: {} },
        },
      };
    case 'free_slots': {
      const items = (body.items || []).filter((item) => item.status !== 'cancelled');
      const slots = freeSlots(items);
      if (slots.length === 0) return done('Nenhum horário livre encontrado.');
      return done(slots.map(([start, end]) => formatRange(start, end)).join('\n'));
    }
    default:
      return done(`Erro: operação desconhecida: ${operation}`);
  }
} catch (error) {
  return done(`Erro: ${error.message}`);
}
