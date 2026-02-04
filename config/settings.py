from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache
from typing import Any, Dict, List, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"


def _load_yaml(path: Path) -> dict[str, Any]:
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


class AmazonSettings(BaseSettings):
    access_key: str = ""
    secret_key: str = ""
    partner_tag: str = ""
    marketplace: str = "www.amazon.com"
    requests_per_second: float = 1.0


class KeepaSettings(BaseSettings):
    api_key: str = ""
    requests_per_minute: int = 60
    domain: int = 1  # 1 = .com


class DatabaseSettings(BaseSettings):
    url: str = f"sqlite:///{DATA_DIR / 'prices.db'}"
    echo: bool = False


class MonitoringSettings(BaseSettings):
    check_interval_minutes: int = 60
    price_drop_threshold_percent: float = 10.0
    clearance_keywords: List[str] = Field(
        default_factory=lambda: ["clearance", "closeout", "liquidation", "discontinued"]
    )
    min_savings_percent: float = 20.0
    target_roi_percent: float = 30.0
    fba_fee_percent: float = 15.0
    referral_fee_percent: float = 15.0


class ServerSettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False


class ExportSettings(BaseSettings):
    output_dir: str = str(DATA_DIR / "exports")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    amazon: AmazonSettings = Field(default_factory=AmazonSettings)
    keepa: KeepaSettings = Field(default_factory=KeepaSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    export: ExportSettings = Field(default_factory=ExportSettings)

    @classmethod
    def from_yaml_and_env(cls) -> Settings:
        yaml_data = _load_yaml(CONFIG_DIR / "config.yaml")
        env_file = BASE_DIR / ".env"
        os.environ.setdefault("ENV_FILE", str(env_file))
        return cls(**yaml_data)


class WatchlistItem:
    def __init__(self, asin: str = "", keywords: str = "", label: str = "",
                 target_buy_price: float | None = None):
        self.asin = asin
        self.keywords = keywords
        self.label = label
        self.target_buy_price = target_buy_price


def load_watchlist() -> list[WatchlistItem]:
    data = _load_yaml(CONFIG_DIR / "watchlist.yaml")
    items = []
    for entry in data.get("watchlist", []):
        items.append(WatchlistItem(**entry))
    return items


@lru_cache
def get_settings() -> Settings:
    return Settings.from_yaml_and_env()
