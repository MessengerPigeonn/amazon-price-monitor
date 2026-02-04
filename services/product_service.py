from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from clients.amazon_paapi import AmazonPAAPIClient
from clients.keepa_client import KeepaClient
from db.repository import ProductRepository, PriceRecordRepository, DealRepository
from services.price_analyzer import PriceAnalyzer
from services.alert_service import AlertService

logger = logging.getLogger(__name__)


class ProductService:
    """Orchestrator: fetch data from APIs, merge, analyze, store."""

    def __init__(self, session: Session):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.price_repo = PriceRecordRepository(session)
        self.deal_repo = DealRepository(session)
        self.paapi = AmazonPAAPIClient()
        self.keepa = KeepaClient()
        self.analyzer = PriceAnalyzer()
        self.alert_service = AlertService(session)

    def add_product(self, asin: str, label: str = "", target_buy_price: float | None = None) -> dict[str, Any]:
        """Add a product to monitoring and do an initial price check."""
        product = self.product_repo.upsert(
            asin=asin,
            label=label,
            target_buy_price=target_buy_price,
            is_active=True,
            source="manual",
        )
        # Do initial check
        results = self.check_asins([asin])
        return {
            "asin": product.asin,
            "title": product.title,
            "label": product.label,
            "checked": len(results) > 0,
        }

    def check_asins(self, asins: list[str]) -> list[dict[str, Any]]:
        """Fetch current prices, merge with Keepa data, detect deals."""
        results = []

        # Fetch from PA-API
        paapi_items = self.paapi.get_items(asins) if self.paapi.is_configured() else []
        paapi_map = {item["asin"]: item for item in paapi_items}

        # Fetch from Keepa
        keepa_items = self.keepa.get_product_data(asins) if self.keepa.is_configured() else []
        keepa_map = {item["asin"]: item for item in keepa_items}

        for asin in asins:
            paapi_data = paapi_map.get(asin, {})
            keepa_data = keepa_map.get(asin, {})

            # Merge into product record
            if paapi_data:
                self.product_repo.upsert(
                    asin=asin,
                    title=paapi_data.get("title"),
                    brand=paapi_data.get("brand"),
                    category=paapi_data.get("category"),
                    image_url=paapi_data.get("image_url"),
                )

            # Build price record
            price_data = {
                "asin": asin,
                "current_price": paapi_data.get("current_price"),
                "list_price": paapi_data.get("list_price"),
                "buy_box_price": paapi_data.get("buy_box_price"),
                "savings_percent": paapi_data.get("savings_percent"),
                "sales_rank": paapi_data.get("sales_rank"),
                "avg_30d": keepa_data.get("avg_30d"),
                "avg_90d": keepa_data.get("avg_90d"),
                "avg_180d": keepa_data.get("avg_180d"),
                "all_time_low": keepa_data.get("all_time_low"),
                "all_time_high": keepa_data.get("all_time_high"),
                "source": "paapi+keepa" if paapi_data and keepa_data else ("paapi" if paapi_data else "keepa"),
            }

            if price_data["current_price"] is not None:
                self.price_repo.add(**price_data)

            # Get previous record for comparison
            previous_record = self.price_repo.get_latest(asin)
            prev_data = None
            if previous_record:
                prev_data = {"current_price": previous_record.current_price}

            # Detect deals
            product = self.product_repo.get_by_asin(asin)
            target = product.target_buy_price if product else None

            signals = self.analyzer.detect_deals(
                current={**paapi_data, **keepa_data},
                previous=prev_data,
                keepa_data=keepa_data or None,
                target_buy_price=target,
            )

            # Deactivate old deals and create new ones
            if signals:
                self.deal_repo.deactivate_for_asin(asin)
                for signal in signals:
                    deal = self.deal_repo.create(
                        asin=asin,
                        deal_type=signal.deal_type,
                        trigger_price=signal.trigger_price,
                        reference_price=signal.reference_price,
                        drop_percent=signal.drop_percent,
                        estimated_profit=signal.estimated_profit,
                        estimated_roi=signal.estimated_roi,
                    )
                    self.alert_service.process_deal(asin, deal)

            results.append({
                "asin": asin,
                "price": price_data["current_price"],
                "deals_found": len(signals),
            })

        return results

    def check_all_active(self) -> list[dict[str, Any]]:
        """Check prices for all active monitored products."""
        products = self.product_repo.get_all_active()
        asins = [p.asin for p in products]
        if not asins:
            logger.info("No active products to check")
            return []
        logger.info(f"Checking {len(asins)} active products")
        return self.check_asins(asins)

    def search_products(self, keywords: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Search Amazon via PA-API."""
        return self.paapi.search_items(keywords, max_results)
