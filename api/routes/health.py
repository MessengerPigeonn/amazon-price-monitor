from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.schemas import HealthResponse
from clients.amazon_paapi import AmazonPAAPIClient
from clients.keepa_client import KeepaClient
from db.database import get_db
from db.repository import ProductRepository, DealRepository

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(session: Session = Depends(get_db)):
    product_repo = ProductRepository(session)
    deal_repo = DealRepository(session)

    paapi = AmazonPAAPIClient()
    keepa = KeepaClient()

    products = product_repo.get_all_active()
    deals = deal_repo.get_active()

    return HealthResponse(
        status="ok",
        paapi_configured=paapi.is_configured(),
        keepa_configured=keepa.is_configured(),
        monitored_products=len(products),
        active_deals=len(deals),
    )
