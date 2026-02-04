from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import ProductCreate, ProductResponse, ProductSearchRequest, ProductSearchResult
from api.dependencies import get_product_service
from db.database import get_db
from db.repository import ProductRepository
from services.product_service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.get("", response_model=List[ProductResponse])
def list_products(skip: int = 0, limit: int = 100, session: Session = Depends(get_db)):
    repo = ProductRepository(session)
    return repo.list_all(skip=skip, limit=limit)


@router.post("", response_model=dict)
def add_product(
    body: ProductCreate,
    service: ProductService = Depends(get_product_service),
):
    result = service.add_product(
        asin=body.asin,
        label=body.label,
        target_buy_price=body.target_buy_price,
    )
    return result


@router.post("/search", response_model=List[ProductSearchResult])
def search_products(
    body: ProductSearchRequest,
    service: ProductService = Depends(get_product_service),
):
    results = service.search_products(body.keywords, body.max_results)
    return [
        ProductSearchResult(
            asin=r.get("asin", ""),
            title=r.get("title", ""),
            brand=r.get("brand", ""),
            current_price=r.get("current_price"),
            image_url=r.get("image_url", ""),
        )
        for r in results
    ]


@router.get("/{asin}", response_model=ProductResponse)
def get_product(asin: str, session: Session = Depends(get_db)):
    repo = ProductRepository(session)
    product = repo.get_by_asin(asin)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.delete("/{asin}")
def deactivate_product(asin: str, session: Session = Depends(get_db)):
    repo = ProductRepository(session)
    if not repo.deactivate(asin):
        raise HTTPException(status_code=404, detail="Product not found")
    return {"asin": asin, "deactivated": True}
