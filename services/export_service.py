from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from config.settings import get_settings
from db.repository import ProductRepository, PriceRecordRepository, DealRepository

logger = logging.getLogger(__name__)


class ExportService:
    """JSON and CSV export of products, prices, and deals."""

    def __init__(self, session: Session):
        self.session = session
        self.product_repo = ProductRepository(session)
        self.price_repo = PriceRecordRepository(session)
        self.deal_repo = DealRepository(session)
        self.output_dir = Path(get_settings().export.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_json(self, save_to_file: bool = False) -> str:
        """Export all monitored data as JSON."""
        data = self._build_export_data()
        json_str = json.dumps(data, indent=2, default=str)

        if save_to_file:
            filename = f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            path = self.output_dir / filename
            path.write_text(json_str)
            logger.info(f"JSON exported to {path}")

        return json_str

    def export_csv(self, save_to_file: bool = False) -> str:
        """Export price records as CSV."""
        data = self._build_export_data()
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "asin", "title", "brand", "category", "label",
            "current_price", "list_price", "buy_box_price",
            "savings_percent", "sales_rank",
            "avg_30d", "avg_90d", "avg_180d",
            "all_time_low", "all_time_high",
            "checked_at", "active_deals",
        ])

        for product in data["products"]:
            latest = product.get("latest_price", {})
            deals = product.get("active_deals", [])
            deal_str = "; ".join(
                f"{d['deal_type']}({d.get('drop_percent', '')}%)" for d in deals
            )
            writer.writerow([
                product["asin"],
                product["title"],
                product["brand"],
                product["category"],
                product["label"],
                latest.get("current_price", ""),
                latest.get("list_price", ""),
                latest.get("buy_box_price", ""),
                latest.get("savings_percent", ""),
                latest.get("sales_rank", ""),
                latest.get("avg_30d", ""),
                latest.get("avg_90d", ""),
                latest.get("avg_180d", ""),
                latest.get("all_time_low", ""),
                latest.get("all_time_high", ""),
                latest.get("checked_at", ""),
                deal_str,
            ])

        csv_str = output.getvalue()

        if save_to_file:
            filename = f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            path = self.output_dir / filename
            path.write_text(csv_str)
            logger.info(f"CSV exported to {path}")

        return csv_str

    def _build_export_data(self) -> dict[str, Any]:
        products = self.product_repo.list_all(limit=10000)
        result: dict[str, Any] = {
            "exported_at": datetime.utcnow().isoformat(),
            "total_products": len(products),
            "products": [],
        }

        for product in products:
            latest = self.price_repo.get_latest(product.asin)
            deals = self.deal_repo.get_active(skip=0, limit=100)
            active_deals = [d for d in deals if d.asin == product.asin]

            product_data: dict[str, Any] = {
                "asin": product.asin,
                "title": product.title,
                "brand": product.brand,
                "category": product.category,
                "label": product.label,
                "target_buy_price": product.target_buy_price,
                "is_active": product.is_active,
                "latest_price": {},
                "active_deals": [],
            }

            if latest:
                product_data["latest_price"] = {
                    "current_price": latest.current_price,
                    "list_price": latest.list_price,
                    "buy_box_price": latest.buy_box_price,
                    "savings_percent": latest.savings_percent,
                    "sales_rank": latest.sales_rank,
                    "avg_30d": latest.avg_30d,
                    "avg_90d": latest.avg_90d,
                    "avg_180d": latest.avg_180d,
                    "all_time_low": latest.all_time_low,
                    "all_time_high": latest.all_time_high,
                    "checked_at": latest.checked_at.isoformat() if latest.checked_at else None,
                }

            for deal in active_deals:
                product_data["active_deals"].append({
                    "deal_type": deal.deal_type,
                    "trigger_price": deal.trigger_price,
                    "reference_price": deal.reference_price,
                    "drop_percent": deal.drop_percent,
                    "estimated_profit": deal.estimated_profit,
                    "estimated_roi": deal.estimated_roi,
                    "detected_at": deal.detected_at.isoformat() if deal.detected_at else None,
                })

            result["products"].append(product_data)

        return result
