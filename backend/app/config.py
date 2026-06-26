"""Configuração da aplicação via variáveis de ambiente."""
from __future__ import annotations

import os
from functools import lru_cache
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Configurações lidas do ambiente (com defaults para dev local)."""

    database_url: str
    jwt_secret: str
    env: str
    tz: str
    frontend_dist: str

    @property
    def is_dev(self) -> bool:
        return self.env.lower() in {"dev", "development", "local"}


def _normalize_db_url(url: str) -> str:
    """Railway/Heroku expõem ``postgres://``; SQLAlchemy 2.0 quer ``postgresql+psycopg``."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=_normalize_db_url(
            os.getenv(
                "DATABASE_URL",
                "postgresql+psycopg://postgres:postgres@localhost:5432/airbnb",
            )
        ),
        jwt_secret=os.getenv("JWT_SECRET", "dev-insecure-secret-change-me"),
        env=os.getenv("ENV", "dev"),
        tz=os.getenv("TZ", "America/Sao_Paulo"),
        # Diretório do build do frontend a ser servido pela API (vazio = não servir).
        frontend_dist=os.getenv("FRONTEND_DIST", ""),
    )
