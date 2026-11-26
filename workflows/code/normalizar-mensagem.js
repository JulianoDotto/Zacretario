// n8n Code node "Normalizar mensagem" — mode: Run Once for Each Item.
// Turns the Evolution API MESSAGES_UPSERT webhook into the few fields the
// rest of the workflow needs. Payload sample: workflows/fixtures/messages-upsert-texto.json

const body = $json.body ?? {};
const data = body.data ?? {};
const key = data.key ?? {};
const message = data.message ?? {};

// WhatsApp is moving senders to "@lid" ids. Prefer the phone JID when either
// field carries one; otherwise keep the raw id so it can still be allowlisted.
const jids = [key.remoteJid, key.remoteJidAlt].filter(Boolean);
const phoneJid = jids.find((jid) => jid.endsWith('@s.whatsapp.net'));
const sender = phoneJid ? phoneJid.split('@')[0] : (key.remoteJid ?? '');

const rawText = message.conversation ?? message.extendedTextMessage?.text ?? null;
const text = typeof rawText === 'string' && rawText.trim() !== '' ? rawText.trim() : null;

return {
  json: {
    isMessageEvent: body.event === 'messages.upsert',
    messageId: key.id ?? '',
    chatId: key.remoteJid ?? '', // reply exactly where the message came from
    sender,
    text,
    fromMe: key.fromMe === true,
    isGroup: (key.remoteJid ?? '').endsWith('@g.us'),
    isText: text !== null,
  },
};
