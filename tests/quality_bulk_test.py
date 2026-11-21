"""Testes da v0.14 com banco temporário, sem tocar nos dados do usuário."""
import os, tempfile, sys
from pathlib import Path
with tempfile.TemporaryDirectory(prefix='dsi14-') as directory:
    os.environ['DSI_DATABASE_PATH'] = str(Path(directory)/'test.db')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
    from auth_test_client import TestClient
    import main
    c=TestClient(main.app)
    for i in range(2):
        r=c.post('/products',json={'url':f'https://www.aliexpress.com/item/10050099999999{i}.html','title':f'Capa celular {i}', 'category':'Celulares','price':25,'currency':'BRL','rating':4.5 if i==0 else None})
        assert r.status_code==200,r.text
    items=c.get('/products').json(); ids=[p['id'] for p in items]
    quality=c.get('/intelligence/collection-quality',params={'category':'Celulares'}).json()
    assert quality['total_products']==2
    fields={f['field']:f for f in quality['fields']}
    assert fields['price']['present']==2 and fields['rating']['present']==1
    assert fields['seller_name']['missing']==2
    bad=c.put('/products/organization/bulk',json={'product_ids':[ids[0],99999], 'apply_category':True,'manual_category':'Capas'});assert bad.status_code==404
    assert all(p['manual_category'] is None for p in c.get('/products').json())
    good=c.put('/products/organization/bulk',json={'product_ids':ids,'apply_category':True,'manual_category':'Capas','apply_color':True,'border_color':'#ABCDEF'})
    assert good.status_code==200,good.text
    assert all(p['category']=='Capas' and p['border_color']=='#abcdef' for p in c.get('/products').json())
    assert c.get('/intelligence/collection-quality',params={'category':'Capas'}).json()['total_products']==2
    assert c.put('/products/organization/bulk',json={'product_ids':ids,'apply_color':True,'border_color':None}).status_code==200
    assert all(p['border_color'] is None and p['category']=='Capas' for p in c.get('/products').json())
    assert c.put('/products/organization/bulk',json={'product_ids':[ids[0],ids[0]],'apply_color':True}).status_code==422
    print('OK: qualidade, categoria, edição atômica, validação e restauração.')
