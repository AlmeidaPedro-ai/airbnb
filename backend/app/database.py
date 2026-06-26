"""Configuração do SQLAlchemy 2.0 (engine, session, Base declarativa)."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base declarativa de todos os modelos."""


_settings = get_settings()
engine = create_engine(_settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dependência FastAPI: fornece uma sessão por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
