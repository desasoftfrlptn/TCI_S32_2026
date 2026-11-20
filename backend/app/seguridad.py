"""Autenticación: contraseñas con PBKDF2-SHA256 (biblioteca estándar) y tokens JWT."""

import base64
import hashlib
import hmac
import secrets
from datetime import timedelta

import jwt

from app.config import JWT_HORAS, JWT_SECRET, PBKDF2_ITERACIONES
from app.models import ahora

ALGORITMO = "HS256"


def hashear_password(password: str) -> str:
    sal = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), sal, PBKDF2_ITERACIONES)
    return "$".join(
        ["pbkdf2_sha256", str(PBKDF2_ITERACIONES), base64.b64encode(sal).decode(), base64.b64encode(digest).decode()]
    )


def verificar_password(password: str, guardado: str) -> bool:
    try:
        algoritmo, iteraciones, sal, digest = guardado.split("$")
    except ValueError:
        return False
    if algoritmo != "pbkdf2_sha256":
        return False
    calculado = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(sal), int(iteraciones))
    return hmac.compare_digest(calculado, base64.b64decode(digest))


def crear_token(usuario: str) -> str:
    """El token dura un turno (JWT_HORAS); `sub` es el nombre de usuario."""
    return jwt.encode({"sub": usuario, "exp": ahora() + timedelta(hours=JWT_HORAS)}, JWT_SECRET, ALGORITMO)


def usuario_del_token(token: str) -> str | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITMO]).get("sub")
    except jwt.PyJWTError:
        return None
