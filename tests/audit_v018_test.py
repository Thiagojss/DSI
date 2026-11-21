"""Verifica novos campos, regras de segurança do navegador e ferramentas do banco."""
import os, sys, tempfile, sqlite3, csv, io
from pathlib import Path
from auth_test_client import TestClient
ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    dbpath = Path(tmp)/'dsi.db'
    os.environ['DSI_DATABASE_PATH'] = str(dbpath)
    sys.path.insert(0,str(ROOT/'backend'))
    import main
    client=TestClient(main.app)
    assert client.get('/health').json()['version']=='1.0.0'
    payload={'title':'Capa X','url':'https://www.aliexpress.com/item/1005001234567890.html',
             'image_url':'https://ae01.alicdn.com/a.jpg','image_urls':['https://ae01.alicdn.com/a.jpg','https://ae01.alicdn.com/b.jpg'],
             'seller_name':'Loja X','seller_url':'https://www.aliexpress.com/store/123456',
             'seller_rating':4.7,'seller_positive_feedback_pct':96.5}
    r=client.post('/products',json=payload);assert r.status_code==200,r.text
    product=client.get('/products')[0] if False else client.get('/products').json()[0]
    assert len(product['image_urls'])==2 and product['seller_rating']==4.7 and product['seller_positive_feedback_pct']==96.5
    # Captura posterior parcial não substitui galeria nem dados da loja.
    p={'title':'Capa X','url':payload['url'],'image_urls':['https://ae01.alicdn.com/c.jpg']}
    assert client.post('/products',json=p).status_code==200
    product=client.get('/products').json()[0]
    assert len(product['image_urls'])==3 and product['seller_url']==payload['seller_url']
    bad={**payload,'seller_url':'https://bad.example/store/123'}
    assert client.post('/products',json=bad).status_code==422
    blocked=client.post('/products',json=payload,headers={'Origin':'https://malicious.example'})
    assert blocked.status_code==403,blocked.text
    assert client.post('/products',json=payload,headers={'Origin':'moz-extension://1234-abcd'}).status_code==200
    integrity=client.get('/settings/integrity'); assert integrity.status_code==200 and integrity.json()['healthy']
    assert client.post('/settings/backup',json={'confirmation':'errado'}).status_code==422
    b=client.post('/settings/backup',json={'confirmation':'CRIAR BACKUP'});assert b.status_code==200,b.text
    assert Path(b.json()['path']).exists()
    with sqlite3.connect(b.json()['path']) as c: assert c.execute('SELECT count(*) FROM products').fetchone()[0]==1
    ex=client.get('/settings/export-products.csv');assert ex.status_code==200
    rows=list(csv.DictReader(io.StringIO(ex.content.decode('utf-8-sig'))));assert len(rows)==1 and rows[0]['seller_rating']=='4.7'
    # Formula in product title: export should escape spreadsheet formula.
    payload['title']='=HYPERLINK("https://bad.example")'
    assert client.post('/products',json=payload).status_code==200
    ex=client.get('/settings/export-products.csv').content.decode('utf-8-sig')
    assert "'=HYPERLINK" in ex
    print('OK: galeria persistente, dados da loja, origem bloqueada, integridade, backup e CSV seguro.')
