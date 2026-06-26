"""Segurança: hash de senha (bcrypt) e tokens JWT."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24h

# bcrypt usa no máximo 72 bytes da senha; truncamos explicitamente para evitar
# erro com versões recentes da lib.
_BCRYPT_MAX_BYTES = 72


def _to_bytes(senha: str) -> bytes:
    return senha.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_senha(senha: str) -> str:
    """Gera o hash bcrypt da senha (string utf-8 armazenável no banco)."""
    return bcrypt.hashpw(_to_bytes(senha), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Confere a senha contra o hash. Retorna False para hashes inválidos."""
    try:
        return bcrypt.checkpw(_to_bytes(senha), senha_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def criar_access_token(
    sub: str, expires_delta: timedelta | None = None
) -> str:
    """Cria um JWT assinado com ``sub`` (identificador do usuário)."""
    settings = get_settings()
    expira = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": sub, "exp": expira}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decodificar_token(token: str) -> str | None:
    """Retorna o ``sub`` do token válido, ou None se inválido/expirado."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        return None
    return payload.get("sub")
