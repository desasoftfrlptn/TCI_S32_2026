from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile

from app.deps import CUALQUIERA, ENCARGADO, STOCK, SUPERVISION, get_servicios
from app.models import Repuesto, Usuario
from app.schemas import (
    IngresoCrear,
    ItemListaCompras,
    MovimientoLeer,
    RepuestoCrear,
    RepuestoLeer,
    RequerimientoCrear,
    RequerimientoLeer,
)
from app.servicios import Servicios

router = APIRouter(tags=["repuestos"])


def _repuesto_o_404(repuesto: Repuesto | None) -> Repuesto:
    if not repuesto:
        raise HTTPException(404, "Repuesto no encontrado")
    return repuesto


@router.get("/repuestos", response_model=list[RepuestoLeer], dependencies=[CUALQUIERA])
def buscar_repuestos(q: str | None = None, servicios: Servicios = Depends(get_servicios)):
    """Consulta de existencia por nombre, descripción, código o nombre de máquina."""
    return servicios.repuestos.buscar(q)


@router.get("/repuestos/codigo/{codigo}", response_model=RepuestoLeer, dependencies=[CUALQUIERA])
def repuesto_por_codigo(codigo: str, servicios: Servicios = Depends(get_servicios)):
    """Lo que devuelve el escaneo del QR/código de barras del repuesto."""
    return _repuesto_o_404(servicios.repuestos.por_codigo(codigo))


@router.post("/repuestos/reconocer", response_model=RepuestoLeer, dependencies=[CUALQUIERA])
def reconocer_repuesto(foto: UploadFile, servicios: Servicios = Depends(get_servicios)):
    """Reconoce el repuesto a partir de una foto: nombre, código, máquinas, stock y ubicación."""
    return servicios.reconocer_repuesto(foto.file.read())


@router.get("/repuestos/{repuesto_id}", response_model=RepuestoLeer, dependencies=[CUALQUIERA])
def obtener_repuesto(repuesto_id: int, servicios: Servicios = Depends(get_servicios)):
    return _repuesto_o_404(servicios.repuestos.obtener(Repuesto, repuesto_id))


@router.get("/repuestos/{repuesto_id}/movimientos", response_model=list[MovimientoLeer], dependencies=[CUALQUIERA])
def historia_repuesto(repuesto_id: int, servicios: Servicios = Depends(get_servicios)):
    """RN-06: historia del repuesto (pedido → recepción → uso), en orden cronológico."""
    _repuesto_o_404(servicios.repuestos.obtener(Repuesto, repuesto_id))
    return servicios.repuestos.movimientos(repuesto_id)


@router.get("/movimientos", response_model=list[MovimientoLeer], dependencies=[CUALQUIERA])
def movimientos_recientes(limite: int = Query(default=10, ge=1, le=100), servicios: Servicios = Depends(get_servicios)):
    """Últimos movimientos de stock de toda la planta (tablero)."""
    return servicios.repuestos.movimientos_recientes(limite)


@router.post("/repuestos", response_model=RepuestoLeer, status_code=201)
def crear_repuesto(datos: RepuestoCrear, _: Usuario = ENCARGADO, servicios: Servicios = Depends(get_servicios)):
    return servicios.crear_repuesto(datos)


@router.post("/repuestos/{repuesto_id}/ingresos", response_model=RepuestoLeer)
def ingresar_stock(
    repuesto_id: int, datos: IngresoCrear, usuario: Usuario = STOCK, servicios: Servicios = Depends(get_servicios)
):
    return servicios.ingresar_stock(repuesto_id, datos, usuario)


@router.get("/lista-compras", response_model=list[ItemListaCompras], dependencies=[SUPERVISION])
def lista_compras(servicios: Servicios = Depends(get_servicios)):
    """Vista derivada (decisión de cátedra 2): bajo umbral + requerimientos manuales pendientes."""
    return servicios.lista_compras()


@router.post("/requerimientos", response_model=RequerimientoLeer, status_code=201, tags=["lista de compras"])
def crear_requerimiento(
    datos: RequerimientoCrear, usuario: Usuario = ENCARGADO, servicios: Servicios = Depends(get_servicios)
):
    """Requerimiento específico o previsión de necesidades que el encargado suma a la lista de compras."""
    return servicios.crear_requerimiento(datos, usuario)
