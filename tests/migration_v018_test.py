"""Banco anterior recebe colunas novas mantendo dados e backup íntegro."""
import tempfile,sqlite3,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)/'dsi.db'
    with sqlite3.connect(p) as db:
        db.execute('CREATE TABLE products (id INTEGER PRIMARY KEY, source VARCHAR(40), title VARCHAR(1000), url VARCHAR(2048), source_product_id VARCHAR(80), last_batch_collected_at DATETIME)')
        db.execute("INSERT INTO products(id,source,title,url,source_product_id) VALUES (1,'aliexpress','Legado','https://www.aliexpress.com/item/1005001234567890.html','1005001234567890')")
    os.environ['DSI_DATABASE_PATH']=str(p)
    sys.path.insert(0,str(ROOT/'backend'))
    import main
    from database import engine
    from sqlalchemy import inspect
    cols={x['name'] for x in inspect(engine).get_columns('products')}
    assert {'image_urls_json','seller_url','seller_rating','seller_positive_feedback_pct'}.issubset(cols)
    with sqlite3.connect(p) as db:
        assert db.execute('SELECT title FROM products WHERE id=1').fetchone()[0]=='Legado'
    backups=list((p.parent/'backups').glob('dsi-before-v0.18-*.db'))
    assert len(backups)==1,backups
    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute('SELECT title FROM products WHERE id=1').fetchone()[0]=='Legado'
        assert 'image_urls_json' not in {row[1] for row in backup.execute('PRAGMA table_info(products)')}
    print('OK: banco legado preservado, migração aditiva e backup anterior consistente.')
