from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import DealResponse, DealScanResponse, DealDismissResponse
from api.dependencies import get_product_service
from db.database import get_db
from db.repository import DealRepository, ProductRepository
from services.product_service import ProductService

router = APIRouter(prefix="/api/v1/deals", tags=["deals"])


@router.get("", response_model=List[DealResponse])
def list_active_deals(
    deal_type: Optional[str] = None,
    min_roi: Optional[float] = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_db),
):
    deal_repo = DealRepository(session)
    product_repo = ProductRepository(session)
    deals = deal_repo.get_active(deal_type=deal_type, min_roi=min_roi, skip=skip, limit=limit)

    results = []
    for deal in deals:
        product = product_repo.get_by_asin(deal.asin)
        results.append(DealResponse(
            id=deal.id,
            asin=deal.asin,
            deal_type=deal.deal_type,
            trigger_price=deal.trigger_price,
            reference_price=deal.reference_price,
            drop_percent=deal.drop_percent,
            estimated_profit=deal.estimated_profit,
            estimated_roi=deal.estimated_roi,
            is_active=deal.is_active,
            detected_at=deal.detected_at,
            product_title=product.title if product else "",
        ))
    return results


@router.post("/scan", response_model=DealScanResponse)
def scan_for_deals(service: ProductService = Depends(get_product_service)):
    results = service.check_all_active()
    total_deals = sum(r.get("deals_found", 0) for r in results)
    return DealScanResponse(
        checked=len(results),
        deals_found=total_deals,
        results=results,
    )


@router.post("/{deal_id}/dismiss", response_model=DealDismissResponse)
def dismiss_deal(deal_id: int, session: Session = Depends(get_db)):
    deal_repo = DealRepository(session)
    success = deal_repo.dismiss(deal_id)
    if not success:
        raise HTTPException(status_code=404, detail="Deal not found")
    return DealDismissResponse(deal_id=deal_id, dismissed=True)
