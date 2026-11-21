from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path
from threading import Lock
import sqlite3
import os
import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from sqlalchemy import select, or_, desc, func
from sqlalchemy.exc import SQLAlchemyError

from database import Base, engine, SessionLocal, migrate_schema, DATABASE_PATH
from models import Product, PriceHistory, PriceAlert, CollectionSession, CostScenario
from collectors.aliexpress import normalize_product
from analyzers.scoring import assess_data_quality
from fx import get_rate_to_brl
from dashboard import dashboard_page
from services.costs import CostInputs, analyze_costs

def backup_before_schema_migration():
    """Backup SQLite consistente antes de qualquer alteração de colunas existentes."""
    if not DATABASE_PATH.exists():
        return
    with sqlite3.connect(f"file:{DATABASE_PATH.as_posix()}?mode=ro", uri=True, timeout=15) as src:
        columns = {row[1] for row in src.execute("PRAGMA table_info(products)")}
        if not columns or {"last_batch_collected_at", "image_urls_json", "seller_url", "seller_rating", "seller_positive_feedback_pct"}.issubset(columns):
            return
        directory = DATABASE_PATH.parent / "backups"
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"dsi-before-v0.18-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.db"
        with sqlite3.connect(str(target), timeout=15) as dest:
            src.backup(dest)
        os.chmod(target, 0o600)


backup_before_schema_migration()
migrate_schema()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="DSI API", description="API local do Dropshipping Intelligence", version="0.18.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_origin_regex=r"moz-extension://[a-zA-Z0-9-]+",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def validate_browser_origin(request, call_next):
    # Navegadores enviam Origin em escritas entre contextos. Bloqueia origens
    # externas mesmo se o cliente não estiver sujeito ao CORS.
    origin = request.headers.get("origin")
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and origin:
        from urllib.parse import urlsplit
        parts = urlsplit(origin)
        allowed = (origin in {"http://127.0.0.1:8000", "http://localhost:8000"}
                   or (parts.scheme == "moz-extension" and parts.hostname
                       and __import__("re").fullmatch(r"[a-zA-Z0-9-]+", parts.hostname)))
        if not allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Origem não permitida."}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


class ProductIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    source: str = Field(default="aliexpress", max_length=40)
    title: str = Field(min_length=2, max_length=1000)
    url: HttpUrl
    image_url: Optional[HttpUrl] = None
    image_urls: list[HttpUrl] = Field(default_factory=list, max_length=16)
    seller_url: Optional[HttpUrl] = None
    seller_rating: Optional[float] = Field(default=None, ge=0, le=5)
    seller_positive_feedback_pct: Optional[float] = Field(default=None, ge=0, le=100)

    @field_validator("seller_url")
    @classmethod
    def ensure_seller_domain(cls, value):
        if value and not (value.host == "aliexpress.com" or value.host.endswith(".aliexpress.com")):
            raise ValueError("O link do fornecedor precisa pertencer ao AliExpress.")
        return value
    price: Optional[float] = Field(default=None, ge=0)
    price_min: Optional[float] = Field(default=None, ge=0)
    price_max: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, pattern=r"^[A-Z]{3}$")
    original_price: Optional[float] = Field(default=None, ge=0)
    discount_percent: Optional[float] = Field(default=None, ge=0, le=100)
    shipping_text: Optional[str] = Field(default=None, max_length=160)
    delivery_text: Optional[str] = Field(default=None, max_length=160)
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
        "title": p.manual_title or p.title, "source_title": p.title,
        "category": p.manual_category or p.category, "source_category": p.category,
        "manual_title": p.manual_title, "manual_category": p.manual_category,
        "border_color": p.border_color, "category_path": category_path,
        "url": p.url, "image_url": p.image_url,
        "image_urls": json.loads(p.image_urls_json) if p.image_urls_json else ([p.image_url] if p.image_url else []),
        "seller_url": p.seller_url, "seller_rating": p.seller_rating,
        "seller_positive_feedback_pct": p.seller_positive_feedback_pct,
        "price": p.price, "price_min": p.price_min, "price_max": p.price_max,
        "original_price": p.original_price, "discount_percent": p.discount_percent,
        "shipping_text": p.shipping_text, "delivery_text": p.delivery_text,
        "currency": p.currency, "price_brl": converted, "price_min_brl": converted_min, "price_max_brl": converted_max,
        "fx_rate_to_brl": fx["rate"] if fx else None, "fx_date": fx["date"] if fx else None,
        "fx_source": fx["source"] if fx else None, "fx_is_fallback": fx["is_fallback"] if fx else False, "rating": p.rating, "review_count": p.review_count,
        "orders_count": p.orders_count, "seller_name": p.seller_name,
        "description": p.description, "availability": p.availability,
        "data_quality": p.data_quality, "is_favorite": bool(p.is_favorite), "capture_warnings": warnings,
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
    return {"status": "ok", "service": "dsi-api", "version": "0.18.0", "database": "connected"}


def prepare_product_values(payload: ProductIn) -> dict:
    """Normaliza uma captura e calcula a completude antes de persistir."""
    values = normalize_product(payload.model_dump(mode="json"))
    values["image_url"] = str(payload.image_url) if payload.image_url else None
    gallery = list(dict.fromkeys(str(link) for link in payload.image_urls))[:16]
    if values["image_url"] and values["image_url"] not in gallery:
        gallery.insert(0, values["image_url"])
    values["image_urls_json"] = json.dumps(gallery[:16]) if gallery else None
    values.pop("image_urls", None)
    values["seller_url"] = str(payload.seller_url) if payload.seller_url else None
    values["category_path"] = json.dumps(values.get("category_path") or [], ensure_ascii=False)
    values["collected_at"] = payload.collected_at or datetime.now(timezone.utc)
    quality = assess_data_quality(values)
    values["data_quality"] = quality["data_quality"]
    values["capture_warnings"] = json.dumps(quality["missing_fields"], ensure_ascii=False)
    return values


def upsert_product(db, payload: ProductIn) -> tuple[Product, bool]:
    """Cria ou atualiza um produto e registra a observação de preço."""
    values = prepare_product_values(payload)
    existing = db.scalar(select(Product).where(
        or_(Product.source_product_id == values["source_product_id"], Product.url == values["url"])
    ))
    if existing:
        # Capturas de listagem são parciais. Um campo ausente não destrói dado
        # antes observado na página individual (nem a moeda escolhida manualmente).
        for key, value in values.items():
            if key in {"data_quality", "capture_warnings"}:
                continue
            if value is None or (key == "category_path" and value == "[]"):
                continue
            if key in {"price", "original_price"} and values.get("currency") is None:
                continue  # não associar preço de moeda desconhecida à moeda antiga
            if key == "image_urls_json":
                previous_images = json.loads(existing.image_urls_json) if existing.image_urls_json else []
                additions = json.loads(value)
                value = json.dumps(list(dict.fromkeys(previous_images + additions))[:16])
            setattr(existing, key, value)
        # A completude deve refletir o registro consolidado, não só a última coleta.
        consolidated = {field: getattr(existing, field) for field in
                        ("title", "source_product_id", "url", "image_url", "price",
                         "price_min", "currency", "rating", "review_count", "orders_count",
                         "seller_name", "seller_url", "category")}
        quality = assess_data_quality(consolidated)
        existing.data_quality = quality["data_quality"]
        existing.capture_warnings = json.dumps(quality["missing_fields"], ensure_ascii=False)
        existing.updated_at = datetime.now(timezone.utc)
        product, updated = existing, True
    else:
        product, updated = Product(**values), False
        db.add(product)
    db.flush()
    if (values.get("price") is not None or values.get("price_min") is not None) and values.get("currency"):
        record_price_observation(db, product, values["collected_at"])
    return product, updated


@app.post("/products")
def save_product(payload: ProductIn):
    try:
        with SessionLocal() as db:
            product, updated = upsert_product(db, payload)
            db.commit()
            db.refresh(product)
            return {
                "message": "Produto atualizado no DSI." if updated else "Produto salvo no DSI.",
                "id": product.id, "updated": updated, "data_quality": product.data_quality,
            }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/products")
def list_products(limit: int = Query(default=100, ge=1, le=500), category: Optional[str] = None, search: Optional[str] = None, sort: str = Query(default="recent", pattern="^(recent|price_asc|price_desc|rating|quality)$")):
    with SessionLocal() as db:
        query = select(Product)
        if category:
            query = query.where(func.coalesce(Product.manual_category, Product.category) == category)
        if search:
            query = query.where(or_(Product.title.ilike(f"%{search[:100]}%"), Product.manual_title.ilike(f"%{search[:100]}%")))
        if sort == "rating": query = query.order_by(Product.rating.desc().nullslast())
        elif sort == "quality": query = query.order_by(Product.data_quality.desc())
        else: query = query.order_by(Product.created_at.desc())
        rows = db.scalars(query).all() if sort in {"price_asc", "price_desc"} else db.scalars(query.limit(limit)).all()
        serialized = [serialize_product(p) for p in rows]
        if sort in {"price_asc", "price_desc"}:
            direction = -1 if sort == "price_desc" else 1
            serialized.sort(key=lambda item: (
                item["price_brl"] is None,
                (item["price_brl"] or 0) * direction,
            ))
        return serialized[:limit]


@app.get("/intelligence/radar")
def intelligence_radar(limit: int = Query(default=2000, ge=1, le=5000)):
    """Dados observados para comparação por categoria. Sem índice comercial inventado."""
    with SessionLocal() as db:
        total = db.scalar(select(func.count(Product.id))) or 0
        rows = db.scalars(select(Product).order_by(desc(Product.updated_at), desc(Product.id)).limit(limit)).all()
        return {"total_catalog": total, "returned": len(rows), "truncated": total > len(rows),
                "products": [serialize_product(p) for p in rows]}


class CollectionBatchIn(BaseModel):
    source_url: HttpUrl
    products: list[ProductIn] = Field(min_length=1, max_length=50)

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value):
        host = (value.host or "").lower()
        if not (host == "aliexpress.com" or host.endswith(".aliexpress.com")):
            raise ValueError("A sessão aceita somente páginas do AliExpress.")
        return value


# Bloqueio de 24h aplicado exclusivamente às sessões de coleta em lote.
# O identificador AliExpress permanece global entre URLs, categorias e abas.
BATCH_COOLDOWN = timedelta(hours=24)
_collection_lock = Lock()  # serializa coletas na instância local da API


def batch_cutoff(now: datetime) -> datetime:
    return now - BATCH_COOLDOWN


def batch_recent(value: Optional[datetime], now: datetime) -> bool:
    if value is None:
        return False
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)  # SQLite pode remover tzinfo
    return value > batch_cutoff(now)


class CollectionEligibilityIn(BaseModel):
    product_ids: list[str] = Field(min_length=1, max_length=3000)

    @field_validator("product_ids")
    @classmethod
    def validate_product_ids(cls, value):
        if any(not item.isascii() or not item.isdecimal() or len(item) > 80 for item in value):
            raise ValueError("IDs AliExpress devem conter somente dígitos.")
        return list(dict.fromkeys(value))


@app.post("/collection-eligibility")
def collection_eligibility(payload: CollectionEligibilityIn):
    """Retorna IDs bloqueados usando o banco, não cache do navegador."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        rows = db.execute(select(Product.source_product_id, Product.last_batch_collected_at).where(
            Product.source == "aliexpress", Product.source_product_id.in_(payload.product_ids),
            Product.last_batch_collected_at.is_not(None)
        )).all()
    blocked = {identity for identity, captured in rows if batch_recent(captured, now)}
    return {"cooldown_hours": 24, "blocked_ids": sorted(blocked),
            "eligible_count": len(payload.product_ids) - len(blocked)}


@app.post("/collection-sessions")
def create_collection_session(payload: CollectionBatchIn):
    source_url = str(payload.source_url)
    counts = {"new": 0, "updated": 0, "skipped": 0, "cooldown": 0}
    # Verificação novamente na gravação: a prévia pode ficar desatualizada.
    with _collection_lock:
        with SessionLocal() as db:
            now = datetime.now(timezone.utc)
            processed_ids = set()
            for item in payload.products:
                try:
                    values = prepare_product_values(item)
                    identity = values["source_product_id"]
                    if identity in processed_ids:
                        counts["skipped"] += 1
                        continue
                    processed_ids.add(identity)
                    existing = db.scalar(select(Product).where(
                        Product.source == "aliexpress", Product.source_product_id == identity
                    ))
                    if existing and batch_recent(existing.last_batch_collected_at, now):
                        counts["cooldown"] += 1
                        counts["skipped"] += 1
                        continue
                    with db.begin_nested():
                        product, updated = upsert_product(db, item)
                        product.last_batch_collected_at = now
                        db.flush()
                    counts["updated" if updated else "new"] += 1
                except (ValueError, TypeError, SQLAlchemyError):
                    counts["skipped"] += 1
            total = len(payload.products)
            status = "completed" if counts["skipped"] == 0 else ("partial" if counts["new"] + counts["updated"] else "empty")
            session = CollectionSession(
                source="aliexpress", source_url=source_url, status=status, total_found=total,
                saved_new=counts["new"], updated=counts["updated"], skipped=counts["skipped"],
                message="Coleta manual dos itens carregados; repetição em lote bloqueada por 24 horas."
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            return {"session_id": session.id, "status": status, "total_found": total,
                    "saved_new": counts["new"], "updated": counts["updated"], "skipped": counts["skipped"],
                    "cooldown_skipped": counts["cooldown"], "message": session.message}


@app.get("/collection-sessions")
def list_collection_sessions(limit: int = Query(default=30, ge=1, le=100)):
    with SessionLocal() as db:
        rows = db.scalars(select(CollectionSession).order_by(desc(CollectionSession.created_at), desc(CollectionSession.id)).limit(limit)).all()
        return [{"id": row.id, "source": row.source, "source_url": row.source_url, "status": row.status,
                 "total_found": row.total_found, "saved_new": row.saved_new, "updated": row.updated,
                 "skipped": row.skipped, "message": row.message, "created_at": row.created_at.isoformat()} for row in rows]


@app.get("/categories")
def list_categories():
    with SessionLocal() as db:
        effective = func.coalesce(Product.manual_category, Product.category)
        products = db.scalars(select(effective).where(effective.is_not(None)).distinct().order_by(effective)).all()
        return [{"name": name} for name in products]


class ProductOrganizationIn(BaseModel):
    """Dados do usuário, independentes dos atributos do anúncio."""
    model_config = ConfigDict(str_strip_whitespace=True)
    manual_title: Optional[str] = Field(default=None, max_length=180)
    manual_category: Optional[str] = Field(default=None, max_length=120)
    border_color: Optional[str] = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("manual_title", "manual_category")
    @classmethod
    def normalize_optional_label(cls, value):
        return value or None


@app.put("/products/{product_id}/organization")
def update_product_organization(product_id: int, payload: ProductOrganizationIn):
    """Substitui personalização do usuário; null restaura o valor capturado."""
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Produto não encontrado.")
        product.manual_title = payload.manual_title
        product.manual_category = payload.manual_category
        product.border_color = payload.border_color.lower() if payload.border_color else None
        product.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(product)
        return serialize_product(product)


# v0.14: diagnóstico objetivo de cobertura dos campos; ausência não é zero.
QUALITY_FIELDS = {
    "price": "Preço", "currency": "Moeda", "image_url": "Imagem",
    "category": "Categoria de origem", "rating": "Nota", "review_count": "Avaliações",
    "orders_count": "Pedidos", "seller_name": "Fornecedor",
    "shipping_text": "Frete", "delivery_text": "Entrega",
    "seller_url": "Link da loja", "seller_rating": "Nota da loja",
    "seller_positive_feedback_pct": "Feedback positivo da loja",
}


def quality_details(product):
    present = {key: getattr(product, key) is not None and getattr(product, key) != "" for key in QUALITY_FIELDS}
    return {"present": present, "missing": [key for key, ok in present.items() if not ok],
            "coverage_percent": round(100 * sum(present.values()) / len(present)),
            "observed_fields": sum(present.values()), "total_fields": len(present)}


@app.get("/intelligence/collection-quality")
def collection_quality(category: Optional[str] = None):
    """Cobertura de coleta por campo, sem confundir ausência com zero."""
    with SessionLocal() as db:
        statement = select(Product)
        if category:
            statement = statement.where(func.coalesce(Product.manual_category, Product.category) == category)
        products = db.scalars(statement).all()
        totals = {field: 0 for field in QUALITY_FIELDS}
        for product in products:
            for field, ok in quality_details(product)["present"].items():
                totals[field] += int(ok)
        count = len(products)
        return {"total_products": count, "category": category,
                "fields": [{"field": key, "label": label, "present": totals[key],
                            "missing": count - totals[key],
                            "coverage_percent": round(100 * totals[key] / count) if count else 0}
                           for key, label in QUALITY_FIELDS.items()]}


class BulkOrganizationIn(BaseModel):
    product_ids: list[int] = Field(min_length=1, max_length=200)
    manual_category: Optional[str] = Field(default=None, max_length=120)
    border_color: Optional[str] = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    apply_category: bool = False
    apply_color: bool = False

    @field_validator("product_ids")
    @classmethod
    def validate_unique_ids(cls, ids):
        if len(ids) != len(set(ids)) or any(item <= 0 for item in ids):
            raise ValueError("IDs devem ser positivos e sem repetição.")
        return ids

    @field_validator("manual_category")
    @classmethod
    def clean_category(cls, value):
        return value.strip() or None if value is not None else None


@app.put("/products/organization/bulk")
def bulk_organize(payload: BulkOrganizationIn):
    """Atualiza apenas campos explicitamente selecionados, de forma atômica."""
    if not payload.apply_category and not payload.apply_color:
        raise HTTPException(status_code=422, detail="Selecione ao menos uma alteração.")
    with SessionLocal() as db:
        products = db.scalars(select(Product).where(Product.id.in_(payload.product_ids))).all()
        if len(products) != len(payload.product_ids):
            raise HTTPException(status_code=404, detail="Um ou mais produtos não existem; nada foi alterado.")
        for product in products:
            if payload.apply_category:
                product.manual_category = payload.manual_category
            if payload.apply_color:
                product.border_color = payload.border_color.lower() if payload.border_color else None
            product.updated_at = datetime.now(timezone.utc)
        db.commit()
        return {"updated": len(products), "product_ids": payload.product_ids}


class FavoriteUpdate(BaseModel):
    is_favorite: bool


@app.put("/products/{product_id}/favorite")
def update_product_favorite(product_id: int, payload: FavoriteUpdate):
    """Define explicitamente se o produto está ou não nos favoritos."""
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Produto não encontrado.")
        product.is_favorite = payload.is_favorite
        db.commit()
        db.refresh(product)
        return {"id": product.id, "is_favorite": bool(product.is_favorite),
                "message": "Produto adicionado aos favoritos." if product.is_favorite else "Produto removido dos favoritos."}


@app.get("/favorites")
def list_favorites(limit: int = Query(default=500, ge=1, le=500)):
    with SessionLocal() as db:
        rows = db.scalars(select(Product).where(Product.is_favorite.is_(True))
                          .order_by(desc(Product.updated_at), desc(Product.id)).limit(limit)).all()
        return [serialize_product(product) for product in rows]


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
        total = db.scalar(select(func.count(Product.id))) or 0
        quality = round(db.scalar(select(func.avg(Product.data_quality))) or 0)
        priced = db.scalar(select(func.count(Product.id)).where(Product.price.is_not(None))) or 0
        with_currency = db.scalar(select(func.count(Product.id)).where(Product.currency.is_not(None))) or 0
        categories = dict(db.execute(
            select(func.coalesce(Product.manual_category, Product.category, "Sem categoria"), func.count(Product.id))
            .group_by(func.coalesce(Product.manual_category, Product.category, "Sem categoria"))
        ).all())
        groups = db.execute(
            select(Product.currency, func.sum(Product.price), func.count(Product.id))
            .where(Product.price.is_not(None), Product.currency.is_not(None))
            .group_by(Product.currency)
        ).all()
        converted = [
            (float(total_price or 0) * rate["rate"], count)
            for currency, total_price, count in groups
            if (rate := get_rate_to_brl(currency))
        ]
        converted_total = sum(value for value, _ in converted)
        converted_count = sum(count for _, count in converted)
        top = sorted(
            ({"name": name, "count": count} for name, count in categories.items()),
            key=lambda item: item["count"], reverse=True,
        )[:6]
        return {
            "total_products": total, "categories": categories,
            "average_data_quality": quality, "products_with_price": priced,
            "products_with_currency": with_currency, "products_converted": converted_count,
            "average_price_brl": round(converted_total / converted_count, 2) if converted_count else None,
            "top_categories": top,
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


def cost_row(db, product, scenario):
    inputs = CostInputs.model_validate_json(scenario.inputs_json)
    observed = serialize_product(product)
    result = analyze_costs(inputs, observed['price_brl'], observed['fx_is_fallback'])
    return {'product_id': product.id, 'title': product.manual_title or product.title, 'category': product.manual_category or product.category or 'Sem categoria',
            'seller_name': product.seller_name, 'url': product.url,
            'fx_source': observed['fx_source'], 'fx_date': observed['fx_date'],
            'inputs': inputs.model_dump(), 'analysis': result,
            'updated_at': scenario.updated_at.isoformat() if scenario.updated_at else None}


@app.get("/products/{product_id}/cost-analysis")
def get_cost_analysis(product_id: int):
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product: raise HTTPException(status_code=404, detail="Produto não encontrado.")
        scenario = db.scalar(select(CostScenario).where(CostScenario.product_id == product_id))
        if scenario: return cost_row(db, product, scenario)
        observed = serialize_product(product)
        inputs = CostInputs()
        return {'product_id': product.id, 'title': product.manual_title or product.title, 'category': product.manual_category or product.category or 'Sem categoria',
                'inputs': inputs.model_dump(), 'analysis': analyze_costs(inputs, observed['price_brl'], observed['fx_is_fallback']),
                'saved': False}


@app.put("/products/{product_id}/cost-analysis")
def save_cost_analysis(product_id: int, inputs: CostInputs):
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product: raise HTTPException(status_code=404, detail="Produto não encontrado.")
        scenario = db.scalar(select(CostScenario).where(CostScenario.product_id == product_id))
        if scenario:
            scenario.inputs_json = inputs.model_dump_json()
            scenario.updated_at = datetime.now(timezone.utc)
        else:
            scenario = CostScenario(product_id=product_id, inputs_json=inputs.model_dump_json())
            db.add(scenario)
        db.commit()
        db.refresh(scenario)
        return cost_row(db, product, scenario)


@app.get("/intelligence/costs")
def list_cost_analyses(limit: int = Query(default=2000, ge=1, le=5000)):
    with SessionLocal() as db:
        rows = db.execute(select(Product, CostScenario).join(CostScenario, CostScenario.product_id == Product.id)
                          .order_by(desc(CostScenario.updated_at), desc(CostScenario.id)).limit(limit)).all()
        count = db.scalar(select(func.count(CostScenario.id))) or 0
        return {'total': count, 'returned': len(rows), 'truncated': count > len(rows),
                'scenarios': [cost_row(db, product, scenario) for product, scenario in rows]}


@app.get("/intelligence/opportunities")
def intelligence_opportunities(limit: int = Query(default=2000, ge=1, le=5000), category: Optional[str] = None):
    """Ranking auditável: não transforma avaliações em vendas nem compara categorias diferentes."""
    with SessionLocal() as db:
        total = db.scalar(select(func.count(Product.id))) or 0
        products = db.scalars(select(Product).order_by(desc(Product.updated_at), desc(Product.id)).limit(limit)).all()
        ids = [p.id for p in products]
        scenarios = {row.product_id: row for row in db.scalars(select(CostScenario).where(CostScenario.product_id.in_(ids))).all()} if ids else {}
        rows = []
        for product in products:
            p = serialize_product(product)
            group = p['category'] or 'Sem categoria'
            if category and group != category: continue
            scenario = scenarios.get(product.id)
            financial = cost_row(db, product, scenario)['analysis'] if scenario else None
            warnings = []
            if not scenario: warnings.append('Sem cenário de custos salvo')
            elif financial['profit_brl'] is None: warnings.append('Cenário financeiro incompleto')
            if p['review_count'] is None: warnings.append('Avaliações não observadas')
            if p['orders_count'] is None: warnings.append('Pedidos não observados')
            if not p['seller_name']: warnings.append('Fornecedor não identificado')
            if p['fx_is_fallback']: warnings.append('Câmbio de contingência')
            margin = financial['margin_pct'] if financial else None
            stress = financial.get('sensitivity') if financial else None
            stress_profit = stress['combined_stress']['profit_brl'] if stress else None
            status = ('incompleto' if margin is None else 'prejuízo simulado' if margin < 0 else
                      'frágil no estresse' if stress_profit is not None and stress_profit < 0 else 'cenário positivo')
            rows.append({'product_id': product.id, 'title': p['title'], 'category': group,
                         'seller_name': p['seller_name'], 'url': p['url'], 'price_brl': p['price_brl'],
                         'rating': p['rating'], 'review_count': p['review_count'], 'orders_count': p['orders_count'],
                         'data_quality': p['data_quality'], 'margin_pct': margin,
                         'profit_brl': financial['profit_brl'] if financial else None,
                         'stress_profit_brl': stress_profit, 'status': status, 'warnings': warnings,
                         'cost_assumptions': financial['zero_assumptions'] if financial else [],
                         'estimated': True})
        # Margem não substitui qualidade; itens sem cenário permanecem visíveis no final.
        rows.sort(key=lambda r: (r['margin_pct'] is None, -(r['margin_pct'] or 0),
                                 -(r['review_count'] or 0), r['product_id']))
        return {'total_catalog': total, 'returned': len(rows), 'truncated': total > len(products),
                'ranking_basis': 'Margem simulada decrescente; avaliações apenas como desempate. Sem índice de demanda.',
                'products': rows}


# Configurações locais: exclui registros, jamais o arquivo SQLite nem seu schema.
_reset_lock = Lock()


class ClearCatalogRequest(BaseModel):
    confirmation: str = Field(min_length=1)


@app.get("/settings/database")
def database_settings():
    with SessionLocal() as db:
        return {"products": db.scalar(select(func.count(Product.id))) or 0,
                "price_history": db.scalar(select(func.count(PriceHistory.id))) or 0,
                "price_alerts": db.scalar(select(func.count(PriceAlert.id))) or 0,
                "cost_scenarios": db.scalar(select(func.count(CostScenario.id))) or 0,
                "collection_sessions": db.scalar(select(func.count(CollectionSession.id))) or 0}


class BackupRequest(BaseModel):
    confirmation: str


def consistent_backup(label: str) -> Path:
    backup_dir = DATABASE_PATH.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"dsi-{label}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.db"
    try:
        with sqlite3.connect(f"file:{DATABASE_PATH.as_posix()}?mode=rw", uri=True, timeout=15) as src:
            with sqlite3.connect(str(target), timeout=15) as dest:
                src.backup(dest)
        os.chmod(target, 0o600)
        return target
    except Exception:
        target.unlink(missing_ok=True)
        raise


@app.post("/settings/backup")
def create_manual_backup(payload: BackupRequest):
    if payload.confirmation != "CRIAR BACKUP":
        raise HTTPException(422, detail="Confirme com CRIAR BACKUP.")
    try:
        path = consistent_backup("manual")
    except (sqlite3.Error, OSError) as exc:
        raise HTTPException(503, detail="Não foi possível criar o backup.") from exc
    return {"created": True, "path": str(path), "bytes": path.stat().st_size}


@app.get("/settings/integrity")
def database_integrity():
    try:
        with sqlite3.connect(f"file:{DATABASE_PATH.as_posix()}?mode=ro", uri=True, timeout=15) as db:
            result = db.execute("PRAGMA quick_check").fetchone()[0]
    except sqlite3.Error as exc:
        raise HTTPException(503, detail="Não foi possível verificar o banco.") from exc
    return {"healthy": result == "ok", "result": result if result == "ok" else "Falha de integridade detectada"}


@app.get("/settings/export-products.csv")
def export_products_csv():
    import csv, io
    from fastapi.responses import Response
    output = io.StringIO(newline="")
    cols = ["id", "title", "category", "source_product_id", "url", "image_url", "seller_name", "seller_url",
            "seller_rating", "seller_positive_feedback_pct", "price", "currency", "rating", "review_count", "orders_count"]
    writer = csv.writer(output)
    writer.writerow(cols)
    with SessionLocal() as db:
        for product in db.scalars(select(Product).order_by(Product.id)).yield_per(200):
            values = {"title": product.manual_title or product.title, "category": product.manual_category or product.category}
            row = []
            for field in cols:
                value = values.get(field, getattr(product, field, None))
                # Protege importadores de planilha contra injeção de fórmulas.
                if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                    value = "'" + value
                row.append(value)
            writer.writerow(row)
    return Response(content="\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="dsi-produtos.csv"'})


@app.post("/settings/clear-products")
def clear_products(payload: ClearCatalogRequest):
    if payload.confirmation != "LIMPAR PRODUTOS":
        raise HTTPException(status_code=422, detail="Digite exatamente LIMPAR PRODUTOS para confirmar.")
    if not _reset_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Uma limpeza já está em andamento.")
    backup_path = None
    try:
        # A API só deve servir a máquina local. O backup é feito antes da exclusão,
        # pela API de backup do SQLite, preservando uma cópia consistente.
        backup_dir = DATABASE_PATH.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_path = backup_dir / f"dsi-before-clear-{timestamp}.db"
        try:
            with sqlite3.connect(f"file:{DATABASE_PATH.as_posix()}?mode=rw", uri=True, timeout=15) as src:
                with sqlite3.connect(str(backup_path), timeout=15) as dest:
                    src.backup(dest)
            os.chmod(backup_path, 0o600)
        except Exception:
            if backup_path.exists():
                backup_path.unlink()
            raise HTTPException(status_code=503, detail="Backup falhou. Nenhum registro foi apagado.")
        try:
            with SessionLocal.begin() as db:
                counts = {
                    "products": db.scalar(select(func.count(Product.id))) or 0,
                    "price_history": db.scalar(select(func.count(PriceHistory.id))) or 0,
                    "price_alerts": db.scalar(select(func.count(PriceAlert.id))) or 0,
                    "cost_scenarios": db.scalar(select(func.count(CostScenario.id))) or 0,
                    "collection_sessions": db.scalar(select(func.count(CollectionSession.id))) or 0,
                }
                # Ordem respeita as relações mesmo quando foreign_keys=ON.
                for model in (PriceAlert, PriceHistory, CostScenario, CollectionSession, Product):
                    db.query(model).delete(synchronize_session=False)
        except SQLAlchemyError:
            raise HTTPException(status_code=503, detail="Falha na exclusão. Transação revertida; backup mantido.")
        return {"status": "cleared", "deleted": counts, "backup_path": str(backup_path),
                "database_preserved": True}
    finally:
        _reset_lock.release()
