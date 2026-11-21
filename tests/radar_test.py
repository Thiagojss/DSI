"""Regressão de captura parcial e radar. SQLite temporário, banco real intocado."""
import os
import sys
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend'))
with tempfile.TemporaryDirectory() as tmp:
    os.environ['DSI_DATABASE_PATH'] = str(Path(tmp)/'test.db')
    import main
    client=TestClient(main.app)
    full={'title':'Produto XYZ teste', 'url':'https://www.aliexpress.com/item/100500999888777.html',
          'category':'Eletrônicos', 'seller_name':'Fornecedor confirmado', 'price':29,
          'currency':'BRL','rating':4.7,'review_count':195,'orders_count':1000}
    a=client.post('/products',json=full)
    assert a.status_code==200,a.text
    partial={'title':'Produto XYZ teste','url':full['url'],'rating':4.8,'review_count':240}
    b=client.post('/collection-sessions',json={'source_url':'https://www.aliexpress.com/w/wholesale-example.html','products':[partial]})
    assert b.status_code==200,b.text
    out=client.get('/intelligence/radar').json()
    assert out['total_catalog']==1 and out['returned']==1 and not out['truncated']
    product=out['products'][0]
    assert product['rating']==4.8 and product['review_count']==240
    assert product['price']==29 and product['currency']=='BRL' and product['orders_count']==1000
    assert product['seller_name']=='Fornecedor confirmado' and product['category']=='Eletrônicos'
    assert product['data_quality'] >= 80
    assert len(client.get(f"/products/{product['id']}/history").json())==1, 'não criar histórico fictício por captura sem preço'
    print('OK: radar e preservação dos campos na captura parcial.')
