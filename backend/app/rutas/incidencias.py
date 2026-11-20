from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import UPLOAD_DIR
from app.deps import CUALQUIERA, REPORTE, get_servicios
from app.models import FotoIncidencia, Incidencia, Usuario
from app.schemas import FotoLeer, IncidenciaCrear, IncidenciaLeer
from app.servicios import Servicios

router = APIRouter(tags=["incidencias"])


@router.get("/incidencias", response_model=list[IncidenciaLeer], dependencies=[CUALQUIERA])
def listar_incidencias(servicios: Servicios = Depends(get_servicios)):
    return servicios.incidencias.listar(Incidencia)


@router.get("/incidencias/{incidencia_id}", response_model=IncidenciaLeer, dependencies=[CUALQUIERA])
def obtener_incidencia(incidencia_id: int, servicios: Servicios = Depends(get_servicios)):
    incidencia = servicios.incidencias.obtener(Incidencia, incidencia_id)
    if not incidencia:
        raise HTTPException(404, "Incidencia no encontrada")
    return incidencia


@router.post("/incidencias", response_model=IncidenciaLeer, status_code=201)
def reportar_incidencia(
    datos: IncidenciaCrear, usuario: Usuario = REPORTE, servicios: Servicios = Depends(get_servicios)
):
    return servicios.crear_incidencia(datos, usuario)


@router.get("/incidencias/{incidencia_id}/fotos", response_model=list[FotoLeer], dependencies=[CUALQUIERA])
def listar_fotos(incidencia_id: int, servicios: Servicios = Depends(get_servicios)):
    return servicios.incidencias.fotos(incidencia_id)


@router.post("/incidencias/{incidencia_id}/fotos", response_model=FotoLeer, status_code=201, dependencies=[REPORTE])
def subir_foto(incidencia_id: int, foto: UploadFile, servicios: Servicios = Depends(get_servicios)):
    return servicios.agregar_foto(incidencia_id, foto.file.read(), foto.content_type or "")


@router.get("/fotos/{foto_id}", dependencies=[CUALQUIERA])
def descargar_foto(foto_id: int, servicios: Servicios = Depends(get_servicios)):
    foto = servicios.incidencias.obtener(FotoIncidencia, foto_id)
    if not foto:
        raise HTTPException(404, "Foto no encontrada")
    return FileResponse(Path(UPLOAD_DIR) / foto.archivo, media_type=foto.tipo_contenido)
