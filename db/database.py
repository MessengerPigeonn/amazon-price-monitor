from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config.settings import get_settings
from db.models import Base

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.database.url
        # Ensure data directory exists for SQLite
        if db_url.startswith("sqlite:///"):
            db_path = Path(db_url.replace("sqlite:///", ""))
            db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            db_url,
            echo=settings.database.echo,
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
        )
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _SessionLocal


def init_db():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
