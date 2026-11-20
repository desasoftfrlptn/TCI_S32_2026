from fastapi import APIRouter, Depends, HTTPException

from app.deps import CUALQUIERA, ENCARGADO, STOCK, get_servicios
from app.models import PedidoCompra, Usuario
from app.schemas import DelegarRecepcion, LineaPedidoLeer, PedidoCrear, PedidoLeer, RecepcionCrear
from app.servicios import Servicios

router = APIRouter(tags=["pedidos de compra"])


def _leer(servicios: Servicios, pedido: PedidoCompra) -> PedidoLeer:
    lineas = [LineaPedidoLeer.model_validate(l) for l in servicios.pedidos.lineas(pedido.id)]
    return PedidoLeer.model_validate({**pedido.model_dump(), "lineas": lineas})


@router.get("/pedidos", response_model=list[PedidoLeer], dependencies=[CUALQUIERA])
def listar_pedidos(servicios: Servicios = Depends(get_servicios)):
    return [_leer(servicios, p) for p in servicios.pedidos.listar(PedidoCompra)]


@router.get("/pedidos/{pedido_id}", response_model=PedidoLeer, dependencies=[CUALQUIERA])
def obtener_pedido(pedido_id: int, servicios: Servicios = Depends(get_servicios)):
    pedido = servicios.pedidos.obtener_pedido(pedido_id)
    if not pedido:
        raise HTTPException(404, "Pedido no encontrado")
    return _leer(servicios, pedido)


@router.post("/pedidos", response_model=PedidoLeer, status_code=201)
def crear_pedido(datos: PedidoCrear, usuario: Usuario = STOCK, servicios: Servicios = Depends(get_servicios)):
    """RN-03 / RN-04: pedido con urgencia, notificado a encargados y gerencia."""
    return _leer(servicios, servicios.crear_pedido(datos, usuario))


@router.post("/pedidos/{pedido_id}/recepcion", response_model=PedidoLeer)
def recibir_pedido(
    pedido_id: int, datos: RecepcionCrear, usuario: Usuario = STOCK, servicios: Servicios = Depends(get_servicios)
):
    """RN-08: carga el stock recibido con su ubicación (encargado o usuario delegado)."""
    return _leer(servicios, servicios.recibir_pedido(pedido_id, datos, usuario))


@router.post("/pedidos/{pedido_id}/delegar", response_model=PedidoLeer)
def delegar_recepcion(
    pedido_id: int, datos: DelegarRecepcion, usuario: Usuario = ENCARGADO, servicios: Servicios = Depends(get_servicios)
):
    """RN-08: el encargado delega la carga de la compra."""
    return _leer(servicios, servicios.delegar_recepcion(pedido_id, datos, usuario))


@router.post("/pedidos/{pedido_id}/verificar", response_model=PedidoLeer)
def verificar_recepcion(pedido_id: int, usuario: Usuario = ENCARGADO, servicios: Servicios = Depends(get_servicios)):
    """RN-08: el encargado supervisa la carga y la da por verificada."""
    return _leer(servicios, servicios.verificar_recepcion(pedido_id, usuario))
