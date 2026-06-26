"""Aplicação FastAPI: healthcheck + API REST (auth, CRUDs, métricas, imposto).

Importação/exportação CSV chegam na Fase 4; frontend na Fase 3.
"""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import (
    apartamentos,
    auth,
    despesas,
    exportacao,
    importacao,
    imposto,
    metricas,
    parametros_ir,
    reservas,
)

settings = get_settings()

app = FastAPI(
    title="Gestão de Locação de Temporada",
    description=(
        "Métricas operacionais, financeiras e tributárias (Carnê-Leão) para "
        "locação de temporada. Autenticação via JWT (Bearer)."
    ),
    version="0.2.0",
)

# CORS liberado para o frontend (Vite). Em produção, restrinja a origem.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    """Erros de regra de negócio viram 422 com mensagem clara em pt-BR."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


@app.get("/api/health", tags=["infra"])
def health() -> dict[str, str]:
    """Healthcheck para o Railway."""
    return {"status": "ok", "env": settings.env}


for r in (
    auth.router,
    apartamentos.router,
    reservas.router,
    despesas.router,
    metricas.router,
    imposto.router,
    parametros_ir.router,
    importacao.router,
    exportacao.router,
):
    app.include_router(r)
