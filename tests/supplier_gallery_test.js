const fs=require('fs'), vm=require('vm'), assert=require('assert/strict');
const source=fs.readFileSync('extension/scripts/content.js','utf8');
const meta={
 'meta[property="og:title"]':'Produto câmera avançada',
 'meta[property="og:image"]':'https://ae01.alicdn.com/main.jpg',
 'meta[property="product:price:amount"]':'19.90',
 'meta[property="product:price:currency"]':'USD'
};
const gallery=[{currentSrc:'https://ae01.alicdn.com/second.jpg',getAttribute:()=>null}, {currentSrc:'https://ae01.alicdn.com/third.jpg',getAttribute:()=>null}];
const sellerLink={href:'https://www.aliexpress.com/store/1001'};
const document={
  scripts:[],documentElement:{lang:'en'}, body:{innerText:''},
  querySelector(selector){
    if(meta[selector])return {getAttribute:()=>meta[selector]};
    if(selector.includes('store-rating'))return {textContent:'4.8 / 5',getAttribute:()=>null};
    if(selector.includes('positive-feedback'))return {textContent:'97.4%'};
    if(selector.includes('store-name'))return {textContent:'Loja Casa'};
    return null;
  },
  querySelectorAll(selector){
    if(selector==='script[type="application/ld+json"]')return [];
    if(selector.includes('[class*="image-view"'))return gallery;
    if(selector.includes('a[href*="/store/"]'))return [sellerLink];
    return [];
  }
};
const sandbox={URL,document,location:{href:'https://www.aliexpress.com/item/1005009000000123.html',hostname:'www.aliexpress.com'},browser:{runtime:{onMessage:{addListener(f){sandbox.onMessage=f}}}}};
vm.runInNewContext(source,sandbox);
(async()=>{
 const product=await sandbox.onMessage({action:'DSI_PREVIEW_PRODUCT'});
 assert.equal(product.seller_url,sellerLink.href);
 assert.equal(product.seller_rating,4.8);
 assert.equal(product.seller_positive_feedback_pct,97.4);
 assert.equal(product.image_urls.length,3);
 assert.equal(product.image_urls[0],meta['meta[property="og:image"]']);
 console.log('OK: galeria de 3 imagens, link da loja, nota e feedback do fornecedor distintos do produto.');
})().catch(e=>{console.error(e);process.exitCode=1});
