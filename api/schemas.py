from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# --- Products ---

class ProductCreate(BaseModel):
    asin: str = Field(..., min_length=5, max_length=20)
    label: str = ""
    target_buy_price: Optional[float] = None


class ProductResponse(BaseModel):
    asin: str
    title: str
    brand: str
    category: str
    image_url: str
    label: str
    target_buy_price: Optional[float]
    source: str
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ProductSearchRequest(BaseModel):
    keywords: str = Field(..., min_length=1)
    max_results: int = Field(default=10, ge=1, le=10)


class ProductSearchResult(BaseModel):
    asin: str
    title: str
    brand: str
    current_price: Optional[float]
    image_url: str


# --- Prices ---

class PriceRecordResponse(BaseModel):
    id: int
    asin: str
    checked_at: Optional[datetime]
    current_price: Optional[float]
    list_price: Optional[float]
    buy_box_price: Optional[float]
    savings_percent: Optional[float]
    sales_rank: Optional[int]
    avg_30d: Optional[float]
    avg_90d: Optional[float]
    avg_180d: Optional[float]
    all_time_low: Optional[float]
    all_time_high: Optional[float]
    source: str

    model_config = {"from_attributes": True}


class PriceStats(BaseModel):
    min_price: Optional[float]
    max_price: Optional[float]
    avg_price: Optional[float]
    record_count: int


class PriceHistoryResponse(BaseModel):
    asin: str
    records: List[PriceRecordResponse]
    stats: Optional[PriceStats] = None


class ProfitEstimateRequest(BaseModel):
    sale_price: float = Field(..., gt=0)
    cost: float = Field(..., gt=0)


class ProfitEstimateResponse(BaseModel):
    sale_price: float
    cost: float
    referral_fee: float
    fba_fee: float
    total_fees: float
    profit: float
    roi: float
    margin: float


# --- Deals ---

class DealResponse(BaseModel):
    id: int
    asin: str
    deal_type: str
    trigger_price: Optional[float]
    reference_price: Optional[float]
    drop_percent: Optional[float]
    estimated_profit: Optional[float]
    estimated_roi: Optional[float]
    is_active: bool
    detected_at: Optional[datetime]
    product_title: str = ""

    model_config = {"from_attributes": True}


class DealScanResponse(BaseModel):
    checked: int
    deals_found: int
    results: List[Dict]


class DealDismissResponse(BaseModel):
    deal_id: int
    dismissed: bool


# --- Health ---

class HealthResponse(BaseModel):
    status: str
    paapi_configured: bool
    keepa_configured: bool
    monitored_products: int
    active_deals: int
