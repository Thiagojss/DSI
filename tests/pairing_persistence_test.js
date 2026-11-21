// Simula dois ciclos completos do popup com o mesmo storage.local do Firefox.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../extension/popup/popup.js'), 'utf8');
const token = 'abcdef0123456789'.repeat(4);
const store = {};
let online = true;
let validToken = token;
const wait = () => new Promise(resolve => setTimeout(resolve, 25));
function startPopup() {
  const nodes = new Map();
  function elem(id) {
    if (!nodes.has(id)) nodes.set(id, {
      id, value: '', textContent: '', className: '', hidden: false, disabled: false,
      children: [], listeners: {}, addEventListener(name, cb) { this.listeners[name] = cb; },
      append(...args) { this.children.push(...args); }, replaceChildren(...args) { this.children = args; },
    });
    return nodes.get(id);
  }
  const browser = {
    storage: { local: {
      async get(name) { return { [name]: store[name] }; },
      async set(item) { Object.assign(store, item); },
      async remove(name) { delete store[name]; }
    }},
    tabs: { async query() { return []; } }
  };
  const ctx = {
    browser, document: { getElementById: elem, createElement: (tag) => elem(`created-${tag}-${Math.random()}`) },
    fetch: async (url, config) => {
      if (!online) throw Error('Failed to fetch');
      const isProtected = !url.endsWith('/health');
      const authorized = config.headers['X-DSI-Token'] === validToken;
      return { ok: !isProtected || authorized, status: authorized ? 200 : 401,
        json: async () => !isProtected ? { version: '1.0.2' } : authorized ? (url.includes('alerts') ? [] : {}) : { detail: 'Pareamento necessário (401)' }
      };
    },
    AbortController, setTimeout, clearTimeout, URL, Intl, console,
  };
  vm.runInNewContext(source, ctx, { filename: 'popup.js' });
  return { elem };
}
(async () => {
  let popup = startPopup();
  await wait();
  assert.match(popup.elem('pair-status').textContent, /Não pareado/);
  popup.elem('pair-token').value = token;
  await popup.elem('pair-save').listeners.click();
  assert.equal(store.dsiPairingToken, token, 'Chave precisa ser gravada');
  assert.equal(popup.elem('pair-status').textContent, 'Conectado');

  popup = startPopup(); // fecha e reabre sem perder storage.local
  await wait();
  assert.equal(popup.elem('pair-status').textContent, 'Conectado');
  assert.equal(popup.elem('pair-token').value, '');

  online = false;
  popup = startPopup();
  await wait();
  assert.equal(store.dsiPairingToken, token, 'Offline não deve apagar chave');
  assert.match(popup.elem('api-status').textContent, /Chave salva/);

  online = true;
  await popup.elem('retry-button').listeners.click();
  assert.equal(popup.elem('pair-status').textContent, 'Conectado', 'Reconectar usa chave salva');

  validToken = '1'.repeat(64);
  popup = startPopup();
  await wait();
  assert.equal(store.dsiPairingToken, token, 'Chave recusada não deve ser apagada');
  assert.match(popup.elem('api-status').textContent, /não aceita/);

  await popup.elem('pair-remove').listeners.click();
  assert.equal(store.dsiPairingToken, undefined, 'Só Desconectar remove chave');
  popup = startPopup();
  await wait();
  assert.equal(popup.elem('pair-status').textContent, 'Não pareado');
  console.log('OK: armazenamento, reabertura, offline, reconexão, troca da chave e desconexão.');
})().catch(error => { console.error(error); process.exitCode = 1; });
