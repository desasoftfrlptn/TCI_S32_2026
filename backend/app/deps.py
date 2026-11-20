"""Dependencias de FastAPI: sesión, servicios y autenticación.

Auth stub (M4): el usuario se identifica con el header `X-Usuario`.
En M5 se reemplaza por autenticación real sin tocar las rutas, porque todas
dependen de `usuario_actual`.
"""

from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status
from sqlmodel import Session

from app.db import get_session
from app.models import Rol, Usuario
from app.notificaciones import Notificador, NotificadorLog
from app.repositorios import UsuarioRepo
from app.servicios import Servicios

_notificador = NotificadorLog()


def get_notificador() -> Notificador:
    return _notificador


def get_servicios(
    session: Session = Depends(get_session), notificador: Notificador = Depends(get_notificador)
) -> Servicios:
    return Servicios(session, notificador)


def usuario_actual(
    x_usuario: str | None = Header(default=None), session: Session = Depends(get_session)
) -> Usuario:
    usuario = UsuarioRepo(session).por_usuario(x_usuario) if x_usuario else None
    if not usuario:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no autenticado")
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
