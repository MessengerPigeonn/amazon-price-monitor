from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from db.database import get_db
from services.product_service import ProductService
from services.price_analyzer import PriceAnalyzer
from services.export_service import ExportService


def get_product_service(session: Session = Depends(get_db)) -> ProductService:
    return ProductService(session)


def get_price_analyzer() -> PriceAnalyzer:
    return PriceAnalyzer()


def get_export_service(session: Session = Depends(get_db)) -> ExportService:
    return ExportService(session)
