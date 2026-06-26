"""Autenticação (login JWT)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import Usuario
from app.schemas import LoginRequest, TokenResponse, UsuarioOut
from app.security import criar_access_token, verificar_senha

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(dados: LoginRequest, db: DbSession) -> TokenResponse:
    """Autentica por email/senha e devolve um JWT."""
    usuario = db.scalar(select(Usuario).where(Usuario.email == dados.email))
    if (
        usuario is None
        or not usuario.ativo
        or not verificar_senha(dados.senha, usuario.senha_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
        )
    token = criar_access_token(sub=str(usuario.id))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UsuarioOut)
def me(usuario: CurrentUser) -> Usuario:
    """Dados do usuário autenticado."""
    return usuario
