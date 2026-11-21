const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const src = fs.readFileSync(path.join(__dirname,'../extension/popup/popup.js'),'utf8');
const token='cafe1234'.repeat(8);
const shared = new Map();
let online=true;
function launch({fallback=true,brokenNative=true}={}) {
  const elements=new Map();
  const el=(id)=>{
    if (!elements.has(id)) elements.set(id,{id,value:'',disabled:false,hidden:false,textContent:'',className:'',children:[],listeners:{},addEventListener(n,fn){this.listeners[n]=fn;},append(...a){this.children.push(...a);},replaceChildren(...a){this.children=a;}});
    return elements.get(id);
  };
  const browser={storage:{local:brokenNative?{
    async get(){throw Error('Extension storage unavailable')},
    async set(){throw Error('Extension storage unavailable')},
    async remove(){throw Error('Extension storage unavailable')}
  }:{ async get(k){return {[k]:shared.get('native:'+k)}}, async set(v){for(const [k,val] of Object.entries(v))shared.set('native:'+k,val)}, async remove(k){shared.delete('native:'+k)} }},tabs:{async query(){return []}}};
  const localStorage = fallback ? {
    getItem(k){return shared.get('local:'+k)??null},
    setItem(k,v){shared.set('local:'+k,v)},
    removeItem(k){shared.delete('local:'+k)}
  } : {getItem(){throw Error('storage disabled')},setItem(){throw Error('storage disabled')},removeItem(){throw Error('storage disabled')}};
  const ctx={browser,localStorage,document:{getElementById:el,createElement:t=>el('node-'+t+Math.random())},
    fetch:async(url,options)=>{
      if(!online)throw Error('offline');
      const auth=options.headers['X-DSI-Token']===token;
      const protectedRoute=!url.endsWith('/health');
      return {ok:!protectedRoute||auth,status:auth?200:401,json:async()=>!protectedRoute?{version:'1.0.2'}:auth?(url.includes('alerts')?[]:{}):{detail:'Pareamento necessário (401)'}};
    }, AbortController, setTimeout,clearTimeout,URL,Intl,console};
  vm.runInNewContext(src,ctx,{filename:'popup.js'});
  return {el};
}
const pause=()=>new Promise(r=>setTimeout(r,40));
(async()=>{
  let popup=launch();
  await pause();
  assert.match(popup.el('pair-status').textContent,/Não pareado/);
  assert.doesNotMatch(popup.el('pair-feedback').textContent,/Falha ao ler/);
  popup.el('pair-token').value=token;
  await popup.el('pair-save').listeners.click();
  assert.equal(shared.get('local:dsiPairingToken'),token);
  assert.equal(popup.el('pair-status').textContent,'Conectado');
  popup=launch(); await pause();
  assert.equal(popup.el('pair-status').textContent,'Conectado');
  assert.match(popup.el('pair-feedback').textContent,/alternativo/);
  online=false; popup=launch(); await pause();
  assert.match(popup.el('api-status').textContent,/Chave salva/);
  online=true;
  await popup.el('retry-button').listeners.click();
  assert.equal(popup.el('pair-status').textContent,'Conectado');
  await popup.el('pair-remove').listeners.click();
  assert.equal(shared.get('local:dsiPairingToken'),undefined);
  popup=launch(); await pause();
  assert.equal(popup.el('pair-status').textContent,'Não pareado');
  popup=launch({fallback:false}); await pause();
  popup.el('pair-token').value=token;
  await popup.el('pair-save').listeners.click();
  assert.equal(popup.el('pair-status').textContent,'Conectado','Chave pode funcionar na sessão mesmo sem persistência');
  assert.match(popup.el('pair-feedback').textContent,/não permitiu salvar/);
  popup=launch({fallback:false}); await pause();
  assert.equal(popup.el('pair-status').textContent,'Não pareado','Não fingir persistência quando ambos falham');
  console.log('OK: falha de storage.local, fallback, reabertura, offline, desconectar, ambos armazenamentos bloqueados');
})().catch(e=>{console.error(e);process.exitCode=1});
