from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(String(512), default="")
    brand = Column(String(256), default="")
    category = Column(String(256), default="")
    image_url = Column(Text, default="")
    label = Column(String(256), default="")
    target_buy_price = Column(Float, nullable=True)
    source = Column(String(50), default="manual")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    price_records = relationship("PriceRecord", back_populates="product", cascade="all, delete-orphan")
    deals = relationship("Deal", back_populates="product", cascade="all, delete-orphan")


class PriceRecord(Base):
    __tablename__ = "price_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String(20), ForeignKey("products.asin"), nullable=False, index=True)
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)
    current_price = Column(Float, nullable=True)
    list_price = Column(Float, nullable=True)
    buy_box_price = Column(Float, nullable=True)
    savings_percent = Column(Float, nullable=True)
    sales_rank = Column(Integer, nullable=True)

    # Keepa historical averages
    avg_30d = Column(Float, nullable=True)
    avg_90d = Column(Float, nullable=True)
    avg_180d = Column(Float, nullable=True)
    all_time_low = Column(Float, nullable=True)
    all_time_high = Column(Float, nullable=True)

    source = Column(String(50), default="paapi")

    product = relationship("Product", back_populates="price_records")

    __table_args__ = (
        Index("ix_price_records_asin_checked", "asin", "checked_at"),
    )


class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String(20), ForeignKey("products.asin"), nullable=False, index=True)
    deal_type = Column(String(50), nullable=False)  # price_drop, clearance, below_average, all_time_low, margin_opportunity
    trigger_price = Column(Float, nullable=True)
    reference_price = Column(Float, nullable=True)
    drop_percent = Column(Float, nullable=True)
    estimated_profit = Column(Float, nullable=True)
    estimated_roi = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    detected_at = Column(DateTime, default=datetime.utcnow)
    dismissed_at = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="deals")
    alerts = relationship("Alert", back_populates="deal", cascade="all, delete-orphan")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String(20), nullable=False, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=True)
    alert_type = Column(String(50), nullable=False)
    message = Column(Text, default="")
    sent_at = Column(DateTime, default=datetime.utcnow)

    deal = relationship("Deal", back_populates="alerts")

    __table_args__ = (
        UniqueConstraint("asin", "deal_id", "alert_type", name="uq_alert_dedup"),
    )
