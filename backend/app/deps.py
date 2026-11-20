"""Dependencias de FastAPI: sesión, servicios, autenticación y autorización por rol."""

from collections.abc import Callable
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.config import NOTIFICADOR, SMTP_HOST, SMTP_PORT, SMTP_REMITENTE
from app.db import get_session
from app.models import Rol, Usuario
from app.notificaciones import Notificador, NotificadorLog, NotificadorSMTP
from app.reconocimiento import Reconocedor, ReconocedorCodigos
from app.repositorios import UsuarioRepo
from app.seguridad import usuario_del_token
from app.servicios import Servicios

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


@lru_cache
def get_notificador() -> Notificador:
    if NOTIFICADOR == "smtp":
        return NotificadorSMTP(SMTP_HOST, SMTP_PORT, SMTP_REMITENTE)
    return NotificadorLog()


def get_reconocedor() -> Reconocedor:
    return ReconocedorCodigos()


def get_servicios(
    session: Session = Depends(get_session),
    notificador: Notificador = Depends(get_notificador),
    reconocedor: Reconocedor = Depends(get_reconocedor),
) -> Servicios:
    return Servicios(session, notificador, reconocedor)


def usuario_actual(token: str | None = Depends(oauth2), session: Session = Depends(get_session)) -> Usuario:
    nombre = usuario_del_token(token) if token else None
    usuario = UsuarioRepo(session).por_usuario(nombre) if nombre else None
    if not usuario:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Sesión inválida o vencida", headers={"WWW-Authenticate": "Bearer"}
        )
    return usuario


def requiere_rol(*roles: Rol) -> Callable[[Usuario], Usuario]:
    def verificar(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Tu rol no permite esta operación")
        return usuario

    return verificar


# Grupos de roles reutilizados por las rutas.
CUALQUIERA = Depends(usuario_actual)
STOCK = Depends(requiere_rol(Rol.mantenimiento, Rol.encargado))
REPORTE = Depends(requiere_rol(Rol.operario, Rol.mantenimiento, Rol.encargado))
ENCARGADO = Depends(requiere_rol(Rol.encargado))
SUPERVISION = Depends(requiere_rol(Rol.encargado, Rol.gerencia))
