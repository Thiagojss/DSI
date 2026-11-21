"""Verifica bloqueio persistente de lotes com banco temporário; jamais usa data/dsi.db."""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
with tempfile.TemporaryDirectory(prefix="dsi-cooldown-") as folder:
    os.environ["DSI_DATABASE_PATH"] = str(Path(folder) / "test.db")
    from auth_test_client import TestClient
    from sqlalchemy import select
    import main
    from models import Product, PriceHistory

    client = TestClient(main.app)
    base = "https://www.aliexpress.com/w/wholesale-phone-case.html"
    def product(n, price=25):
        return {"title": f"Capa celular teste {n}", "url": f"https://www.aliexpress.com/item/{1005009000000000+n}.html", "price": price, "currency": "BRL"}
    def batch(items, url=base):
        resp = client.post("/collection-sessions", json={"source_url": url, "products": items})
        assert resp.status_code == 200, resp.text
        return resp.json()
    ids = [str(1005009000000000 + n) for n in range(1, 91)]
    all_new = client.post("/collection-eligibility", json={"product_ids": ids})
    assert all_new.status_code == 200 and all_new.json()["eligible_count"] == 90
    first = batch([product(n) for n in range(1, 41)])
    assert (first["saved_new"], first["skipped"]) == (40, 0), first
    eligibility = client.post("/collection-eligibility", json={"product_ids": ids}).json()
    assert eligibility["eligible_count"] == 50 and len(eligibility["blocked_ids"]) == 40, eligibility
    repeat = batch([product(1, price=1), product(2, price=1)], "https://www.aliexpress.com/w/wholesale-another-category.html")
    assert repeat["cooldown_skipped"] == 2 and repeat["saved_new"] == 0 and repeat["updated"] == 0, repeat
    with main.SessionLocal() as db:
        p = db.scalar(select(Product).where(Product.source_product_id == ids[0]))
        assert p.price == 25
        assert len(db.scalars(select(PriceHistory).where(PriceHistory.product_id == p.id)).all()) == 1
    second = batch([product(n) for n in range(41, 81)])
    assert second["saved_new"] == 40, second
    third = batch([product(n) for n in range(81, 91)])
    assert third["saved_new"] == 10, third
    eligibility = client.post("/collection-eligibility", json={"product_ids": ids}).json()
    assert eligibility["eligible_count"] == 0
    # Simula a passagem do prazo no banco temporário; não depende de esperar 24 horas reais.
    with main.SessionLocal() as db:
        p = db.scalar(select(Product).where(Product.source_product_id == ids[0]))
        p.last_batch_collected_at = datetime.now(timezone.utc) - timedelta(hours=24, minutes=1)
        db.commit()
    eligibility = client.post("/collection-eligibility", json={"product_ids": ids[:2]}).json()
    assert eligibility["eligible_count"] == 1 and eligibility["blocked_ids"] == [ids[1]], eligibility
    expired = batch([product(1, price=19)])
    assert expired["updated"] == 1 and expired["cooldown_skipped"] == 0, expired
    with main.SessionLocal() as db:
        p = db.scalar(select(Product).where(Product.source_product_id == ids[0]))
        assert p.price == 19
        assert len(db.scalars(select(PriceHistory).where(PriceHistory.product_id == p.id)).all()) == 2
    # Captura individual continua permitida durante o bloqueio do lote.
    manual = client.post("/products", json=product(2, price=15))
    assert manual.status_code == 200
    assert batch([product(2, price=5)])["cooldown_skipped"] == 1
    invalid = client.post("/collection-eligibility", json={"product_ids": ["1001", "malicious-id"]})
    assert invalid.status_code == 422
    print("OK: 90 itens em 3 lotes, 24h globais, filtragem, recaptura, histórico e captura individual.")
