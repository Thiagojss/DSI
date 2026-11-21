"""Teste isolado: limpeza confirma intenção, salva backup e preserva esquema."""
import os
import sys
import sqlite3
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
with tempfile.TemporaryDirectory(prefix='dsi-settings-') as tmp:
    path=Path(tmp)/'dsi.db'
    os.environ['DSI_DATABASE_PATH']=str(path)
    from fastapi.testclient import TestClient
    from sqlalchemy import select,func
    from database import SessionLocal, engine
    from models import Product,PriceHistory,PriceAlert,CollectionSession,CostScenario
    import main
    client=TestClient(main.app)
    assert client.get('/health').json()['version']=='0.18.0'
    assert client.post('/settings/clear-products',json={'confirmation':'apagar'}).status_code==422
    assert client.get('/settings/database').json()['products']==0
    with SessionLocal.begin() as db:
        p=Product(source='aliexpress',title='Celular',url='https://www.aliexpress.com/item/1005006666666666.html',manual_title='Meu celular',manual_category='Smartphones',is_favorite=True)
        db.add(p);db.flush()
        h=PriceHistory(product_id=p.id,price=9,currency='BRL');db.add(h);db.flush()
        db.add(PriceAlert(product_id=p.id,history_id=h.id,message='Mudou'))
        db.add(CostScenario(product_id=p.id,inputs_json='{}'))
        db.add(CollectionSession(source_url='https://www.aliexpress.com/w/wholesale-phone.html',total_found=1))
    before=client.get('/settings/database').json()
    assert all(value==1 for value in before.values()),before
    response=client.post('/settings/clear-products',json={'confirmation':'LIMPAR PRODUTOS'})
    assert response.status_code==200,response.text
    r=response.json()
    assert r['deleted']==before and r['database_preserved']
    backup=Path(r['backup_path']);assert backup.is_file() and backup.parent==path.parent/'backups'
    assert path.is_file() and all(v==0 for v in client.get('/settings/database').json().values())
    with sqlite3.connect(backup) as con:
        assert con.execute('select count(*) from products').fetchone()[0]==1
        assert con.execute('select count(*) from cost_scenarios').fetchone()[0]==1
    assert client.get('/products').json()==[]
    assert client.get('/intelligence/costs').json()['total']==0
    assert client.get('/collection-sessions').json()==[]
    assert client.get('/intelligence/radar').status_code==200
    assert client.post('/products',json={'title':'Novo','url':'https://www.aliexpress.com/item/1005007777777777.html'}).status_code==200
    assert client.get('/settings/database').json()['products']==1
    print('OK: confirmação, backup completo, exclusão relacionada, banco preservado e nova coleta.')
