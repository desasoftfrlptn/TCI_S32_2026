"""Entidades persistidas (sección 5 del dominio).

Los estados de Incidencia, Reparación, Reserva y Pedido son la versión mínima
que necesita el backend; deben coincidir con las máquinas de estado de M1.
"""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime
from sqlmodel import Field, Relationship, SQLModel


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def _momento():
    return Field(default_factory=ahora, sa_type=DateTime(timezone=True))


def _momento_opcional():
    return Field(default=None, sa_type=DateTime(timezone=True))


class Rol(str, Enum):
    operario = "operario"
    mantenimiento = "mantenimiento"
    encargado = "encargado"
    gerencia = "gerencia"


class Turno(str, Enum):
    manana = "mañana"
    tarde = "tarde"
    noche = "noche"


class EstadoMaquina(str, Enum):
    operativa = "operativa"
    fuera_de_servicio = "fuera_de_servicio"


class Prioridad(str, Enum):
    baja = "baja"
    media = "media"
    alta = "alta"


class EstadoIncidencia(str, Enum):
    abierta = "abierta"
    en_reparacion = "en_reparacion"
    resuelta = "resuelta"


class TipoReparacion(str, Enum):
    correctiva = "correctiva"
    preventiva = "preventiva"


class EstadoReparacion(str, Enum):
    abierta = "abierta"
    finalizada = "finalizada"


class EstadoReserva(str, Enum):
    activa = "activa"
    consumida = "consumida"
    liberada = "liberada"


class Urgencia(str, Enum):
    normal = "normal"
    urgente = "urgente"


class EstadoPedido(str, Enum):
    pendiente = "pendiente"
    recibido = "recibido"
    verificado = "verificado"


class OrigenRequerimiento(str, Enum):
    especifico = "especifico"
    prevision = "prevision"


class EstadoRequerimiento(str, Enum):
    pendiente = "pendiente"
    atendido = "atendido"


class TipoMovimiento(str, Enum):
    entrada = "entrada"
    salida = "salida"
    reserva = "reserva"
    liberacion = "liberacion"
    consumo = "consumo"


class Usuario(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    usuario: str = Field(unique=True, index=True)
    nombre: str
    email: str
    rol: Rol
    password_hash: str


class MaquinaRepuesto(SQLModel, table=True):
    """Lista de repuestos a mantener en stock para cada máquina (RN-07)."""

    maquina_id: int = Field(foreign_key="maquina.id", primary_key=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", primary_key=True)


class Maquina(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    codigo: str = Field(unique=True, index=True)
    nombre: str
    tipo: str
    estado: EstadoMaquina = EstadoMaquina.operativa

    repuestos: list["Repuesto"] = Relationship(back_populates="maquinas", link_model=MaquinaRepuesto)


class Repuesto(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint("stock_fisico >= 0", name="ck_repuesto_fisico_no_negativo"),
        CheckConstraint(
            "stock_reservado >= 0 AND stock_reservado <= stock_fisico",
            name="ck_repuesto_reservado_valido",
        ),
        CheckConstraint("umbral_minimo >= 0", name="ck_repuesto_umbral_no_negativo"),
    )

    id: int | None = Field(default=None, primary_key=True)
    codigo: str = Field(unique=True, index=True)
    nombre: str
    descripcion: str = ""
    stock_fisico: int = 0
    stock_reservado: int = 0
    umbral_minimo: int = 0
    ubicacion_codigo: str | None = None
    ubicacion_descripcion: str | None = None

    maquinas: list[Maquina] = Relationship(back_populates="repuestos", link_model=MaquinaRepuesto)

    @property
    def stock_disponible(self) -> int:
        return self.stock_fisico - self.stock_reservado

    @property
    def bajo_umbral(self) -> bool:
        return self.stock_disponible <= self.umbral_minimo


class Incidencia(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    maquina_id: int = Field(foreign_key="maquina.id", index=True)
    titulo: str
    descripcion: str
    prioridad: Prioridad = Prioridad.media
    estado: EstadoIncidencia = EstadoIncidencia.abierta
    turno: Turno
    reportada_en: datetime = _momento()
    reportada_por_id: int = Field(foreign_key="usuario.id")


class FotoIncidencia(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    incidencia_id: int = Field(foreign_key="incidencia.id", index=True)
    archivo: str
    tipo_contenido: str
    subida_en: datetime = _momento()


class Reparacion(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    tipo: TipoReparacion
    descripcion: str
    incidencia_id: int | None = Field(default=None, foreign_key="incidencia.id", index=True)
    estado: EstadoReparacion = EstadoReparacion.abierta
    programada_para: datetime | None = _momento_opcional()
    creada_en: datetime = _momento()
    finalizada_en: datetime | None = _momento_opcional()
    informe_resolucion: str | None = None


class LineaUso(SQLModel, table=True):
    __table_args__ = (CheckConstraint("cantidad >= 1", name="ck_linea_uso_cantidad"),)

    id: int | None = Field(default=None, primary_key=True)
    reparacion_id: int = Field(foreign_key="reparacion.id", index=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    cantidad: int
    registrada_en: datetime = _momento()
    usuario_id: int = Field(foreign_key="usuario.id")


class Reserva(SQLModel, table=True):
    __table_args__ = (CheckConstraint("cantidad >= 1", name="ck_reserva_cantidad"),)

    id: int | None = Field(default=None, primary_key=True)
    reparacion_id: int = Field(foreign_key="reparacion.id", index=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    cantidad: int
    estado: EstadoReserva = EstadoReserva.activa
    creada_en: datetime = _momento()
    creada_por_id: int = Field(foreign_key="usuario.id")
    liberada_por_id: int | None = Field(default=None, foreign_key="usuario.id")
    motivo_liberacion: str | None = None


class PedidoCompra(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    urgencia: Urgencia = Urgencia.normal
    estado: EstadoPedido = EstadoPedido.pendiente
    observaciones: str = ""
    creado_en: datetime = _momento()
    creado_por_id: int = Field(foreign_key="usuario.id")
    # RN-08: el encargado puede delegar la recepción y luego supervisarla.
    delegado_a_id: int | None = Field(default=None, foreign_key="usuario.id")
    recibido_por_id: int | None = Field(default=None, foreign_key="usuario.id")
    recibido_en: datetime | None = _momento_opcional()
    verificado_por_id: int | None = Field(default=None, foreign_key="usuario.id")
    verificado_en: datetime | None = _momento_opcional()


class LineaPedido(SQLModel, table=True):
    __table_args__ = (CheckConstraint("cantidad >= 1", name="ck_linea_pedido_cantidad"),)

    id: int | None = Field(default=None, primary_key=True)
    pedido_id: int = Field(foreign_key="pedidocompra.id", index=True)
    repuesto_id: int = Field(foreign_key="repuesto.id")
    cantidad: int


class RequerimientoCompra(SQLModel, table=True):
    """Requerimiento manual que el encargado suma a la lista de compras."""

    __table_args__ = (CheckConstraint("cantidad >= 1", name="ck_requerimiento_cantidad"),)

    id: int | None = Field(default=None, primary_key=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    cantidad: int
    origen: OrigenRequerimiento
    motivo: str
    estado: EstadoRequerimiento = EstadoRequerimiento.pendiente
    creado_por_id: int = Field(foreign_key="usuario.id")
    creado_en: datetime = _momento()
    pedido_id: int | None = Field(default=None, foreign_key="pedidocompra.id")


class MovimientoStock(SQLModel, table=True):
    """Registro inmutable de cada cambio de stock (base de la trazabilidad, RN-06)."""

    __table_args__ = (CheckConstraint("cantidad >= 1", name="ck_movimiento_cantidad"),)

    id: int | None = Field(default=None, primary_key=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    tipo: TipoMovimiento
    cantidad: int
    fecha: datetime = _momento()
    usuario_id: int = Field(foreign_key="usuario.id")
    referencia: str
