"""Confirma migração aditiva em banco legado, preservando registro existente."""
import os
import sqlite3
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="dsi-legacy-") as folder:
    db_path = Path(folder) / "legacy.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, url VARCHAR(2048) NOT NULL)")
        connection.execute("INSERT INTO products (id, url) VALUES (7, 'https://www.aliexpress.com/item/1005001234567890.html')")
    os.environ["DSI_DATABASE_PATH"] = str(db_path)
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
    from database import engine, migrate_schema
    migrate_schema()
    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(products)")}
        row = connection.execute("SELECT id, url, is_favorite FROM products WHERE id=7").fetchone()
        indexes = {item[1] for item in connection.execute("PRAGMA index_list(products)")}
    assert "is_favorite" in columns
    assert "ix_products_is_favorite" in indexes
    assert row == (7, "https://www.aliexpress.com/item/1005001234567890.html", 0)
print("OK: migração adiciona is_favorite sem apagar ou alterar produtos existentes.")
