// Runs the source of an n8n Code node ("Run Once for Each Item") outside n8n.
// The node's `$json` is the item passed in; `$('Node name')` reads from `nodes`.
// Usage: runCodeNode('normalizar-mensagem.js', webhookItem) -> the returned item's json.
const fs = require('node:fs');
const path = require('node:path');

function runCodeNode(file, json, nodes = {}) {
  const src = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
  const $ = (name) => {
    if (!(name in nodes)) throw new Error(`node "${name}" not stubbed`);
    return { item: { json: nodes[name] }, first: () => ({ json: nodes[name] }) };
  };
  const result = new Function('$json', '$', src)(json, $);
  return result.json;
}

// Deep copy of a fixture, so a test can change it without affecting the others.
function fixture(name) {
  const file = path.join(__dirname, '..', '..', 'fixtures', name);
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

module.exports = { runCodeNode, fixture };
