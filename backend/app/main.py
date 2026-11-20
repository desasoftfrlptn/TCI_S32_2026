import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.config import CORS_ORIGINS
from app.deps import ENCARGADO, get_servicios, usuario_actual
from app.models import Rol, Usuario
from app.rutas import incidencias, maquinas, pedidos, reparaciones, repuestos
from app.schemas import Sesion, UsuarioLeer
from app.servicios import ErrorDominio, Servicios

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Planta en orden API",
    version="0.1.0",
    description="Gestión de stock y mantenimiento de planta. Autenticación: `POST /auth/login` → token Bearer.",
)
app.add_middleware(
    CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"]
)


@app.exception_handler(ErrorDominio)
def error_dominio(_: Request, error: ErrorDominio) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"detail": str(error)})


@app.get("/health", tags=["sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/login", response_model=Sesion, tags=["sistema"])
def login(form: OAuth2PasswordRequestForm = Depends(), servicios: Servicios = Depends(get_servicios)):
    usuario, token = servicios.autenticar(form.username, form.password)
    return Sesion(access_token=token, usuario=UsuarioLeer.model_validate(usuario))


@app.get("/me", response_model=UsuarioLeer, tags=["sistema"])
def yo(usuario: Usuario = Depends(usuario_actual)):
    return usuario


@app.get("/usuarios/delegables", response_model=list[UsuarioLeer], dependencies=[ENCARGADO], tags=["sistema"])
def usuarios_delegables(servicios: Servicios = Depends(get_servicios)):
    """Usuarios en los que el encargado puede delegar la recepción de una compra."""
    return servicios.usuarios.listar_por_rol(Rol.mantenimiento, Rol.encargado)


for modulo in (repuestos, maquinas, incidencias, reparaciones, pedidos):
    app.include_router(modulo.router)
