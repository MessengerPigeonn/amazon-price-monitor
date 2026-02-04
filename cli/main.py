from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import typer
import uvicorn

from config.settings import get_settings
from db.database import init_db, get_session_factory
from services.product_service import ProductService
from services.export_service import ExportService

app = typer.Typer(
    name="amazon-price-monitor",
    help="Monitor Amazon product prices and detect deals.",
)


@app.command()
def check(asins: list[str] = typer.Argument(..., help="One or more ASINs to check")):
    """One-shot price check for specific ASINs."""
    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        service = ProductService(session)
        results = service.check_asins(asins)
        for r in results:
            deals_info = f", {r['deals_found']} deal(s) found" if r.get("deals_found") else ""
            price_str = f"${r['price']:.2f}" if r.get("price") is not None else "N/A"
            typer.echo(f"  {r['asin']}: {price_str}{deals_info}")
    finally:
        session.close()


@app.command()
def search(keywords: str = typer.Argument(..., help="Search keywords")):
    """Search Amazon for products."""
    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        service = ProductService(session)
        results = service.search_products(keywords)
        if not results:
            typer.echo("No results found.")
            return
        for r in results:
            price_str = f"${r['current_price']:.2f}" if r.get("current_price") else "N/A"
            typer.echo(f"  {r.get('asin', 'N/A')}: {r.get('title', '')[:60]} - {price_str}")
    finally:
        session.close()


@app.command()
def deals(
    deal_type: str = typer.Option(None, help="Filter by deal type"),
    min_roi: float = typer.Option(None, help="Minimum ROI percentage"),
):
    """Show active deals."""
    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        from db.repository import DealRepository, ProductRepository

        deal_repo = DealRepository(session)
        product_repo = ProductRepository(session)
        active_deals = deal_repo.get_active(deal_type=deal_type, min_roi=min_roi)

        if not active_deals:
            typer.echo("No active deals.")
            return

        for d in active_deals:
            product = product_repo.get_by_asin(d.asin)
            title = product.title[:40] if product and product.title else d.asin
            price_str = f"${d.trigger_price:.2f}" if d.trigger_price else "N/A"
            drop_str = f" ({d.drop_percent:.1f}% off)" if d.drop_percent else ""
            roi_str = f" ROI:{d.estimated_roi:.1f}%" if d.estimated_roi else ""
            typer.echo(f"  [{d.deal_type}] {title}: {price_str}{drop_str}{roi_str}")
    finally:
        session.close()


@app.command()
def export(
    format: str = typer.Option("json", help="Export format: json or csv"),
    save: bool = typer.Option(False, help="Save to file"),
):
    """Export monitored data."""
    init_db()
    factory = get_session_factory()
    session = factory()
    try:
        service = ExportService(session)
        if format == "csv":
            data = service.export_csv(save_to_file=save)
        else:
            data = service.export_json(save_to_file=save)
        typer.echo(data)
    finally:
        session.close()


@app.command()
def serve(
    host: str = typer.Option(None, help="Host to bind to"),
    port: int = typer.Option(None, help="Port to listen on"),
):
    """Start the FastAPI server."""
    settings = get_settings().server
    uvicorn.run(
        "api.app:create_app",
        factory=True,
        host=host or settings.host,
        port=port or settings.port,
        reload=settings.reload,
    )


@app.command()
def run(
    host: str = typer.Option(None, help="Host to bind to"),
    port: int = typer.Option(None, help="Port to listen on"),
):
    """Start scheduler + FastAPI server."""
    from api.app import setup_logging

    setup_logging()
    init_db()

    from services.scheduler import start_scheduler

    start_scheduler()

    settings = get_settings().server
    uvicorn.run(
        "api.app:create_app",
        factory=True,
        host=host or settings.host,
        port=port or settings.port,
        reload=settings.reload,
    )


if __name__ == "__main__":
    app()
