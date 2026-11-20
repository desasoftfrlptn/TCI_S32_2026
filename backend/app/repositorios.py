"""Acceso a datos. Los servicios no arman consultas: piden a los repositorios."""

from typing import TypeVar

from sqlmodel import Session, SQLModel, col, or_, select

from app.models import (
    EstadoReserva,
    FotoIncidencia,
    LineaPedido,
    LineaUso,
    Maquina,
    MaquinaRepuesto,
    MovimientoStock,
    PedidoCompra,
    Repuesto,
    Reserva,
    Rol,
    Usuario,
)

T = TypeVar("T", bound=SQLModel)


class Repositorio:
    def __init__(self, session: Session):
        self.s = session

    def obtener(self, modelo: type[T], id: int, bloquear: bool = False) -> T | None:
        consulta = select(modelo).where(modelo.id == id)  # type: ignore[attr-defined]
        if bloquear:
            consulta = consulta.with_for_update()
        return self.s.exec(consulta).first()

    def listar(self, modelo: type[T]) -> list[T]:
        return list(self.s.exec(select(modelo).order_by(col(modelo.id).desc())))  # type: ignore[attr-defined]


class RepuestoRepo(Repositorio):
    def por_codigo(self, codigo: str, bloquear: bool = False) -> Repuesto | None:
        consulta = select(Repuesto).where(Repuesto.codigo == codigo)
        if bloquear:
            consulta = consulta.with_for_update()
        return self.s.exec(consulta).first()

    def buscar(self, texto: str | None = None) -> list[Repuesto]:
        """Busca por nombre, descripción, código o nombre de máquina."""
        consulta = select(Repuesto)
        if texto:
            patron = f"%{texto}%"
            consulta = (
                consulta.outerjoin(MaquinaRepuesto, col(MaquinaRepuesto.repuesto_id) == Repuesto.id)
                .outerjoin(Maquina, col(Maquina.id) == MaquinaRepuesto.maquina_id)
                .where(
                    or_(
                        col(Repuesto.nombre).ilike(patron),
                        col(Repuesto.descripcion).ilike(patron),
                        col(Repuesto.codigo).ilike(patron),
                        col(Maquina.nombre).ilike(patron),
                    )
                )
                .distinct()
            )
        return list(self.s.exec(consulta.order_by(Repuesto.nombre)))

    def bajo_umbral(self) -> list[Repuesto]:
        consulta = select(Repuesto).where(
            Repuesto.stock_fisico - Repuesto.stock_reservado <= Repuesto.umbral_minimo
        )
        return list(self.s.exec(consulta.order_by(Repuesto.nombre)))

    def movimientos(self, repuesto_id: int) -> list[MovimientoStock]:
        consulta = (
            select(MovimientoStock)
            .where(MovimientoStock.repuesto_id == repuesto_id)
            .order_by(col(MovimientoStock.fecha), col(MovimientoStock.id))
        )
        return list(self.s.exec(consulta))

    def movimientos_recientes(self, limite: int) -> list[MovimientoStock]:
        consulta = select(MovimientoStock).order_by(col(MovimientoStock.fecha).desc(), col(MovimientoStock.id).desc())
        return list(self.s.exec(consulta.limit(limite)))


class MaquinaRepo(Repositorio):
    def por_codigo(self, codigo: str) -> Maquina | None:
        return self.s.exec(select(Maquina).where(Maquina.codigo == codigo)).first()


class IncidenciaRepo(Repositorio):
    def fotos(self, incidencia_id: int) -> list[FotoIncidencia]:
        consulta = select(FotoIncidencia).where(FotoIncidencia.incidencia_id == incidencia_id)
        return list(self.s.exec(consulta.order_by(col(FotoIncidencia.id))))


class ReparacionRepo(Repositorio):
    def lineas_uso(self, reparacion_id: int) -> list[LineaUso]:
        consulta = select(LineaUso).where(LineaUso.reparacion_id == reparacion_id)
        return list(self.s.exec(consulta.order_by(col(LineaUso.id))))

    def reservas_activas(self, reparacion_id: int) -> list[Reserva]:
        consulta = (
            select(Reserva)
            .where(Reserva.reparacion_id == reparacion_id, Reserva.estado == EstadoReserva.activa)
            .order_by(col(Reserva.id))
            .with_for_update()
        )
        return list(self.s.exec(consulta))


class PedidoRepo(Repositorio):
    def lineas(self, pedido_id: int) -> list[LineaPedido]:
        consulta = select(LineaPedido).where(LineaPedido.pedido_id == pedido_id)
        return list(self.s.exec(consulta.order_by(col(LineaPedido.id))))

    def obtener_pedido(self, pedido_id: int, bloquear: bool = False) -> PedidoCompra | None:
        return self.obtener(PedidoCompra, pedido_id, bloquear)


class UsuarioRepo(Repositorio):
    def por_usuario(self, usuario: str) -> Usuario | None:
        return self.s.exec(select(Usuario).where(Usuario.usuario == usuario)).first()

    def emails_por_rol(self, *roles: Rol) -> list[str]:
        consulta = select(Usuario.email).where(col(Usuario.rol).in_(roles)).order_by(Usuario.email)
        return list(self.s.exec(consulta))

