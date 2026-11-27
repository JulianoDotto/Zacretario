// node --test workflows/code/tests/
const test = require('node:test');
const assert = require('node:assert/strict');
const { runCodeNode, fixture } = require('./run-code-node');

const run = (item) => runCodeNode('normalizar-mensagem.js', item);
const msg = (item) => item.body.data.message;

test('texto continua igual', () => {
  const out = run(fixture('messages-upsert-texto.json'));
  assert.equal(out.isText, true);
  assert.equal(out.text, 'Oi');
  assert.equal(out.ignore, false);
  assert.equal(out.mediaKind, null);
  assert.equal(out.tooBig, false);
});

test('áudio próprio', () => {
  const out = run(fixture('messages-upsert-audio.json'));
  assert.equal(out.isText, false);
  assert.equal(out.mediaKind, 'audio');
  assert.equal(out.mimetype, 'audio/ogg; codecs=opus');
  assert.equal(out.isForwarded, false);
  assert.equal(out.tooBig, false);
  assert.equal(out.ignore, false);
  assert.equal(out.caption, null);
});

test('áudio encaminhado', () => {
  const item = fixture('messages-upsert-audio.json');
  msg(item).audioMessage.contextInfo = { forwardingScore: 1, isForwarded: true };
  assert.equal(run(item).isForwarded, true);
});

test('áudio de 301 s é grande demais', () => {
  const item = fixture('messages-upsert-audio.json');
  msg(item).audioMessage.seconds = 301;
  assert.equal(run(item).tooBig, true);
});

test('áudio de 300 s ainda passa', () => {
  const item = fixture('messages-upsert-audio.json');
  msg(item).audioMessage.seconds = 300;
  assert.equal(run(item).tooBig, false);
});

test('imagem com legenda', () => {
  const out = run(fixture('messages-upsert-imagem.json'));
  assert.equal(out.mediaKind, 'image');
  assert.equal(out.caption, 'Coloca na agenda');
  assert.equal(out.mimetype, 'image/jpeg');
  assert.equal(out.tooBig, false);
});

test('imagem de 6 MB com fileLength string é grande demais', () => {
  const item = fixture('messages-upsert-imagem.json');
  msg(item).imageMessage.fileLength = '6291456';
  assert.equal(run(item).tooBig, true);
});

test('imagem de 6 MB com fileLength {low, high} é grande demais', () => {
  const item = fixture('messages-upsert-imagem.json');
  msg(item).imageMessage.fileLength = { low: 6291456, high: 0, unsigned: true };
  assert.equal(run(item).tooBig, true);
});

test('arquivo acima de 4 GB ({high: 1}) é grande demais', () => {
  const item = fixture('messages-upsert-pdf.json');
  msg(item).documentMessage.fileLength = { low: 0, high: 1, unsigned: true };
  assert.equal(run(item).tooBig, true);
});

test('PDF sem legenda', () => {
  const out = run(fixture('messages-upsert-pdf.json'));
  assert.equal(out.mediaKind, 'pdf');
  assert.equal(out.caption, null);
  assert.equal(out.tooBig, false);
});

test('PDF de 11 páginas é grande demais', () => {
  const item = fixture('messages-upsert-pdf.json');
  msg(item).documentMessage.pageCount = 11;
  assert.equal(run(item).tooBig, true);
});

test('PDF sem fileLength nem pageCount não é barrado', () => {
  const item = fixture('messages-upsert-pdf.json');
  delete msg(item).documentMessage.fileLength;
  delete msg(item).documentMessage.pageCount;
  assert.equal(run(item).tooBig, false);
});

test('documentWithCaptionMessage com PDF', () => {
  const item = fixture('messages-upsert-pdf.json');
  const doc = { ...msg(item).documentMessage, caption: 'põe na agenda' };
  item.body.data.message = { documentWithCaptionMessage: { message: { documentMessage: doc } } };
  const out = run(item);
  assert.equal(out.mediaKind, 'pdf');
  assert.equal(out.caption, 'põe na agenda');
  assert.equal(out.ignore, false);
});

test('documento .docx não é legível, mas recebe aviso', () => {
  const item = fixture('messages-upsert-pdf.json');
  msg(item).documentMessage.mimetype =
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  const out = run(item);
  assert.equal(out.mediaKind, null);
  assert.equal(out.ignore, false);
});

test('vídeo não é legível, mas recebe aviso', () => {
  const item = fixture('messages-upsert-audio.json');
  item.body.data.message = { videoMessage: { mimetype: 'video/mp4', seconds: 10 } };
  const out = run(item);
  assert.equal(out.mediaKind, null);
  assert.equal(out.ignore, false);
});

test('legenda só de espaços vira null', () => {
  const item = fixture('messages-upsert-imagem.json');
  msg(item).imageMessage.caption = '   ';
  assert.equal(run(item).caption, null);
});
