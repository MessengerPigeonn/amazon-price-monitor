from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db.database import init_db
from api.routes import products, prices, deals, exports, health


def setup_logging():
    from config.settings import LOGS_DIR
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOGS_DIR / "app.log"),
        ],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logging.getLogger(__name__).info("Initializing database...")
    init_db()
    logging.getLogger(__name__).info("Amazon Price Monitor started")
    yield
    logging.getLogger(__name__).info("Amazon Price Monitor shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Amazon Price Monitor",
        description="Monitor Amazon product prices, detect deals, and estimate profits",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(health.router)
    app.include_router(products.router)
    app.include_router(prices.router)
    app.include_router(deals.router)
    app.include_router(exports.router)

    return app
