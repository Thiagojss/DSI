"""Personalização independente de capturas; SQLite isolado em diretório temporário."""
import os
import sys
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, text, inspect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
with tempfile.TemporaryDirectory(prefix='dsi-org-') as tmp:
    path = Path(tmp) / 'test.db'
    # Cria estrutura equivalente à versão anterior: remove apenas as novas colunas.
    os.environ['DSI_DATABASE_PATH'] = str(path)
    from database import Base, engine
    import models
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE products DROP COLUMN manual_title'))
        conn.execute(text('DROP INDEX IF EXISTS ix_products_manual_category'))
        conn.execute(text('ALTER TABLE products DROP COLUMN manual_category'))
        conn.execute(text('ALTER TABLE products DROP COLUMN border_color'))
        conn.execute(text("INSERT INTO products (id,source,title,url,category,data_quality,is_favorite,created_at,updated_at) VALUES (1,'aliexpress','Capa original','https://www.aliexpress.com/item/1005008888888888.html','Celulares',0,0,'2026-11-21','2026-11-21')"))
    from fastapi.testclient import TestClient
    import main
    from database import engine
    assert {'manual_title', 'manual_category', 'border_color'} <= {x['name'] for x in inspect(engine).get_columns('products')}
    c = TestClient(main.app)
    original = c.get('/products/1').json()
    assert original['source_title'] == 'Capa original' and original['source_category'] == 'Celulares'
    edited = c.put('/products/1/organization', json={'manual_title':'Capa premium', 'manual_category':'Capas para celular', 'border_color':'#3B82F6'})
    assert edited.status_code == 200, edited.text
    assert edited.json()['title']=='Capa premium' and edited.json()['category']=='Capas para celular'
    assert edited.json()['border_color']=='#3b82f6'
    assert c.get('/categories').json() == [{'name':'Capas para celular'}]
    assert len(c.get('/products', params={'category':'Capas para celular'}).json())==1
    assert len(c.get('/products', params={'search':'premium'}).json())==1
    assert c.get('/stats').json()['categories']['Capas para celular']==1
    radar = c.get('/intelligence/radar').json()['products'][0]
    assert radar['title']=='Capa premium' and radar['category']=='Capas para celular'
    assert c.put('/products/1/organization', json={'border_color':'red'}).status_code==422
    assert c.put('/products/1/organization', json={'manual_title':'X'*181}).status_code==422
    assert c.put('/products/5000/organization', json={}).status_code==404
    # Captura atualiza fonte, não apaga a curadoria.
    capture = c.post('/products', json={'url':'https://www.aliexpress.com/item/1005008888888888.html','title':'Capa original, novo título','category':'Eletrônicos','price':39.9,'currency':'BRL'})
    assert capture.status_code==200, capture.text
    after = c.get('/products/1').json()
    assert (after['title'],after['source_title'],after['category'],after['source_category'],after['border_color']) == ('Capa premium','Capa original, novo título','Capas para celular','Eletrônicos','#3b82f6')
    assert len(c.get('/products').json())==1
    assert c.get('/categories').json() == [{'name':'Capas para celular'}]
    assert c.get('/intelligence/costs').status_code==200
    reset = c.put('/products/1/organization', json={})
    assert reset.status_code==200 and reset.json()['category']=='Eletrônicos' and reset.json()['title']=='Capa original, novo título'
    assert reset.json()['border_color'] is None
    assert c.get('/stats').json()['categories']['Eletrônicos']==1
    print('OK: migração legada, personalização, filtros, radar, estatísticas, preservação após recaptura e restauração.')
