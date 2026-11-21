"""Conversão indicativa para BRL usando taxas públicas do Frankfurter (referência BCE)."""
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen
from urllib.error import URLError
import json

# Taxa indicativa de contingência baseada na referência publicada em 20/11/2026.
FALLBACK_USD_BRL = 5.93803
_CACHE = {}
_CACHE_TTL = timedelta(hours=1)


def get_rate_to_brl(currency: str):
    code = (currency or "").upper().strip()
    if code == "BRL":
        return {"currency": "BRL", "rate": 1.0, "date": datetime.now(timezone.utc).date().isoformat(), "source": "paridade", "is_fallback": False}
    if len(code) != 3 or not code.isalpha():
        return None
    now = datetime.now(timezone.utc)
    cached = _CACHE.get(code)
    if cached and now - cached["cached_at"] < _CACHE_TTL:
        return cached["value"]
    try:
        url = f"https://api.frankfurter.app/latest?from={code}&to=BRL"
        with urlopen(url, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
        rate = float(payload["rates"]["BRL"])
        value = {"currency": code, "rate": rate, "date": payload.get("date"), "source": "Frankfurter / BCE", "is_fallback": False}
        _CACHE[code] = {"cached_at": now, "value": value}
        return value
    except (URLError, TimeoutError, ValueError, KeyError, OSError):
        if code == "USD":
            value = {"currency": "USD", "rate": FALLBACK_USD_BRL, "date": "2026-11-20", "source": "taxa de contingência (referência BCE)", "is_fallback": True}
            return value
        return None
