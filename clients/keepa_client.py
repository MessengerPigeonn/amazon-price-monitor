from __future__ import annotations

import logging
from typing import Any

from clients.base import BaseClient, RateLimiter
from config.settings import get_settings

logger = logging.getLogger(__name__)


class KeepaClient(BaseClient):
    """Wrapper around the Keepa API for historical price data."""

    def __init__(self):
        settings = get_settings().keepa
        self.api_key = settings.api_key
        self.domain = settings.domain
        self._api = None

        rate_limiter = RateLimiter(
            max_calls=settings.requests_per_minute, period_seconds=60.0
        )
        super().__init__(rate_limiter)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _get_api(self):
        if self._api is None:
            try:
                import keepa

                self._api = keepa.Keepa(self.api_key)
            except ImportError:
                raise RuntimeError("keepa is not installed. Run: pip install keepa")
        return self._api

    def get_product_data(self, asins: list[str]) -> list[dict[str, Any]]:
        if not self.is_configured():
            logger.warning("Keepa not configured, skipping")
            return []

        self._rate_limit_sync()
        api = self._get_api()

        try:
            products = api.query(asins, domain=self.domain, stats=180)
            return [self._parse_product(p) for p in products]
        except Exception as e:
            logger.error(f"Keepa query error: {e}")
            return []

    def get_deals(self, price_types: list[int] | None = None, count: int = 50) -> list[dict[str, Any]]:
        if not self.is_configured():
            logger.warning("Keepa not configured, skipping")
            return []

        self._rate_limit_sync()
        api = self._get_api()

        try:
            deal_params = {
                "domainId": self.domain,
                "page": 0,
                "priceTypes": price_types or [0],  # 0 = Amazon price
            }
            deals = api.deals(deal_params)
            results = []
            for d in deals[:count]:
                results.append({
                    "asin": d.get("asin", ""),
                    "title": d.get("title", ""),
                    "current_price": d.get("current", [None])[0],
                    "deal_type": "keepa_deal",
                })
            return results
        except Exception as e:
            logger.error(f"Keepa deals error: {e}")
            return []

    def _parse_product(self, product: dict[str, Any]) -> dict[str, Any]:
        """Extract useful stats from a Keepa product response."""
        data: dict[str, Any] = {
            "asin": product.get("asin", ""),
            "title": product.get("title", ""),
            "avg_30d": None,
            "avg_90d": None,
            "avg_180d": None,
            "all_time_low": None,
            "all_time_high": None,
        }

        stats = product.get("stats", None)
        if stats is None:
            return data

        # Current price stats (index 0 = Amazon price)
        # stats.avg contains [avg_Amazon, avg_new, avg_used, ...]
        avg = stats.get("avg", [])
        if len(avg) > 0 and avg[0] is not None and avg[0] > 0:
            # Keepa prices are in cents for some domains
            data["avg_180d"] = self._to_price(avg[0])

        avg30 = stats.get("avg30", [])
        if len(avg30) > 0 and avg30[0] is not None and avg30[0] > 0:
            data["avg_30d"] = self._to_price(avg30[0])

        avg90 = stats.get("avg90", [])
        if len(avg90) > 0 and avg90[0] is not None and avg90[0] > 0:
            data["avg_90d"] = self._to_price(avg90[0])

        min_prices = stats.get("min", [])
        if len(min_prices) > 0 and min_prices[0] is not None and min_prices[0] > 0:
            data["all_time_low"] = self._to_price(min_prices[0])

        max_prices = stats.get("max", [])
        if len(max_prices) > 0 and max_prices[0] is not None and max_prices[0] > 0:
            data["all_time_high"] = self._to_price(max_prices[0])

        return data

    def _to_price(self, keepa_val: int | float) -> float:
        """Convert Keepa price value to dollars. Keepa stores US prices in cents."""
        if self.domain == 1:  # US
            return round(keepa_val / 100.0, 2)
        return round(float(keepa_val) / 100.0, 2)
