from fastapi import APIRouter, Depends, HTTPException

from app.deps import CUALQUIERA, ENCARGADO, get_servicios
from app.models import Maquina, Usuario
from app.schemas import MaquinaCrear, MaquinaLeer
from app.servicios import Servicios

router = APIRouter(tags=["máquinas"])


@router.get("/maquinas", response_model=list[MaquinaLeer], dependencies=[CUALQUIERA])
def listar_maquinas(servicios: Servicios = Depends(get_servicios)):
    return servicios.maquinas.listar(Maquina)


@router.get("/maquinas/codigo/{codigo}", response_model=MaquinaLeer, dependencies=[CUALQUIERA])
def maquina_por_codigo(codigo: str, servicios: Servicios = Depends(get_servicios)):
    """Lo que devuelve el escaneo del QR/código de barras de la máquina."""
    maquina = servicios.maquinas.por_codigo(codigo)
    if not maquina:
        raise HTTPException(404, "Máquina no encontrada")
    return maquina


@router.post("/maquinas", response_model=MaquinaLeer, status_code=201)
def crear_maquina(datos: MaquinaCrear, _: Usuario = ENCARGADO, servicios: Servicios = Depends(get_servicios)):
    return servicios.crear_maquina(datos)
