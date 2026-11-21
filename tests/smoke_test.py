"""Teste de fumaça da API v0.4.0. Usa banco temporário; não toca em data/dsi.db."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
_temp = tempfile.TemporaryDirectory(prefix="dsi-test-")
os.environ["DSI_DATABASE_PATH"] = str(Path(_temp.name) / "test.db")

from fastapi.testclient import TestClient
import main

client = TestClient(main.app)
assert client.get("/health").status_code == 200

payload = {
    "title": "Produto de teste DSI",
    "url": "https://www.aliexpress.com/item/1005001234567890.html",
    "price": 20.0,
    "currency": "USD",
    "rating": 4.8,
    "review_count": 100,
    "seller_name": "Loja de teste",
}
created = client.post("/products", json=payload)
assert created.status_code == 200, created.text
product_id = created.json()["id"]
assert len(client.get(f"/products/{product_id}/history").json()) == 1

payload["price"] = 15.0
updated = client.post("/products", json=payload)
assert updated.status_code == 200 and updated.json()["updated"] is True
history = client.get(f"/products/{product_id}/history").json()
assert len(history) == 2
alerts = client.get("/alerts?unread_only=true").json()
assert len(alerts) == 1 and alerts[0]["change_percent"] == -25.0
assert client.put(f"/alerts/{alerts[0]['id']}/read").status_code == 200
assert client.get("/monitoring/summary").json()["unread_alerts"] == 0
# Captura sem alteração deve acrescentar observação, mas não duplicar alerta.
client.post("/products", json=payload)
assert len(client.get("/alerts").json()) == 1
# Mudança somente na faixa de variantes gera alerta próprio, sem percentual enganoso.
payload["price_min"] = 12.0
payload["price_max"] = 18.0
client.post("/products", json=payload)
latest_alerts = client.get("/alerts").json()
assert latest_alerts[0]["alert_type"] == "price_range_changed"
assert latest_alerts[0]["change_percent"] is None
assert client.post("/products", json={**payload, "url": "https://www.aliexpress.com/category/123.html"}).status_code == 422
print("OK: saúde, cadastro, histórico, alerta, leitura de alerta e validação de URL.")
_temp.cleanup()
