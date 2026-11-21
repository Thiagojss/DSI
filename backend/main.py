from datetime import datetime, timezone
from typing import Optional
import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from sqlalchemy import select, or_, desc

from database import Base, engine, SessionLocal, migrate_schema
from models import Product, PriceHistory, PriceAlert
from collectors.aliexpress import normalize_product
from analyzers.scoring import assess_data_quality
from fx import get_rate_to_brl
from dashboard import dashboard_page

migrate_schema()
Base.metadata.create_all(bind=engine)
migrate_schema()

app = FastAPI(title="DSI API", description="API local do Dropshipping Intelligence", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_origin_regex=r"moz-extension://[a-zA-Z0-9-]+",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


class ProductIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    source: str = Field(default="aliexpress", max_length=40)
    title: str = Field(min_length=2, max_length=1000)
    url: HttpUrl
    image_url: Optional[HttpUrl] = None
    price: Optional[float] = Field(default=None, ge=0)
    price_min: Optional[float] = Field(default=None, ge=0)
    price_max: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, pattern=r"^[A-Z]{3}$")
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    review_count: Optional[int] = Field(default=None, ge=0)
    orders_count: Optional[int] = Field(default=None, ge=0)
    seller_name: Optional[str] = Field(default=None, max_length=300)
    description: Optional[str] = Field(default=None, max_length=10000)
    category: Optional[str] = Field(default=None, max_length=300)
    category_path: Optional[list[str]] = None
    availability: Optional[str] = Field(default=None, max_length=40)
    collected_at: Optional[datetime] = None

    @field_validator("category_path")
    @classmethod
    def clean_category_path(cls, value):
        return [str(item).strip()[:120] for item in value if str(item).strip()][:12] if value else None


def serialize_product(p: Product):
    category_path = json.loads(p.category_path) if p.category_path else []
    warnings = json.loads(p.capture_warnings) if p.capture_warnings else []
    fx = get_rate_to_brl(p.currency) if p.currency else None
    converted = round(float(p.price) * fx["rate"], 2) if p.price is not None and fx else None
    converted_min = round(float(p.price_min) * fx["rate"], 2) if p.price_min is not None and fx else None
    converted_max = round(float(p.price_max) * fx["rate"], 2) if p.price_max is not None and fx else None
    return {
        "id": p.id, "source": p.source, "source_product_id": p.source_product_id,
        "title": p.title, "category": p.category, "category_path": category_path,
        "url": p.url, "image_url": p.image_url,
        "price": p.price, "price_min": p.price_min, "price_max": p.price_max,
        "currency": p.currency, "price_brl": converted, "price_min_brl": converted_min, "price_max_brl": converted_max,
        "fx_rate_to_brl": fx["rate"] if fx else None, "fx_date": fx["date"] if fx else None,
        "fx_source": fx["source"] if fx else None, "fx_is_fallback": fx["is_fallback"] if fx else False, "rating": p.rating, "review_count": p.review_count,
        "orders_count": p.orders_count, "seller_name": p.seller_name,
        "description": p.description, "availability": p.availability,
        "data_quality": p.data_quality, "capture_warnings": warnings,
        "collected_at": p.collected_at.isoformat() if p.collected_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _same_number(a, b):
    if a is None or b is None:
        return a is b
    return round(float(a), 6) == round(float(b), 6)


def record_price_observation(db, product, collected_at):
    """Record each valid capture and create an alert only for comparable price changes."""
    if product.price is None and product.price_min is None and product.price_max is None:
        return None
    previous = db.scalar(select(PriceHistory).where(
        PriceHistory.product_id == product.id
    ).order_by(desc(PriceHistory.collected_at), desc(PriceHistory.id)).limit(1))
    history = PriceHistory(
        product_id=product.id, price=product.price, price_min=product.price_min,
        price_max=product.price_max, currency=product.currency,
        collected_at=collected_at, source="capture",
    )
    db.add(history)
    db.flush()
    if previous and previous.currency and previous.currency == product.currency:
        old_value = previous.price if previous.price is not None else previous.price_min
        new_value = product.price if product.price is not None else product.price_min
        changed = not (_same_number(previous.price, product.price) and
                       _same_number(previous.price_min, product.price_min) and
                       _same_number(previous.price_max, product.price_max))
        if changed and old_value is not None and new_value is not None:
            base_price_changed = not _same_number(previous.price, product.price)
            percent = ((float(new_value) - float(old_value)) / float(old_value) * 100) if base_price_changed and float(old_value) else None
            if base_price_changed:
                direction = "aumentou" if new_value > old_value else "diminuiu" if new_value < old_value else "foi alterado"
                detail = f"{abs(percent):.2f}%" if percent is not None else "valor alterado"
                message = f"O preço {direction} ({detail})."
                alert_type = "price_changed"
            else:
                message = "A faixa de preço ou as variantes disponíveis foram alteradas."
                alert_type = "price_range_changed"
            db.add(PriceAlert(
                product_id=product.id, history_id=history.id, alert_type=alert_type,
                old_price=old_value, new_price=new_value, currency=product.currency,
                change_percent=round(percent, 4) if percent is not None else None,
                message=message,
            ))
    return history


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return dashboard_page()


@app.get("/health")
def health():
    with SessionLocal() as db:
        db.execute(select(1))
    return {"status": "ok", "service": "dsi-api", "version": "0.4.0", "database": "connected"}


@app.post("/products")
def save_product(payload: ProductIn):
    try:
        values = normalize_product(payload.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    values["image_url"] = str(payload.image_url) if payload.image_url else None
    values["category_path"] = json.dumps(values.get("category_path") or [], ensure_ascii=False)
    values["collected_at"] = payload.collected_at or datetime.now(timezone.utc)
    quality = assess_data_quality(values)
    values["data_quality"] = quality["data_quality"]
    values["capture_warnings"] = json.dumps(quality["missing_fields"], ensure_ascii=False)

    with SessionLocal() as db:
        existing = db.scalar(select(Product).where(
            or_(Product.source_product_id == values["source_product_id"], Product.url == values["url"])
        ))
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
            existing.updated_at = datetime.now(timezone.utc)
            db.flush()
            record_price_observation(db, existing, values["collected_at"])
            db.commit(); db.refresh(existing)
            return {"message": "Produto atualizado no DSI.", "id": existing.id, "updated": True, "data_quality": existing.data_quality}
        product = Product(**values)
        db.add(product); db.flush()
        record_price_observation(db, product, values["collected_at"])
        db.commit(); db.refresh(product)
        return {"message": "Produto salvo no DSI.", "id": product.id, "updated": False, "data_quality": product.data_quality}


@app.get("/products")
def list_products(limit: int = Query(default=100, ge=1, le=500), category: Optional[str] = None, search: Optional[str] = None, sort: str = Query(default="recent", pattern="^(recent|price_asc|price_desc|rating|quality)$")):
    with SessionLocal() as db:
        query = select(Product)
        if category:
            query = query.where(Product.category == category)
        if search:
            query = query.where(Product.title.ilike(f"%{search[:100]}%"))
        if sort == "rating": query = query.order_by(Product.rating.desc().nullslast())
        elif sort == "quality": query = query.order_by(Product.data_quality.desc())
        else: query = query.order_by(Product.created_at.desc())
        rows = db.scalars(query).all() if sort in {"price_asc", "price_desc"} else db.scalars(query.limit(limit)).all()
        serialized = [serialize_product(p) for p in rows]
        if sort in {"price_asc", "price_desc"}:
            serialized.sort(key=lambda item: item["price_brl"] if item["price_brl"] is not None else float("inf"), reverse=(sort == "price_desc"))
        return serialized[:limit]


@app.get("/categories")
def list_categories():
    with SessionLocal() as db:
        products = db.scalars(select(Product.category).where(Product.category.is_not(None)).distinct().order_by(Product.category)).all()
        return [{"name": name} for name in products]


@app.get("/products/{product_id}")
def get_product(product_id: int):
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Produto não encontrado.")
        return serialize_product(product)


@app.get("/stats")
def stats():
    with SessionLocal() as db:
        products = db.scalars(select(Product)).all()
        categories = {}
        for product in products:
            key = product.category or "Sem categoria"
            categories[key] = categories.get(key, 0) + 1
        priced = [p for p in products if p.price is not None]
        converted_total = 0.0
        converted_count = 0
        for product in priced:
            fx = get_rate_to_brl(product.currency) if product.currency else None
            if fx:
                converted_total += float(product.price) * fx["rate"]
                converted_count += 1
        return {
            "total_products": len(products), "categories": categories,
            "average_data_quality": round(sum(p.data_quality for p in products) / len(products)) if products else 0,
            "products_with_price": len(priced), "products_with_currency": sum(1 for p in products if p.currency),
            "products_converted": converted_count,
            "average_price_brl": round(converted_total / converted_count, 2) if converted_count else None,
            "top_categories": sorted([{"name": k, "count": v} for k, v in categories.items()], key=lambda x: x["count"], reverse=True)[:6]
        }


@app.get("/exchange-rates")
def exchange_rates(currencies: str = Query(default="USD,EUR,CNY,GBP,BRL")):
    result = []
    for code in dict.fromkeys(x.strip().upper() for x in currencies.split(",") if x.strip()):
        if len(code) != 3 or not code.isalpha():
            continue
        rate = get_rate_to_brl(code)
        if rate:
            result.append(rate)
    return {"base": "BRL", "rates": result}


class CurrencyUpdate(BaseModel):
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")


@app.put("/products/{product_id}/currency")
def update_product_currency(product_id: int, payload: CurrencyUpdate):
    code = payload.currency.upper()
    if not get_rate_to_brl(code):
        raise HTTPException(status_code=422, detail="Moeda não suportada para conversão em BRL.")
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Produto não encontrado.")
        product.currency = code
        product.updated_at = datetime.now(timezone.utc)
        db.commit(); db.refresh(product)
        return serialize_product(product)


@app.get("/products/{product_id}/history")
def product_price_history(product_id: int, limit: int = Query(default=100, ge=1, le=1000)):
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Produto não encontrado.")
        rows = db.scalars(select(PriceHistory).where(PriceHistory.product_id == product_id)
                          .order_by(desc(PriceHistory.collected_at), desc(PriceHistory.id)).limit(limit)).all()
        rows.reverse()
        return [{"id": row.id, "price": row.price, "price_min": row.price_min,
                 "price_max": row.price_max, "currency": row.currency,
                 "collected_at": row.collected_at.isoformat(), "source": row.source}
                for row in rows]


@app.get("/alerts")
def list_price_alerts(limit: int = Query(default=100, ge=1, le=500), unread_only: bool = False):
    with SessionLocal() as db:
        query = select(PriceAlert).order_by(desc(PriceAlert.created_at), desc(PriceAlert.id))
        if unread_only:
            query = query.where(PriceAlert.is_read.is_(False))
        rows = db.scalars(query.limit(limit)).all()
        result = []
        for row in rows:
            product = db.get(Product, row.product_id)
            result.append({"id": row.id, "product_id": row.product_id,
                           "product_title": product.title if product else "Produto removido",
                           "alert_type": row.alert_type, "old_price": row.old_price,
                           "new_price": row.new_price, "currency": row.currency,
                           "change_percent": row.change_percent, "message": row.message,
                           "created_at": row.created_at.isoformat(), "is_read": row.is_read})
        return result


@app.put("/alerts/{alert_id}/read")
def mark_alert_read(alert_id: int):
    with SessionLocal() as db:
        alert = db.get(PriceAlert, alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alerta não encontrado.")
        alert.is_read = True
        db.commit()
        return {"id": alert.id, "is_read": True}


@app.get("/monitoring/summary")
def monitoring_summary():
    with SessionLocal() as db:
        history_count = db.query(PriceHistory).count()
        unread_count = db.query(PriceAlert).filter(PriceAlert.is_read.is_(False)).count()
        monitored_count = db.query(PriceHistory.product_id).distinct().count()
        return {"products_with_history": monitored_count, "observations": history_count,
                "unread_alerts": unread_count, "monitoring_mode": "capture_based",
                "note": "O histórico é atualizado quando um produto é capturado novamente pela extensão."}
