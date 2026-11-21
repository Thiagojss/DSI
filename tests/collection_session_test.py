"""Testa sessões em lote com banco temporário, sem tocar em data/dsi.db."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
_temp = tempfile.TemporaryDirectory(prefix="dsi-collection-")
os.environ["DSI_DATABASE_PATH"] = str(Path(_temp.name) / "collection.db")

from fastapi.testclient import TestClient
import main

client = TestClient(main.app)
assert client.get("/health").json()["version"] == "0.18.0"

base = {
    "title": "Luminária LED de teste",
    "url": "https://www.aliexpress.com/item/1005001234500011.html",
    "price": 19.9,
    "currency": "USD",
    "image_url": "https://ae01.alicdn.com/kf/test.jpg",
}
response = client.post("/collection-sessions", json={
    "source_url": "https://www.aliexpress.com/w/wholesale-led-lamp.html",
    "products": [base, {**base, "title": "Luminária LED atualizada", "price": 17.5}],
})
assert response.status_code == 200, response.text
result = response.json()
assert result["total_found"] == 2
assert result["saved_new"] == 1 and result["updated"] == 0 and result["skipped"] == 1
assert result["status"] == "partial"
products = client.get("/products?limit=20").json()
assert len(products) == 1 and products[0]["title"] == "Luminária LED de teste"
history = client.get(f"/products/{products[0]['id']}/history").json()
assert len(history) == 1
sessions = client.get("/collection-sessions").json()
assert len(sessions) == 1 and sessions[0]["saved_new"] == 1 and sessions[0]["updated"] == 0
invalid = client.post("/collection-sessions", json={
    "source_url": "https://example.com/search", "products": [base]
})
assert invalid.status_code == 422
partial = client.post("/collection-sessions", json={
    "source_url": "https://www.aliexpress.com/w/wholesale-led-lamp.html",
    "products": [{**base, "url": "https://www.aliexpress.com/category/123.html"}],
})
assert partial.status_code == 200, partial.text
assert partial.json()["status"] == "empty" and partial.json()["skipped"] == 1

# Uma falha isolada em um item não deve interromper o restante do lote.
from sqlalchemy.exc import SQLAlchemyError
original_upsert = main.upsert_product
def flaky_upsert(db, item):
    if item.title == "Falha simulada":
        raise SQLAlchemyError("falha simulada")
    return original_upsert(db, item)
main.upsert_product = flaky_upsert
isolated = client.post("/collection-sessions", json={
    "source_url": "https://www.aliexpress.com/w/wholesale-led-lamp.html",
    "products": [
        {**base, "title": "Falha simulada", "url": "https://www.aliexpress.com/item/1005001234500012.html"},
        {**base, "title": "Luminária preservada", "url": "https://www.aliexpress.com/item/1005001234500013.html"},
    ],
})
assert isolated.status_code == 200, isolated.text
assert isolated.json()["skipped"] == 1 and isolated.json()["saved_new"] == 1
assert any(p["title"] == "Luminária preservada" for p in client.get("/products?limit=20").json())
main.upsert_product = original_upsert

print("OK: lote, bloqueio de duplicatas, histórico, isolamento de falhas, rejeição de origem e registro de itens ignorados.")
_temp.cleanup()
