from __future__ import annotations

import logging
from typing import Any

from clients.base import BaseClient, RateLimiter
from config.settings import get_settings

logger = logging.getLogger(__name__)

# PA-API batch limit
MAX_BATCH_SIZE = 10


def _chunks(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


class AmazonPAAPIClient(BaseClient):
    """Wrapper around Amazon Product Advertising API 5.0."""

    def __init__(self):
        settings = get_settings().amazon
        self.access_key = settings.access_key
        self.secret_key = settings.secret_key
        self.partner_tag = settings.partner_tag
        self.marketplace = settings.marketplace
        self._api = None

        rate_limiter = RateLimiter(
            max_calls=settings.requests_per_second, period_seconds=1.0
        )
        super().__init__(rate_limiter)

    def is_configured(self) -> bool:
        return bool(self.access_key and self.secret_key and self.partner_tag)

    def _get_api(self):
        if self._api is None:
            try:
                from amazon_paapi import AmazonAPI

                self._api = AmazonAPI(
                    self.access_key,
                    self.secret_key,
                    self.partner_tag,
                    country=self._country_code(),
                )
            except ImportError:
                raise RuntimeError(
                    "python-amazon-paapi is not installed. Run: pip install python-amazon-paapi"
                )
        return self._api

    def _country_code(self) -> str:
        mapping = {
            "www.amazon.com": "US",
            "www.amazon.co.uk": "UK",
            "www.amazon.de": "DE",
            "www.amazon.ca": "CA",
        }
        return mapping.get(self.marketplace, "US")

    def get_items(self, asins: list[str]) -> list[dict[str, Any]]:
        if not self.is_configured():
            logger.warning("PA-API not configured, skipping")
            return []

        api = self._get_api()
        results = []

        for batch in _chunks(asins, MAX_BATCH_SIZE):
            self._rate_limit_sync()
            try:
                items = api.get_items(batch)
                for item in items:
                    results.append(self._parse_item(item))
            except Exception as e:
                logger.error(f"PA-API get_items error: {e}")

        return results

    def search_items(self, keywords: str, max_results: int = 10) -> list[dict[str, Any]]:
        if not self.is_configured():
            logger.warning("PA-API not configured, skipping")
            return []

        api = self._get_api()
        self._rate_limit_sync()

        try:
            results = api.search_items(keywords=keywords, item_count=min(max_results, 10))
            return [self._parse_item(item) for item in results]
        except Exception as e:
            logger.error(f"PA-API search error: {e}")
            return []

    def _parse_item(self, item: Any) -> dict[str, Any]:
        """Parse a PA-API item response into a flat dict."""
        data: dict[str, Any] = {
            "asin": getattr(item, "asin", ""),
            "title": "",
            "brand": "",
            "category": "",
            "image_url": "",
            "current_price": None,
            "list_price": None,
            "buy_box_price": None,
            "savings_percent": None,
            "sales_rank": None,
            "deal_details": None,
        }

        # Title
        info = getattr(item, "item_info", None)
        if info:
            title_obj = getattr(info, "title", None)
            if title_obj:
                data["title"] = getattr(title_obj, "display_value", "") or ""

            by_line = getattr(info, "by_line_info", None)
            if by_line:
                brand_obj = getattr(by_line, "brand", None)
                if brand_obj:
                    data["brand"] = getattr(brand_obj, "display_value", "") or ""

            classifications = getattr(info, "classifications", None)
            if classifications:
                binding = getattr(classifications, "binding", None)
                if binding:
                    data["category"] = getattr(binding, "display_value", "") or ""

        # Images
        images = getattr(item, "images", None)
        if images:
            primary = getattr(images, "primary", None)
            if primary:
                large = getattr(primary, "large", None)
                if large:
                    data["image_url"] = getattr(large, "url", "") or ""

        # Offers / pricing
        offers = getattr(item, "offers", None)
        if offers:
            listings = getattr(offers, "listings", None)
            if listings and len(listings) > 0:
                listing = listings[0]
                price_obj = getattr(listing, "price", None)
                if price_obj:
                    amount = getattr(price_obj, "amount", None)
                    data["current_price"] = float(amount) if amount is not None else None

                    savings = getattr(price_obj, "savings", None)
                    if savings:
                        pct = getattr(savings, "percentage", None)
                        data["savings_percent"] = float(pct) if pct is not None else None

                saving_basis = getattr(listing, "saving_basis", None)
                if saving_basis:
                    amount = getattr(saving_basis, "amount", None)
                    data["list_price"] = float(amount) if amount is not None else None

            # Buy box
            data["buy_box_price"] = data["current_price"]

        # Sales rank
        browse_nodes = getattr(item, "browse_node_info", None)
        if browse_nodes:
            sales_rank_obj = getattr(browse_nodes, "website_sales_rank", None)
            if sales_rank_obj:
                data["sales_rank"] = getattr(sales_rank_obj, "sales_rank", None)

        return data
