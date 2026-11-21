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
    url = Column(String(2048), nullable=False, unique=True, index=True)
    image_url = Column(String(2048), nullable=True)
    price = Column(Float, nullable=True)
    price_min = Column(Float, nullable=True)
    price_max = Column(Float, nullable=True)
    currency = Column(String(3), nullable=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    orders_count = Column(Integer, nullable=True)
    seller_name = Column(String(300), nullable=True)
    description = Column(Text, nullable=True)
    availability = Column(String(40), nullable=True)
    data_quality = Column(Integer, nullable=False, default=0)
    capture_warnings = Column(Text, nullable=True)
    collected_at = Column(DateTime(timezone=True), nullable=True)
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
