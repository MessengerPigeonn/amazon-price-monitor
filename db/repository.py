from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from db.models import Product, PriceRecord, Deal, Alert


class ProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_asin(self, asin: str) -> Product | None:
        return self.session.execute(
            select(Product).where(Product.asin == asin)
        ).scalar_one_or_none()

    def get_all_active(self) -> Sequence[Product]:
        return self.session.execute(
            select(Product).where(Product.is_active.is_(True))
        ).scalars().all()

    def list_all(self, skip: int = 0, limit: int = 100) -> Sequence[Product]:
        return self.session.execute(
            select(Product).offset(skip).limit(limit)
        ).scalars().all()

    def create(self, **kwargs) -> Product:
        product = Product(**kwargs)
        self.session.add(product)
        self.session.commit()
        self.session.refresh(product)
        return product

    def upsert(self, asin: str, **kwargs) -> Product:
        product = self.get_by_asin(asin)
        if product:
            for k, v in kwargs.items():
                if v is not None:
                    setattr(product, k, v)
            product.updated_at = datetime.utcnow()
            self.session.commit()
            self.session.refresh(product)
            return product
        return self.create(asin=asin, **kwargs)

    def deactivate(self, asin: str) -> bool:
        result = self.session.execute(
            update(Product).where(Product.asin == asin).values(is_active=False)
        )
        self.session.commit()
        return result.rowcount > 0


class PriceRecordRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, **kwargs) -> PriceRecord:
        record = PriceRecord(**kwargs)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_history(self, asin: str, limit: int = 100) -> Sequence[PriceRecord]:
        return self.session.execute(
            select(PriceRecord)
            .where(PriceRecord.asin == asin)
            .order_by(PriceRecord.checked_at.desc())
            .limit(limit)
        ).scalars().all()

    def get_latest(self, asin: str) -> PriceRecord | None:
        return self.session.execute(
            select(PriceRecord)
            .where(PriceRecord.asin == asin)
            .order_by(PriceRecord.checked_at.desc())
            .limit(1)
        ).scalar_one_or_none()


class DealRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, **kwargs) -> Deal:
        deal = Deal(**kwargs)
        self.session.add(deal)
        self.session.commit()
        self.session.refresh(deal)
        return deal

    def get_active(
        self,
        deal_type: str | None = None,
        min_roi: float | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Deal]:
        stmt = select(Deal).where(Deal.is_active.is_(True))
        if deal_type:
            stmt = stmt.where(Deal.deal_type == deal_type)
        if min_roi is not None:
            stmt = stmt.where(Deal.estimated_roi >= min_roi)
        stmt = stmt.order_by(Deal.detected_at.desc()).offset(skip).limit(limit)
        return self.session.execute(stmt).scalars().all()

    def dismiss(self, deal_id: int) -> bool:
        result = self.session.execute(
            update(Deal)
            .where(Deal.id == deal_id)
            .values(is_active=False, dismissed_at=datetime.utcnow())
        )
        self.session.commit()
        return result.rowcount > 0

    def deactivate_for_asin(self, asin: str):
        self.session.execute(
            update(Deal)
            .where(Deal.asin == asin, Deal.is_active.is_(True))
            .values(is_active=False, dismissed_at=datetime.utcnow())
        )
        self.session.commit()


class AlertRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, **kwargs) -> Alert:
        alert = Alert(**kwargs)
        self.session.add(alert)
        self.session.commit()
        self.session.refresh(alert)
        return alert

    def exists(self, asin: str, deal_id: int, alert_type: str) -> bool:
        result = self.session.execute(
            select(Alert).where(
                Alert.asin == asin,
                Alert.deal_id == deal_id,
                Alert.alert_type == alert_type,
            )
        ).scalar_one_or_none()
        return result is not None

    def get_for_asin(self, asin: str, limit: int = 50) -> Sequence[Alert]:
        return self.session.execute(
            select(Alert)
            .where(Alert.asin == asin)
            .order_by(Alert.sent_at.desc())
            .limit(limit)
        ).scalars().all()
