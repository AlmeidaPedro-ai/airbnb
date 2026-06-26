"""Dependências compartilhadas: sessão de banco e usuário autenticado."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario
from app.security import decodificar_token

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    cred: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> Usuario:
    """Valida o token Bearer e retorna o usuário ativo."""
    erro = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if cred is None or not cred.credentials:
        raise erro
    sub = decodificar_token(cred.credentials)
    if sub is None:
        raise erro
    try:
        usuario_id = int(sub)
    except (TypeError, ValueError):
        raise erro
    usuario = db.get(Usuario, usuario_id)
    if usuario is None or not usuario.ativo:
        raise erro
    return usuario


CurrentUser = Annotated[Usuario, Depends(get_current_user)]
