from fastapi import APIRouter, Depends

from app.deps import CUALQUIERA, ENCARGADO, STOCK, get_servicios
from app.models import Reparacion, Reserva, Usuario
from app.schemas import (
    FinalizarReparacion,
    LiberarReserva,
    LineaUsoLeer,
    ReparacionCrear,
    ReparacionLeer,
    ReservaCrear,
    ReservaLeer,
    UsoCrear,
)
from app.servicios import Servicios

router = APIRouter()


@router.get("/reparaciones", response_model=list[ReparacionLeer], dependencies=[CUALQUIERA], tags=["reparaciones"])
def listar_reparaciones(servicios: Servicios = Depends(get_servicios)):
    return servicios.reparaciones.listar(Reparacion)


@router.post("/reparaciones", response_model=ReparacionLeer, status_code=201, dependencies=[STOCK], tags=["reparaciones"])
def crear_reparacion(datos: ReparacionCrear, servicios: Servicios = Depends(get_servicios)):
    return servicios.crear_reparacion(datos)


@router.get("/reparaciones/{reparacion_id}/usos", response_model=list[LineaUsoLeer], dependencies=[CUALQUIERA],
            tags=["reparaciones"])
def listar_usos(reparacion_id: int, servicios: Servicios = Depends(get_servicios)):
    return servicios.reparaciones.lineas_uso(reparacion_id)


@router.post("/reparaciones/{reparacion_id}/usos", response_model=LineaUsoLeer, status_code=201, tags=["reparaciones"])
def registrar_uso(
    reparacion_id: int, datos: UsoCrear, usuario: Usuario = STOCK, servicios: Servicios = Depends(get_servicios)
):
    """RN-01: escaneo del repuesto + cantidad usada → descuenta stock físico."""
    return servicios.registrar_uso(reparacion_id, datos, usuario)


@router.post("/reparaciones/{reparacion_id}/finalizar", response_model=ReparacionLeer, tags=["reparaciones"])
def finalizar_reparacion(
    reparacion_id: int, datos: FinalizarReparacion, usuario: Usuario = STOCK,
    servicios: Servicios = Depends(get_servicios),
):
    """Cierra la reparación con su informe. En preventivas consume las reservas (RN-10)."""
    return servicios.finalizar_reparacion(reparacion_id, datos.informe, usuario)


@router.get("/reservas", response_model=list[ReservaLeer], dependencies=[CUALQUIERA], tags=["reservas"])
def listar_reservas(servicios: Servicios = Depends(get_servicios)):
    return servicios.reparaciones.listar(Reserva)


@router.post("/reservas", response_model=ReservaLeer, status_code=201, tags=["reservas"])
def crear_reserva(datos: ReservaCrear, usuario: Usuario = STOCK, servicios: Servicios = Depends(get_servicios)):
    return servicios.crear_reserva(datos, usuario)


@router.post("/reservas/{reserva_id}/liberar", response_model=ReservaLeer, tags=["reservas"])
def liberar_reserva(
    reserva_id: int, datos: LiberarReserva, usuario: Usuario = ENCARGADO,
    servicios: Servicios = Depends(get_servicios),
):
    """RN-05: requiere rol Encargado y notifica el cambio de inmediato."""
    return servicios.liberar_reserva(reserva_id, datos, usuario)
