"""Indicador de completude dos dados; não confundir com potencial comercial."""


def assess_data_quality(product: dict) -> dict:
    checks = {
        "title": bool(product.get("title")),
        "product_url": bool(product.get("source_product_id") and product.get("url")),
        "image": bool(product.get("image_url")),
        "price": product.get("price") is not None or product.get("price_min") is not None,
        "currency": bool(product.get("currency")),
        "rating": product.get("rating") is not None,
        "reviews": product.get("review_count") is not None,
        "orders": product.get("orders_count") is not None,
        "seller": bool(product.get("seller_name")),
        "category": bool(product.get("category")),
    }
    score = round(sum(checks.values()) / len(checks) * 100)
    missing = [key for key, present in checks.items() if not present]
    return {"data_quality": score, "data_completeness": checks, "missing_fields": missing}


def score_product(product: dict) -> dict:
    return {
        "score": None,
        "status": "awaiting_market_data",
        "reason": "A qualidade dos dados pode ser medida, mas a oportunidade comercial exige histórico de preço, demanda, concorrência e custos de operação.",
        **assess_data_quality(product),
    }
