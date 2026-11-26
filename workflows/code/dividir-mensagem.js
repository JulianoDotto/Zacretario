// n8n Code node "Dividir mensagem" — mode: Run Once for All Items.
// Splits a long reply into parts of at most LIMIT characters, breaking on line
// boundaries when possible (a single line longer than LIMIT is cut in chunks).
// Input items: { text, chatId }. Output: one item per part: { part, chatId }.

const LIMIT = 4096;

function splitMessage(text, limit = LIMIT) {
  const parts = [];
  let current = null; // null = no open part (different from an empty line)
  for (const line of text.split('\n')) {
    if (line.length > limit) {
      if (current !== null) parts.push(current);
      const chunks = [];
      for (let i = 0; i < line.length; i += limit) chunks.push(line.slice(i, i + limit));
      parts.push(...chunks.slice(0, -1));
      current = chunks[chunks.length - 1];
    } else if (current === null) {
      current = line;
    } else if (current.length + 1 + line.length <= limit) {
      current += '\n' + line;
    } else {
      parts.push(current);
      current = line;
    }
  }
  if (current !== null) parts.push(current);
  return parts.filter((part) => part.trim() !== '');
}

const out = [];
for (const item of $input.all()) {
  for (const part of splitMessage(item.json.text ?? '')) {
    out.push({ json: { part, chatId: item.json.chatId } });
  }
}
return out;
