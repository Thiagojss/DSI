from pathlib import Path
import os
from sqlalchemy import create_engine, inspect, text
import re
from sqlalchemy.orm import declarative_base, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_PATH = Path(os.environ.get("DSI_DATABASE_PATH", str(DATA_DIR / "dsi.db"))).expanduser().resolve()
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def migrate_schema():
    """Additive SQLite migration; preserves products already collected in v0.1."""
    inspector = inspect(engine)
    if "products" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("products")}
    additions = {
        "source_product_id": "VARCHAR(80)", "category": "VARCHAR(300)",
        "category_path": "TEXT", "price_min": "FLOAT", "price_max": "FLOAT",
        "orders_count": "INTEGER", "availability": "VARCHAR(40)",
        "data_quality": "INTEGER NOT NULL DEFAULT 0", "capture_warnings": "TEXT",
    }
    with engine.begin() as connection:
        for name, sql_type in additions.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE products ADD COLUMN {name} {sql_type}"))
        # Backfill identity for rows collected by v0.1, so a recapture updates
        # the existing row instead of creating a duplicate.
        rows = connection.execute(text("SELECT id, url FROM products WHERE source_product_id IS NULL")).all()
        for row_id, url in rows:
            match = re.search(r"/item/(?:[^/]+/)?(\d+)(?:\.html)?(?:[/?#]|$)", url or "", re.I)
            if match:
                product_id = match.group(1)
                canonical = f"https://www.aliexpress.com/item/{product_id}.html"
                conflict = connection.execute(text("SELECT id FROM products WHERE url = :url AND id != :id"), {"url": canonical, "id": row_id}).first()
                if not conflict:
                    connection.execute(text("UPDATE products SET source_product_id = :pid, url = :url WHERE id = :id"), {"pid": product_id, "url": canonical, "id": row_id})
        # Numeric legacy columns are converted by SQLAlchemy's Float/Integer result processors.
