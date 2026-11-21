"""Pesquisa: backup aditivo, decisões, paginação, validação e reset seguro."""
import os,sys,tempfile,sqlite3
from pathlib import Path
from auth_test_client import TestClient
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend'))
with tempfile.TemporaryDirectory(prefix='dsi-research-') as d:
    dbpath=Path(d)/'dsi.db'
    # Banco da versão anterior simulado com todas as colunas preexistentes,
    # mas sem a nova tabela de decisões.
    os.environ['DSI_DATABASE_PATH']=str(dbpath)
    import database, models
    database.Base.metadata.create_all(bind=database.engine)
    with sqlite3.connect(dbpath) as conn:
        conn.execute('DROP TABLE research_decisions')
        conn.execute("INSERT INTO products(id,url,title,source,data_quality,is_favorite,created_at,updated_at) VALUES (1,'https://www.aliexpress.com/item/100500123456789.html','Legado','aliexpress',0,0,'2026-11-20 10:00:00','2026-11-20 10:00:00')")
    import main
    from models import ResearchDecision
    client=TestClient(main.app)
    backups=list((Path(d)/'backups').glob('dsi-before-v0.19*'))
    assert backups, 'Backup pré-migração ausente'
    with sqlite3.connect(backups[0]) as old:
        assert old.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='research_decisions'").fetchone() is None
        assert old.execute("SELECT title FROM products WHERE id=1").fetchone()[0]=='Legado'
    first=client.get('/intelligence/research').json()
    assert first['total']==1 and first['products'][0]['stage']=='nao_avaliado',first
    pid=1
    assert client.put(f'/products/{pid}/research',json={'stage':'aprovado','priority':'alta','notes':'Confirmar a amostra'}).status_code==200
    assert client.put(f'/products/{pid}/research',json={'stage':'inventado','notes':'oi'}).status_code==422
    assert client.put('/products/90000/research',json={'stage':'testar'}).status_code==404
    saved=client.get('/intelligence/research',params={'stage':'aprovado'}).json()
    assert saved['total']==1 and saved['products'][0]['notes']=='Confirmar a amostra'
    assert client.get('/intelligence/research',params={'stage':'nao_avaliado'}).json()['total']==0
    ids=[]
    for i in range(3):
        r=client.post('/products',json={'title':f'Cabo Teste {i}','url':f'https://www.aliexpress.com/item/{100500123457000+i}.html','category':'Cabos','seller_url':'https://www.aliexpress.com/store/110000001','seller_rating':4.8,'seller_name':'Loja A','price':25,'currency':'BRL'})
        assert r.status_code==200,r.text
        ids.append(r.json()['id'])
    page1=client.get('/intelligence/research',params={'limit':2,'offset':0}).json()
    page2=client.get('/intelligence/research',params={'limit':2,'offset':2}).json()
    assert page1['total']==4 and page2['total']==4
    assert len(set(p['product_id'] for p in page1['products']+page2['products']))==4
    assert client.get('/intelligence/research',params={'category':'Cabos'}).json()['total']==3
    suppliers=client.get('/intelligence/suppliers',params={'category':'Cabos'}).json()
    assert suppliers['total_suppliers']==1 and suppliers['suppliers'][0]['products']==3
    assert suppliers['suppliers'][0]['seller_rating_min']==4.8
    export=client.get('/intelligence/research.csv')
    assert export.status_code==200 and 'Confirmar a amostra' in export.text
    assert client.get('/intelligence/research.csv',params={'stage':'invalido'}).status_code==422
    assert client.get('/settings/database').json()['research_decisions']==1
    clean=client.post('/settings/clear-products',json={'confirmation':'LIMPAR PRODUTOS'})
    assert clean.status_code==200,clean.text
    assert clean.json()['deleted']['research_decisions']==1
    assert client.get('/intelligence/research').json()['total']==0
    with sqlite3.connect(dbpath) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='research_decisions'").fetchone()
print('OK: migração e backup, decisões, paginação, agrupamento, exclusão segura')
