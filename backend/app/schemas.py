"""Contratos de entrada/salida de la API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import (
    EstadoIncidencia,
    EstadoMaquina,
    EstadoPedido,
    EstadoReparacion,
    EstadoReserva,
    Prioridad,
    Rol,
    TipoMovimiento,
    TipoReparacion,
    Turno,
    Urgencia,
)

# Ubicación: código alfanumérico con guiones, ej. A-03-12 (decisión de cátedra 5).
PATRON_UBICACION = r"^[A-Za-z0-9]+(-[A-Za-z0-9]+)*$"


class Leer(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UsuarioLeer(Leer):
    id: int
    usuario: str
    nombre: str
    email: str
    rol: Rol


class Referencia(Leer):
    id: int
    codigo: str
    nombre: str


# --- Repuestos -----------------------------------------------------------------


class RepuestoCrear(BaseModel):
    codigo: str = Field(min_length=1, max_length=64)
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str = ""
    umbral_minimo: int = Field(ge=0)
    ubicacion_codigo: str | None = Field(default=None, pattern=PATRON_UBICACION)
    ubicacion_descripcion: str | None = None
    maquina_ids: list[int] = []


class RepuestoLeer(Leer):
    id: int
    codigo: str
    nombre: str
    descripcion: str
    stock_fisico: int
    stock_reservado: int
    stock_disponible: int
    umbral_minimo: int
    bajo_umbral: bool
    ubicacion_codigo: str | None
    ubicacion_descripcion: str | None
    maquinas: list[Referencia]


class IngresoCrear(BaseModel):
    cantidad: int = Field(ge=1)
    ubicacion_codigo: str = Field(pattern=PATRON_UBICACION)
    ubicacion_descripcion: str | None = None


class MovimientoLeer(Leer):
    id: int
    repuesto_id: int
    tipo: TipoMovimiento
    cantidad: int
    fecha: datetime
    usuario_id: int
    referencia: str


# --- Máquinas ------------------------------------------------------------------


class MaquinaCrear(BaseModel):
    codigo: str = Field(min_length=1, max_length=64)
    nombre: str = Field(min_length=1, max_length=200)
    tipo: str = Field(min_length=1, max_length=100)
    repuesto_ids: list[int] = []


class MaquinaLeer(Leer):
    id: int
    codigo: str
    nombre: str
    tipo: str
    estado: EstadoMaquina
    repuestos: list[Referencia]


# --- Incidencias ---------------------------------------------------------------


class IncidenciaCrear(BaseModel):
    maquina_codigo: str = Field(min_length=1, description="Código QR/barras escaneado de la máquina")
    titulo: str = Field(min_length=1, max_length=120)
    descripcion: str = Field(min_length=1)
    prioridad: Prioridad = Prioridad.media


class FotoLeer(Leer):
    id: int
    tipo_contenido: str
    subida_en: datetime


class IncidenciaLeer(Leer):
    id: int
    maquina_id: int
    titulo: str
    descripcion: str
    prioridad: Prioridad
    estado: EstadoIncidencia
    turno: Turno
    reportada_en: datetime
    reportada_por_id: int


# --- Reparaciones y uso de repuestos -------------------------------------------


class ReparacionCrear(BaseModel):
    tipo: TipoReparacion
    descripcion: str = Field(min_length=1)
    incidencia_id: int | None = None
    programada_para: datetime | None = None


class ReparacionLeer(Leer):
    id: int
    tipo: TipoReparacion
    descripcion: str
    incidencia_id: int | None
    estado: EstadoReparacion
    programada_para: datetime | None
    creada_en: datetime
    finalizada_en: datetime | None
    informe_resolucion: str | None


class UsoCrear(BaseModel):
    repuesto_codigo: str = Field(min_length=1, description="Código QR/barras escaneado del repuesto")
    cantidad: int = Field(ge=1)


class LineaUsoLeer(Leer):
    id: int
    reparacion_id: int
    repuesto_id: int
    cantidad: int
    registrada_en: datetime
    usuario_id: int


class FinalizarReparacion(BaseModel):
    informe: str = Field(min_length=1, description="Informe de resolución")


# --- Reservas ------------------------------------------------------------------


class ReservaCrear(BaseModel):
    reparacion_id: int
    repuesto_id: int
    cantidad: int = Field(ge=1)


class ReservaLeer(Leer):
    id: int
    reparacion_id: int
    repuesto_id: int
    cantidad: int
    estado: EstadoReserva
    creada_en: datetime
    creada_por_id: int
    liberada_por_id: int | None
    motivo_liberacion: str | None


class LiberarReserva(BaseModel):
    motivo: str = Field(min_length=1)


# --- Pedidos de compra ---------------------------------------------------------


class LineaPedidoCrear(BaseModel):
    repuesto_id: int
    cantidad: int = Field(ge=1)


class PedidoCrear(BaseModel):
    urgencia: Urgencia = Urgencia.normal
    observaciones: str = ""
    lineas: list[LineaPedidoCrear] = Field(min_length=1)


class LineaPedidoLeer(Leer):
    id: int
    repuesto_id: int
    cantidad: int


class PedidoLeer(Leer):
    id: int
    urgencia: Urgencia
    estado: EstadoPedido
    observaciones: str
    creado_en: datetime
    creado_por_id: int
    recibido_en: datetime | None
    lineas: list[LineaPedidoLeer]


class LineaRecepcion(BaseModel):
    repuesto_id: int
    cantidad: int = Field(ge=1)
    ubicacion_codigo: str = Field(pattern=PATRON_UBICACION)
    ubicacion_descripcion: str | None = None


class RecepcionCrear(BaseModel):
    lineas: list[LineaRecepcion] = Field(min_length=1)
