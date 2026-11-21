"""Beta final: verificações persistentes, inclusão de oportunidades, migração, limpeza e paginação."""
import os,sys,tempfile,sqlite3
from pathlib import Path
from auth_test_client import TestClient
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend'))
with tempfile.TemporaryDirectory(prefix='dsi-beta-') as tmp:
    dbpath=Path(tmp)/'dsi.db'
    os.environ['DSI_DATABASE_PATH']=str(dbpath)
    import database,models
    database.Base.metadata.create_all(bind=database.engine)
    with sqlite3.connect(dbpath) as con:
        con.execute('DROP TABLE research_checks')
        con.execute("INSERT INTO products(id,url,title,source,data_quality,is_favorite,created_at,updated_at,category) VALUES (1,'https://www.aliexpress.com/item/100500123456789.html','Legado','aliexpress',0,0,'2026-11-20 10:00:00','2026-11-20 10:00:00','Capas')")
    import main
    client=TestClient(main.app)
    assert client.get('/health').json()['version']=='1.0.2'
    backups=list((Path(tmp)/'backups').glob('dsi-before-v0.20*'))
    assert backups
    with sqlite3.connect(backups[0]) as conn:
        assert conn.execute("select count(*) from products").fetchone()[0]==1
        assert conn.execute("select name from sqlite_master where name='research_checks'").fetchone() is None
    pid=1
    r=client.get(f'/products/{pid}/research-checks');assert r.status_code==200
    d=r.json();assert d['total']==4 and d['confirmed']==0 and len(d['checks'])==4
    r=client.put(f'/products/{pid}/research-checks',json={'checks':[
        {'kind':'fornecedor','status':'confirmado','evidence':'Consulta manual em 2026-11-21'},
        {'kind':'custos','status':'bloqueado','evidence':'Falta cotação de frete'}]})
    assert r.status_code==200,r.text
    assert r.json()['confirmed']==1
    r=client.get('/intelligence/research',params={'category':'Capas'}).json()
    assert r['products'][0]['checklist_confirmed']==1
    assert client.put(f'/products/{pid}/research-checks',json={'checks':[{'kind':'fornecedor','status':'inventado'}]}).status_code==422
    assert client.put(f'/products/{pid}/research-checks',json={'checks':[{'kind':'fornecedor','status':'confirmado'},{'kind':'fornecedor','status':'confirmado'}]}).status_code==422
    assert client.put('/products/999999/research-checks',json={'checks':[{'kind':'fornecedor','status':'confirmado'}]}).status_code==404
    assert client.get('/settings/database').json()['research_checks']==2
    with sqlite3.connect(dbpath) as conn:
        assert conn.execute("select status from research_checks where kind='custos'").fetchone()[0]=='bloqueado'
    # Filtering categories before limit: chosen category can be beyond the most recent item
    add=client.post('/products',json={'title':'Outro produto','url':'https://www.aliexpress.com/item/100500123459999.html','category':'Cabos'})
    assert add.status_code==200
    opportunity=client.get('/intelligence/opportunities',params={'category':'Capas','limit':1}).json()
    assert opportunity['returned']==1 and opportunity['products'][0]['product_id']==1 and opportunity['total_catalog']==1
    assert opportunity['products'][0]['research_stage']=='nao_avaliado'
    assert client.put(f'/products/{pid}/research',json={'stage':'testar','priority':'alta','notes':'Amostra solicitada'}).status_code==200
    assert client.get('/intelligence/opportunities',params={'category':'Capas'}).json()['products'][0]['research_stage']=='testar'
    before=client.get('/settings/database').json()
    result=client.post('/settings/clear-products',json={'confirmation':'LIMPAR PRODUTOS'})
    assert result.status_code==200,result.text
    assert result.json()['deleted']==before
    assert client.get('/settings/database').json()['research_checks']==0
    assert client.get(f'/products/{pid}/research-checks').status_code==404
    assert client.post('/products',json={'title':'Novo após limpeza','url':'https://www.aliexpress.com/item/100500123456799.html'}).status_code==200
print('OK: migração, checklists, evidências, validação, filtro antes do limite e limpeza.')
