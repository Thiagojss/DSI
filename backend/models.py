from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, Boolean, Index
from database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(40), nullable=False, default="aliexpress", index=True)
    source_product_id = Column(String(80), nullable=True, index=True)
    title = Column(String(1000), nullable=False)
    category = Column(String(300), nullable=True, index=True)
    category_path = Column(Text, nullable=True)
    manual_title = Column(String(180), nullable=True)
    manual_category = Column(String(120), nullable=True, index=True)
    border_color = Column(String(7), nullable=True)
    url = Column(String(2048), nullable=False, unique=True, index=True)
    image_url = Column(String(2048), nullable=True)
    image_urls_json = Column(Text, nullable=True)
    seller_url = Column(String(2048), nullable=True)
    seller_rating = Column(Float, nullable=True)
    seller_positive_feedback_pct = Column(Float, nullable=True)
    price = Column(Float, nullable=True)
    price_min = Column(Float, nullable=True)
    price_max = Column(Float, nullable=True)
    currency = Column(String(3), nullable=True)
    original_price = Column(Float, nullable=True)
    discount_percent = Column(Float, nullable=True)
    shipping_text = Column(String(160), nullable=True)
    delivery_text = Column(String(160), nullable=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    orders_count = Column(Integer, nullable=True)
    seller_name = Column(String(300), nullable=True)
    description = Column(Text, nullable=True)
    availability = Column(String(40), nullable=True)
    data_quality = Column(Integer, nullable=False, default=0)
    is_favorite = Column(Boolean, nullable=False, default=False, index=True)
    capture_warnings = Column(Text, nullable=True)
    collected_at = Column(DateTime(timezone=True), nullable=True)
    last_batch_collected_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (Index("ix_price_history_product_collected", "product_id", "collected_at"),)

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    price = Column(Float, nullable=True)
    price_min = Column(Float, nullable=True)
    price_max = Column(Float, nullable=True)
    currency = Column(String(3), nullable=True)
    collected_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    source = Column(String(40), nullable=False, default="capture")


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    history_id = Column(Integer, ForeignKey("price_history.id", ondelete="SET NULL"), nullable=True)
    alert_type = Column(String(40), nullable=False, default="price_changed")
    old_price = Column(Float, nullable=True)
    new_price = Column(Float, nullable=True)
    currency = Column(String(3), nullable=True)
    change_percent = Column(Float, nullable=True)
    message = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    is_read = Column(Boolean, nullable=False, default=False, index=True)


class CollectionSession(Base):
    __tablename__ = "collection_sessions"

    id = Column(Integer, primary_key=True)
    source = Column(String(40), nullable=False, default="aliexpress")
    source_url = Column(String(2048), nullable=False)
    status = Column(String(24), nullable=False, default="completed")
    total_found = Column(Integer, nullable=False, default=0)
    saved_new = Column(Integer, nullable=False, default=0)
    updated = Column(Integer, nullable=False, default=0)
    skipped = Column(Integer, nullable=False, default=0)
    message = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)


class CostScenario(Base):
    __tablename__ = "cost_scenarios"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    inputs_json = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class ResearchDecision(Base):
    """Decisão humana; nunca inferida de indicadores de venda."""
    __tablename__ = "research_decisions"
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    stage = Column(String(32), nullable=False, default="investigar", index=True)
    priority = Column(String(12), nullable=False, default="normal")
    notes = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class ResearchCheck(Base):
    """Verificação manual rastreável; não implica confirmação automática."""
    __tablename__ = "research_checks"
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    kind = Column(String(32), primary_key=True)
    status = Column(String(16), nullable=False, default="pendente")
    evidence = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
