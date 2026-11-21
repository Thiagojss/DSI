const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const source = fs.readFileSync('extension/scripts/content.js', 'utf8');
const links = [];
function link(n) {
  const id = String(1005009000000000 + n);
  const picture = {currentSrc: 'https://ae01.alicdn.com/test.jpg', src: 'https://ae01.alicdn.com/test.jpg', getAttribute: () => `Capa modelo celular ${n}`};
  const card = {
    innerText: `Capa modelo celular ${n}\nR$ ${10+n},00\n★ 4,8\n120 reviews`,
    querySelector: (selector) => selector === 'img' ? picture : null,
    querySelectorAll: () => [], parentElement: null,
  };
  return { href:`https://www.aliexpress.com/item/${id}.html`, getAttribute: key => key === 'title' ? `Capa modelo celular ${n}` : null,
    innerText: `Capa modelo celular ${n}`, parentElement: card };
}
for(let n=1;n<=90;n++) links.push(link(n));
const sandbox = {
 document: {querySelectorAll: selector => selector === 'a[href*="/item/"]' ? links : [], querySelector: () => null},
 location: { href:'https://www.aliexpress.com/w/wholesale-case.html', hostname:'www.aliexpress.com' },
 browser:{runtime:{onMessage:{addListener(fn){ sandbox.messageHandler = fn; }}}}
};
vm.runInNewContext(source, sandbox);
(async () => {
 const result = await sandbox.messageHandler({action:'DSI_COLLECT_LISTING'});
 assert.equal(result.products.length,90);
 assert.equal(new Set(result.products.map(p=>p.source_product_id)).size,90);
 assert.equal(result.products[89].source_product_id,String(1005009000000090));
 console.log('OK: leitor percorre 90 cards no DOM e envia IDs explícitos, sem corte aos 40.');
})().catch(e => {console.error(e);process.exitCode=1});
