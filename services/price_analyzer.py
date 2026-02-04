from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class DealSignal:
    deal_type: str
    trigger_price: float | None = None
    reference_price: float | None = None
    drop_percent: float | None = None
    estimated_profit: float | None = None
    estimated_roi: float | None = None


@dataclass
class ProfitEstimate:
    sale_price: float
    cost: float
    referral_fee: float
    fba_fee: float
    total_fees: float
    profit: float
    roi: float
    margin: float


class PriceAnalyzer:
    """Stateless deal detection and profit estimation."""

    def __init__(self):
        settings = get_settings().monitoring
        self.drop_threshold = settings.price_drop_threshold_percent
        self.clearance_keywords = settings.clearance_keywords
        self.min_savings = settings.min_savings_percent
        self.target_roi = settings.target_roi_percent
        self.fba_fee_pct = settings.fba_fee_percent / 100.0
        self.referral_fee_pct = settings.referral_fee_percent / 100.0

    def detect_deals(
        self,
        current: dict[str, Any],
        previous: dict[str, Any] | None = None,
        keepa_data: dict[str, Any] | None = None,
        target_buy_price: float | None = None,
    ) -> list[DealSignal]:
        """Analyze price data and return any detected deal signals."""
        signals: list[DealSignal] = []
        price = current.get("current_price")
        if price is None:
            return signals

        # 1. Price drop vs previous check
        if previous:
            prev_price = previous.get("current_price")
            if prev_price and prev_price > 0:
                drop_pct = ((prev_price - price) / prev_price) * 100
                if drop_pct >= self.drop_threshold:
                    signals.append(DealSignal(
                        deal_type="price_drop",
                        trigger_price=price,
                        reference_price=prev_price,
                        drop_percent=round(drop_pct, 1),
                    ))

        # 2. Clearance detection
        title = current.get("title", "").lower()
        is_clearance_keyword = any(kw in title for kw in self.clearance_keywords)
        savings = current.get("savings_percent") or 0
        if is_clearance_keyword or savings >= self.min_savings:
            list_price = current.get("list_price") or price
            signals.append(DealSignal(
                deal_type="clearance",
                trigger_price=price,
                reference_price=list_price,
                drop_percent=round(savings, 1) if savings else None,
            ))

        if keepa_data:
            # 3. Below average
            for period in ["avg_30d", "avg_90d", "avg_180d"]:
                avg = keepa_data.get(period)
                if avg and avg > 0 and price < avg:
                    drop = ((avg - price) / avg) * 100
                    if drop >= self.drop_threshold:
                        signals.append(DealSignal(
                            deal_type="below_average",
                            trigger_price=price,
                            reference_price=avg,
                            drop_percent=round(drop, 1),
                        ))
                        break  # One signal is enough

            # 4. All-time low
            atl = keepa_data.get("all_time_low")
            if atl and atl > 0 and price <= atl:
                signals.append(DealSignal(
                    deal_type="all_time_low",
                    trigger_price=price,
                    reference_price=atl,
                    drop_percent=0.0,
                ))

        # 5. Margin opportunity
        if target_buy_price is not None and price <= target_buy_price:
            # Use list price or a Keepa avg as the expected resale price
            resale_price = current.get("list_price")
            if not resale_price and keepa_data:
                resale_price = keepa_data.get("avg_90d")
            if resale_price and resale_price > price:
                estimate = self.estimate_profit(resale_price, price)
                if estimate.roi >= self.target_roi:
                    signals.append(DealSignal(
                        deal_type="margin_opportunity",
                        trigger_price=price,
                        reference_price=resale_price,
                        drop_percent=round(((resale_price - price) / resale_price) * 100, 1),
                        estimated_profit=estimate.profit,
                        estimated_roi=estimate.roi,
                    ))

        return signals

    def estimate_profit(self, sale_price: float, cost: float) -> ProfitEstimate:
        """Calculate estimated profit after Amazon fees."""
        referral_fee = round(sale_price * self.referral_fee_pct, 2)
        fba_fee = round(sale_price * self.fba_fee_pct, 2)
        total_fees = round(referral_fee + fba_fee, 2)
        profit = round(sale_price - cost - total_fees, 2)
        roi = round((profit / cost) * 100, 1) if cost > 0 else 0.0
        margin = round((profit / sale_price) * 100, 1) if sale_price > 0 else 0.0

        return ProfitEstimate(
            sale_price=sale_price,
            cost=cost,
            referral_fee=referral_fee,
            fba_fee=fba_fee,
            total_fees=total_fees,
            profit=profit,
            roi=roi,
            margin=margin,
        )
