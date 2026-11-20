import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import CORS_ORIGINS
from app.deps import usuario_actual
from app.models import Usuario
from app.rutas import incidencias, maquinas, pedidos, reparaciones, repuestos
from app.schemas import UsuarioLeer
from app.servicios import ErrorDominio

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Planta en orden API",
    version="0.1.0",
    description="Gestión de stock y mantenimiento de planta. Auth stub: header `X-Usuario`.",
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


@app.get("/me", response_model=UsuarioLeer, tags=["sistema"])
def yo(usuario: Usuario = Depends(usuario_actual)):
    return usuario


for modulo in (repuestos, maquinas, incidencias, reparaciones, pedidos):
    app.include_router(modulo.router)
