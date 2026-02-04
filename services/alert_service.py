from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from db.models import Deal
from db.repository import AlertRepository

logger = logging.getLogger(__name__)


class AlertService:
    """Threshold checking, deduplication, and logging for deal alerts."""

    def __init__(self, session: Session):
        self.alert_repo = AlertRepository(session)

    def process_deal(self, asin: str, deal: Deal):
        """Create an alert for a deal if not already sent."""
        alert_type = f"{deal.deal_type}_detected"

        if self.alert_repo.exists(asin, deal.id, alert_type):
            logger.debug(f"Alert already sent for {asin} deal #{deal.id}")
            return

        message = self._format_message(asin, deal)
        self.alert_repo.create(
            asin=asin,
            deal_id=deal.id,
            alert_type=alert_type,
            message=message,
        )
        logger.info(f"DEAL ALERT [{deal.deal_type}] {asin}: {message}")

    def _format_message(self, asin: str, deal: Deal) -> str:
        parts = [f"{deal.deal_type.upper()} for {asin}"]

        if deal.trigger_price is not None:
            parts.append(f"Price: ${deal.trigger_price:.2f}")

        if deal.reference_price is not None:
            parts.append(f"Reference: ${deal.reference_price:.2f}")

        if deal.drop_percent is not None:
            parts.append(f"Drop: {deal.drop_percent:.1f}%")

        if deal.estimated_profit is not None:
            parts.append(f"Est. Profit: ${deal.estimated_profit:.2f}")

        if deal.estimated_roi is not None:
            parts.append(f"ROI: {deal.estimated_roi:.1f}%")

        return " | ".join(parts)
