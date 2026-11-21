"""Oportunidades: isolamento de categoria, campos ausentes e cálculo simulado."""
import os,sys,tempfile
from pathlib import Path
from fastapi.testclient import TestClient
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend'))
with tempfile.TemporaryDirectory(prefix='dsi-opportunities-') as tmp:
 os.environ['DSI_DATABASE_PATH']=str(Path(tmp)/'test.db')
 import main
 c=TestClient(main.app)
 def add(pid,cat):
  r=c.post('/products',json={'title':f'Produto {pid}', 'url':f'https://www.aliexpress.com/item/{pid}.html','price':25,'currency':'BRL','category':cat,'review_count':15});assert r.status_code==200,r.text;return r.json()['id']
 a=add('100500123450001','Capas');b=add('100500123450002','Cabos')
 r=c.get('/intelligence/opportunities').json();assert len(r['products'])==2
 assert all(x['margin_pct'] is None for x in r['products'])
 payload={'shipping_brl':5,'sale_price_brl':80}
 r=c.put(f'/products/{a}/cost-analysis',json=payload);assert r.status_code==200,r.text
 r=c.get('/intelligence/opportunities',params={'category':'Capas'}).json();assert len(r['products'])==1
 item=r['products'][0];assert item['product_id']==a and item['margin_pct'] is not None and item['stress_profit_brl'] is not None
 assert item['estimated'] is True and item['cost_assumptions']
 assert c.get('/intelligence/opportunities',params={'category':'Cabos'}).json()['products'][0]['margin_pct'] is None
print('OK: ranking explicável, filtros por categoria, cenário e lacunas.')
