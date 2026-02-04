from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.schemas import (
    PriceHistoryResponse,
    PriceRecordResponse,
    PriceStats,
    ProfitEstimateRequest,
    ProfitEstimateResponse,
)
from api.dependencies import get_price_analyzer
from db.database import get_db
from db.repository import PriceRecordRepository
from services.price_analyzer import PriceAnalyzer

router = APIRouter(prefix="/api/v1/prices", tags=["prices"])


@router.get("/{asin}/history", response_model=PriceHistoryResponse)
def get_price_history(asin: str, limit: int = 100, session: Session = Depends(get_db)):
    repo = PriceRecordRepository(session)
    records = repo.get_history(asin, limit=limit)

    stats = None
    prices = [r.current_price for r in records if r.current_price is not None]
    if prices:
        stats = PriceStats(
            min_price=min(prices),
            max_price=max(prices),
            avg_price=round(sum(prices) / len(prices), 2),
            record_count=len(prices),
        )

    return PriceHistoryResponse(
        asin=asin,
        records=[PriceRecordResponse.model_validate(r) for r in records],
        stats=stats,
    )


@router.post("/profit-estimate", response_model=ProfitEstimateResponse)
def estimate_profit(
    body: ProfitEstimateRequest,
    analyzer: PriceAnalyzer = Depends(get_price_analyzer),
):
    result = analyzer.estimate_profit(body.sale_price, body.cost)
    return ProfitEstimateResponse(
        sale_price=result.sale_price,
        cost=result.cost,
        referral_fee=result.referral_fee,
        fba_fee=result.fba_fee,
        total_fees=result.total_fees,
        profit=result.profit,
        roi=result.roi,
        margin=result.margin,
    )
