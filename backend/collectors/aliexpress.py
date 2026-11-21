"""Normalização e validação dos dados capturados pelo content script."""
import re
from urllib.parse import urlsplit, urlunsplit

PRODUCT_PATH = re.compile(r"^/item/(?:[^/]+/)?(\d+)(?:\.html)?/?$", re.I)


def identify_product_url(raw_url: str):
    parts = urlsplit(raw_url or "")
    host = (parts.hostname or "").lower()
    if not (host == "aliexpress.com" or host.endswith(".aliexpress.com")):
        return None
    match = PRODUCT_PATH.match(parts.path)
    if not match:
        return None
    product_id = match.group(1)
    canonical = urlunsplit(("https", "www.aliexpress.com", f"/item/{product_id}.html", "", ""))
    return product_id, canonical


def normalize_product(raw: dict) -> dict:
    identity = identify_product_url(str(raw.get("url") or ""))
    if not identity:
        raise ValueError("A URL não corresponde a uma página individual de produto do AliExpress.")
    product_id, canonical_url = identity
    title = re.sub(r"\s+", " ", str(raw.get("title") or "")).strip()
    if not title or title.lower() in {"aliexpress", "aliexpress.com"}:
        raise ValueError("Não foi possível identificar o título do produto.")
    return {
        **raw,
        "source": "aliexpress",
        "source_product_id": product_id,
        "title": title[:1000],
        "url": canonical_url,
    }
