"""Aplicação FastAPI. Na Fase 1 expõe apenas o healthcheck.

Os endpoints REST (apartamentos, reservas, despesas, métricas, imposto,
importação/exportação) chegam na Fase 2.
"""
from __future__ import annotations

from fastapi import FastAPI

from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Gestão de Locação de Temporada",
    description="Métricas operacionais, financeiras e tributárias (Carnê-Leão).",
    version="0.1.0",
)


@app.get("/api/health", tags=["infra"])
def health() -> dict[str, str]:
    """Healthcheck para o Railway."""
    return {"status": "ok", "env": settings.env}
