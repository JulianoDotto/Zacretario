// n8n Code node "Normalizar mensagem" — mode: Run Once for Each Item.
// Turns the Evolution API MESSAGES_UPSERT webhook into the few fields the
// rest of the workflow needs. Payload sample: workflows/fixtures/messages-upsert-texto.json

// Any media type. Readable ones (see readableMedia) go to "Ler mídia";
// the rest get the "text only" notice.
const MEDIA_TYPES = new Set([
  'imageMessage', 'audioMessage', 'videoMessage', 'documentMessage', 'documentWithCaptionMessage',
  'stickerMessage', 'locationMessage', 'liveLocationMessage', 'contactMessage', 'contactsArrayMessage',
  'ptvMessage',
]);

// Limits for readable media. Above them the person gets a polite notice and
// nothing is fetched. Missing metadata never blocks a message.
const MAX_AUDIO_SECONDS = 300;
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const MAX_PDF_BYTES = 10 * 1024 * 1024;
const MAX_PDF_PAGES = 10;

// WhatsApp sends 64-bit sizes as {low, high}; they may also come as a number or a string.
function toNumber(value) {
  if (value == null) return null;
  if (typeof value === 'object') return (value.high >>> 0) * 2 ** 32 + (value.low >>> 0);
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

const over = (value, max) => value !== null && value > max;

// Returns { mediaKind, media } for audio, images and PDFs, or null.
function readableMedia(message) {
  if (message.audioMessage) return { mediaKind: 'audio', media: message.audioMessage };
  if (message.imageMessage) return { mediaKind: 'image', media: message.imageMessage };
  const doc = message.documentMessage
    ?? message.documentWithCaptionMessage?.message?.documentMessage;
  if (doc?.mimetype === 'application/pdf') return { mediaKind: 'pdf', media: doc };
  return null;
}

function isTooBig(mediaKind, media) {
  const bytes = toNumber(media.fileLength);
  if (mediaKind === 'audio') return over(toNumber(media.seconds), MAX_AUDIO_SECONDS);
  if (mediaKind === 'image') return over(bytes, MAX_IMAGE_BYTES);
  return over(bytes, MAX_PDF_BYTES) || over(toNumber(media.pageCount), MAX_PDF_PAGES);
}

const body = $json.body ?? {};
const data = body.data ?? {};
const key = data.key ?? {};

// Disappearing and view-once messages wrap the real message one level down.
let message = data.message ?? {};
for (const wrapper of ['ephemeralMessage', 'viewOnceMessage', 'viewOnceMessageV2']) {
  if (message[wrapper]?.message) message = message[wrapper].message;
}

// WhatsApp is moving senders to "@lid" ids. Prefer the phone JID when either
// field carries one; otherwise keep the raw id so it can still be allowlisted.
const jids = [key.remoteJid, key.remoteJidAlt].filter(Boolean);
const phoneJid = jids.find((jid) => jid.endsWith('@s.whatsapp.net'));
const sender = phoneJid ? phoneJid.split('@')[0] : (key.remoteJid ?? '');

const rawText = message.conversation ?? message.extendedTextMessage?.text ?? null;
const text = typeof rawText === 'string' && rawText.trim() !== '' ? rawText.trim() : null;
const isText = text !== null;
const isMedia = !isText && Object.keys(message).some((type) => MEDIA_TYPES.has(type));

const readable = isMedia ? readableMedia(message) : null;
const media = readable?.media ?? {};
const rawCaption = typeof media.caption === 'string' ? media.caption.trim() : '';

return {
  json: {
    isMessageEvent: body.event === 'messages.upsert',
    messageId: key.id ?? '',
    chatId: key.remoteJid ?? '', // reply exactly where the message came from
    sender,
    text,
    fromMe: key.fromMe === true,
    isGroup: (key.remoteJid ?? '').endsWith('@g.us'),
    isText,
    // Readable media: 'audio' | 'image' | 'pdf'. null for text and for media the bot can't read.
    mediaKind: readable?.mediaKind ?? null,
    mimetype: readable ? (media.mimetype ?? null) : null,
    caption: rawCaption !== '' ? rawCaption : null,
    // A forwarded voice note is someone else speaking: treated as data, not as a request.
    isForwarded: media.contextInfo?.isForwarded === true || data.contextInfo?.isForwarded === true,
    tooBig: readable ? isTooBig(readable.mediaKind, media) : false,
    // Evolution does not store messages (DATABASE_SAVE_DATA_NEW_MESSAGE=false), so
    // "Ler mídia" hands it the whole message: the media keys let it download and decrypt.
    webMessage: readable ? { key, message } : null,
    // Reactions, edits, deletions, poll votes and other events: no reply at all.
    ignore: !isText && !isMedia,
  },
};
