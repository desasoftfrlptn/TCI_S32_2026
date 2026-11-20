"""Capa de servicio: acá viven las reglas de negocio (RN-01 a RN-10).

Toda operación que cambia stock bloquea la fila del repuesto con
SELECT ... FOR UPDATE, de modo que dos empleados que descuentan la última
unidad a la vez se serializan; los CHECK de la tabla son la última barrera.
Las notificaciones se envían después del commit.
"""

import uuid
from pathlib import Path

from sqlmodel import Session

from app.config import UPLOAD_DIR
from app.models import (
    EstadoIncidencia,
    EstadoPedido,
    EstadoReparacion,
    EstadoRequerimiento,
    EstadoReserva,
    FotoIncidencia,
    Incidencia,
    LineaPedido,
    LineaUso,
    Maquina,
    MovimientoStock,
    PedidoCompra,
    Reparacion,
    Repuesto,
    RequerimientoCompra,
    Reserva,
    Rol,
    TipoMovimiento,
    TipoReparacion,
    Usuario,
    ahora,
)
from app.notificaciones import Notificador
from app.reconocimiento import FotoInvalida, Reconocedor
from app.repositorios import (
    IncidenciaRepo,
    MaquinaRepo,
    PedidoRepo,
    ReparacionRepo,
    RepuestoRepo,
    UsuarioRepo,
)
from app.schemas import (
    DelegarRecepcion,
    IncidenciaCrear,
    IngresoCrear,
    ItemListaCompras,
    LiberarReserva,
    MaquinaCrear,
    PedidoCrear,
    RecepcionCrear,
    ReparacionCrear,
    RepuestoCrear,
    RepuestoLeer,
    RequerimientoCrear,
    ReservaCrear,
    UsoCrear,
)
from app.seguridad import crear_token, verificar_password
from app.turnos import turno_de

TIPOS_FOTO = {"image/jpeg": ".jpg", "image/png": ".png"}


class ErrorDominio(Exception):
    status_code = 409


class NoEncontrado(ErrorDominio):
    status_code = 404


class SinPermiso(ErrorDominio):
    status_code = 403


class StockInsuficiente(ErrorDominio):
    status_code = 409


class OperacionInvalida(ErrorDominio):
    status_code = 409


class CredencialesInvalidas(ErrorDominio):
    status_code = 401


class Servicios:
    def __init__(self, session: Session, notificador: Notificador, reconocedor: Reconocedor):
        self.s = session
        self.notificador = notificador
        self.reconocedor = reconocedor
        self.repuestos = RepuestoRepo(session)
        self.maquinas = MaquinaRepo(session)
        self.incidencias = IncidenciaRepo(session)
        self.reparaciones = ReparacionRepo(session)
        self.pedidos = PedidoRepo(session)
        self.usuarios = UsuarioRepo(session)

    # --- auxiliares ------------------------------------------------------------

    def _notificar(self, roles: tuple[Rol, ...], asunto: str, cuerpo: str) -> None:
        destinatarios = self.usuarios.emails_por_rol(*roles)
        if destinatarios:
            self.notificador.enviar(destinatarios, asunto, cuerpo)

    def _alertar_si_bajo_umbral(self, repuesto: Repuesto) -> None:
        """RN-02: alerta cuando stock disponible <= umbral mínimo."""
        if repuesto.bajo_umbral:
            self._notificar(
                (Rol.encargado,),
                f"Alerta de umbral: {repuesto.codigo} {repuesto.nombre}",
                f"Stock disponible {repuesto.stock_disponible} (umbral mínimo {repuesto.umbral_minimo}). "
                "El repuesto ya figura en la lista de compras.",
            )

    def _movimiento(
        self, repuesto: Repuesto, tipo: TipoMovimiento, cantidad: int, usuario: Usuario, referencia: str
    ) -> None:
        self.s.add(
            MovimientoStock(
                repuesto_id=repuesto.id,
                tipo=tipo,
                cantidad=cantidad,
                usuario_id=usuario.id,
                referencia=referencia,
            )
        )

    def _repuesto(self, repuesto_id: int, bloquear: bool = False) -> Repuesto:
        repuesto = self.repuestos.obtener(Repuesto, repuesto_id, bloquear)
        if not repuesto:
            raise NoEncontrado(f"No existe el repuesto {repuesto_id}")
        return repuesto

    def _reparacion_abierta(self, reparacion_id: int) -> Reparacion:
        reparacion = self.reparaciones.obtener(Reparacion, reparacion_id, bloquear=True)
        if not reparacion:
            raise NoEncontrado(f"No existe la reparación {reparacion_id}")
        if reparacion.estado != EstadoReparacion.abierta:
            raise OperacionInvalida(f"La reparación {reparacion_id} ya está finalizada")
        return reparacion

    def _ingresar(self, repuesto: Repuesto, cantidad: int, ubicacion: str, detalle: str | None,
                  usuario: Usuario, referencia: str) -> None:
        repuesto.stock_fisico += cantidad
        repuesto.ubicacion_codigo = ubicacion.upper()
        if detalle is not None:
            repuesto.ubicacion_descripcion = detalle
        self._movimiento(repuesto, TipoMovimiento.entrada, cantidad, usuario, referencia)

    # --- autenticación ----------------------------------------------------------

    def autenticar(self, usuario: str, password: str) -> tuple[Usuario, str]:
        encontrado = self.usuarios.por_usuario(usuario)
        if not encontrado or not verificar_password(password, encontrado.password_hash):
            raise CredencialesInvalidas("Usuario o contraseña incorrectos")
        return encontrado, crear_token(encontrado.usuario)

    # --- repuestos y máquinas --------------------------------------------------

    def reconocer_repuesto(self, foto: bytes) -> Repuesto:
        """Identifica el repuesto leyendo los códigos que aparecen en la foto."""
        try:
            codigos = self.reconocedor.codigos(foto)
        except FotoInvalida as error:
            raise OperacionInvalida(str(error)) from error
        if not codigos:
            raise NoEncontrado("No se reconoció ningún código en la foto. Probá acercando la cámara a la etiqueta.")
        for codigo in codigos:
            repuesto = self.repuestos.por_codigo(codigo)
            if repuesto:
                return repuesto
        raise NoEncontrado(f"Se leyó {', '.join(codigos)}, pero no corresponde a ningún repuesto registrado")

    def crear_repuesto(self, datos: RepuestoCrear) -> Repuesto:
        if self.repuestos.por_codigo(datos.codigo):
            raise OperacionInvalida(f"Ya existe un repuesto con código {datos.codigo}")
        repuesto = Repuesto(
            **datos.model_dump(exclude={"maquina_ids", "ubicacion_codigo"}),
            ubicacion_codigo=datos.ubicacion_codigo.upper() if datos.ubicacion_codigo else None,
        )
        repuesto.maquinas = [self._maquina(i) for i in datos.maquina_ids]
        self.s.add(repuesto)
        self.s.commit()
        self.s.refresh(repuesto)
        return repuesto

    def _maquina(self, maquina_id: int) -> Maquina:
        maquina = self.maquinas.obtener(Maquina, maquina_id)
        if not maquina:
            raise NoEncontrado(f"No existe la máquina {maquina_id}")
        return maquina

    def crear_maquina(self, datos: MaquinaCrear) -> Maquina:
        """RN-07: se registra la máquina con la lista de repuestos a mantener en stock."""
        if self.maquinas.por_codigo(datos.codigo):
            raise OperacionInvalida(f"Ya existe una máquina con código {datos.codigo}")
        maquina = Maquina(codigo=datos.codigo, nombre=datos.nombre, tipo=datos.tipo)
        maquina.repuestos = [self._repuesto(i) for i in datos.repuesto_ids]
        self.s.add(maquina)
        self.s.commit()
        self.s.refresh(maquina)
        return maquina

    def ingresar_stock(self, repuesto_id: int, datos: IngresoCrear, usuario: Usuario) -> Repuesto:
        """RN-08: carga de stock físico con su ubicación."""
        repuesto = self._repuesto(repuesto_id, bloquear=True)
        self._ingresar(repuesto, datos.cantidad, datos.ubicacion_codigo, datos.ubicacion_descripcion,
                       usuario, "ingreso manual")
        self.s.commit()
        self.s.refresh(repuesto)
        return repuesto

    # --- incidencias ------------------------------------------------------------

    def crear_incidencia(self, datos: IncidenciaCrear, usuario: Usuario) -> Incidencia:
        maquina = self.maquinas.por_codigo(datos.maquina_codigo)
        if not maquina:
            raise NoEncontrado(f"No hay ninguna máquina con código {datos.maquina_codigo}")
        momento = ahora()
        incidencia = Incidencia(
            maquina_id=maquina.id,
            titulo=datos.titulo,
            descripcion=datos.descripcion,
            prioridad=datos.prioridad,
            turno=turno_de(momento),
            reportada_en=momento,
            reportada_por_id=usuario.id,
        )
        self.s.add(incidencia)
        self.s.commit()
        self.s.refresh(incidencia)
        self._notificar(
            (Rol.mantenimiento, Rol.encargado),
            f"Incidencia #{incidencia.id} en {maquina.nombre} ({incidencia.prioridad.value})",
            f"{incidencia.titulo}\n\n{incidencia.descripcion}\n\nReportó: {usuario.nombre} "
            f"· turno {incidencia.turno.value}",
        )
        return incidencia

    def agregar_foto(self, incidencia_id: int, contenido: bytes, tipo_contenido: str) -> FotoIncidencia:
        if not self.incidencias.obtener(Incidencia, incidencia_id):
            raise NoEncontrado(f"No existe la incidencia {incidencia_id}")
        extension = TIPOS_FOTO.get(tipo_contenido)
        if not extension:
            raise OperacionInvalida("La foto debe ser JPG o PNG")
        carpeta = Path(UPLOAD_DIR)
        carpeta.mkdir(parents=True, exist_ok=True)
        archivo = f"{uuid.uuid4().hex}{extension}"
        (carpeta / archivo).write_bytes(contenido)
        foto = FotoIncidencia(incidencia_id=incidencia_id, archivo=archivo, tipo_contenido=tipo_contenido)
        self.s.add(foto)
        self.s.commit()
        self.s.refresh(foto)
        return foto

    # --- reparaciones y uso -----------------------------------------------------

    def crear_reparacion(self, datos: ReparacionCrear) -> Reparacion:
        if datos.tipo == TipoReparacion.correctiva:
            if datos.incidencia_id is None:
                raise OperacionInvalida("Una reparación correctiva debe referir a una incidencia")
            incidencia = self.incidencias.obtener(Incidencia, datos.incidencia_id)
            if not incidencia:
                raise NoEncontrado(f"No existe la incidencia {datos.incidencia_id}")
            if incidencia.estado == EstadoIncidencia.resuelta:
                raise OperacionInvalida(f"La incidencia {incidencia.id} ya está resuelta")
            incidencia.estado = EstadoIncidencia.en_reparacion
        reparacion = Reparacion(**datos.model_dump())
        self.s.add(reparacion)
        self.s.commit()
        self.s.refresh(reparacion)
        return reparacion

    def registrar_uso(self, reparacion_id: int, datos: UsoCrear, usuario: Usuario) -> LineaUso:
        """RN-01: descuenta del stock físico; RN-05: no puede tomar unidades reservadas."""
        reparacion = self._reparacion_abierta(reparacion_id)
        repuesto = self.repuestos.por_codigo(datos.repuesto_codigo, bloquear=True)
        if not repuesto:
            raise NoEncontrado(f"No hay ningún repuesto con código {datos.repuesto_codigo}")
        if datos.cantidad > repuesto.stock_disponible:
            raise StockInsuficiente(
                f"Stock disponible insuficiente de {repuesto.codigo}: hay {repuesto.stock_disponible}, "
                f"se pidieron {datos.cantidad}. Podés generar un pedido de compra."
            )
        repuesto.stock_fisico -= datos.cantidad
        linea = LineaUso(
            reparacion_id=reparacion.id,
            repuesto_id=repuesto.id,
            cantidad=datos.cantidad,
            usuario_id=usuario.id,
        )
        self.s.add(linea)
        self._movimiento(repuesto, TipoMovimiento.salida, datos.cantidad, usuario,
                         f"reparacion:{reparacion.id}")
        self.s.commit()
        self.s.refresh(linea)
        self.s.refresh(repuesto)
        self._notificar(
            (Rol.encargado,),
            f"Cambio de parte en reparación #{reparacion.id}",
            f"{usuario.nombre} usó {datos.cantidad} × {repuesto.codigo} {repuesto.nombre}.",
        )
        self._alertar_si_bajo_umbral(repuesto)
        return linea

    def finalizar_reparacion(self, reparacion_id: int, informe: str, usuario: Usuario) -> Reparacion:
        """Cierra la reparación. Si es preventiva, consume sus reservas (RN-10)."""
        reparacion = self._reparacion_abierta(reparacion_id)
        for reserva in self.reparaciones.reservas_activas(reparacion.id):
            repuesto = self._repuesto(reserva.repuesto_id, bloquear=True)
            repuesto.stock_fisico -= reserva.cantidad
            repuesto.stock_reservado -= reserva.cantidad
            reserva.estado = EstadoReserva.consumida
            self.s.add(LineaUso(reparacion_id=reparacion.id, repuesto_id=repuesto.id,
                                cantidad=reserva.cantidad, usuario_id=usuario.id))
            self._movimiento(repuesto, TipoMovimiento.consumo, reserva.cantidad, usuario,
                             f"reserva:{reserva.id}")
        reparacion.estado = EstadoReparacion.finalizada
        reparacion.finalizada_en = ahora()
        reparacion.informe_resolucion = informe
        if reparacion.incidencia_id is not None:
            incidencia = self.incidencias.obtener(Incidencia, reparacion.incidencia_id)
            if incidencia:
                incidencia.estado = EstadoIncidencia.resuelta
        self.s.commit()
        self.s.refresh(reparacion)
        self._notificar(
            (Rol.encargado, Rol.gerencia),
            f"Informe de resolución · reparación #{reparacion.id}",
            f"{usuario.nombre} finalizó la reparación.\n\n{informe}",
        )
        return reparacion

    # --- reservas ---------------------------------------------------------------

    def crear_reserva(self, datos: ReservaCrear, usuario: Usuario) -> Reserva:
        reparacion = self._reparacion_abierta(datos.reparacion_id)
        if reparacion.tipo != TipoReparacion.preventiva:
            raise OperacionInvalida("Solo se reservan repuestos para mantenimientos preventivos")
        repuesto = self._repuesto(datos.repuesto_id, bloquear=True)
        if datos.cantidad > repuesto.stock_disponible:
            raise StockInsuficiente(
                f"Stock disponible insuficiente de {repuesto.codigo} para reservar: "
                f"hay {repuesto.stock_disponible}, se pidieron {datos.cantidad}"
            )
        repuesto.stock_reservado += datos.cantidad
        reserva = Reserva(**datos.model_dump(), creada_por_id=usuario.id)
        self.s.add(reserva)
        self.s.flush()
        self._movimiento(repuesto, TipoMovimiento.reserva, datos.cantidad, usuario, f"reserva:{reserva.id}")
        self.s.commit()
        self.s.refresh(reserva)
        self.s.refresh(repuesto)
        self._alertar_si_bajo_umbral(repuesto)
        return reserva

    def liberar_reserva(self, reserva_id: int, datos: LiberarReserva, usuario: Usuario) -> Reserva:
        """RN-05: solo un Encargado libera, y se avisa de inmediato el impacto."""
        if usuario.rol != Rol.encargado:
            raise SinPermiso("Solo un usuario con rol Encargado puede liberar una reserva")
        reserva = self.reparaciones.obtener(Reserva, reserva_id, bloquear=True)
        if not reserva:
            raise NoEncontrado(f"No existe la reserva {reserva_id}")
        if reserva.estado != EstadoReserva.activa:
            raise OperacionInvalida(f"La reserva {reserva_id} no está activa")
        repuesto = self._repuesto(reserva.repuesto_id, bloquear=True)
        repuesto.stock_reservado -= reserva.cantidad
        reserva.estado = EstadoReserva.liberada
        reserva.liberada_por_id = usuario.id
        reserva.motivo_liberacion = datos.motivo
        self._movimiento(repuesto, TipoMovimiento.liberacion, reserva.cantidad, usuario,
                         f"reserva:{reserva.id}")
        self.s.commit()
        self.s.refresh(reserva)
        self._notificar(
            (Rol.encargado, Rol.mantenimiento),
            f"Reserva #{reserva.id} liberada: {repuesto.codigo} {repuesto.nombre}",
            f"{usuario.nombre} liberó {reserva.cantidad} unidades reservadas para el mantenimiento "
            f"preventivo #{reserva.reparacion_id}. Ese mantenimiento ya no cuenta con esas unidades.\n\n"
            f"Motivo: {datos.motivo}",
        )
        return reserva

    # --- pedidos de compra ------------------------------------------------------

    def crear_pedido(self, datos: PedidoCrear, usuario: Usuario) -> PedidoCompra:
        """RN-03 / RN-04: el pedido se notifica a encargados y gerencia con su urgencia."""
        repuestos = [self._repuesto(linea.repuesto_id) for linea in datos.lineas]
        requerimientos = [self._requerimiento_pendiente(i) for i in datos.requerimiento_ids]
        pedido = PedidoCompra(urgencia=datos.urgencia, observaciones=datos.observaciones,
                              creado_por_id=usuario.id)
        self.s.add(pedido)
        self.s.flush()
        for linea in datos.lineas:
            self.s.add(LineaPedido(pedido_id=pedido.id, **linea.model_dump()))
        for requerimiento in requerimientos:
            requerimiento.estado = EstadoRequerimiento.atendido
            requerimiento.pedido_id = pedido.id
        self.s.commit()
        self.s.refresh(pedido)
        detalle = "\n".join(
            f"- {linea.cantidad} × {r.codigo} {r.nombre}" for linea, r in zip(datos.lineas, repuestos)
        )
        self._notificar(
            (Rol.encargado, Rol.gerencia),
            f"[{pedido.urgencia.value.upper()}] Pedido de compra #{pedido.id}",
            f"Solicitado por {usuario.nombre}.\n\n{detalle}\n\n{pedido.observaciones}".strip(),
        )
        return pedido

    def _pedido(self, pedido_id: int) -> PedidoCompra:
        pedido = self.pedidos.obtener_pedido(pedido_id, bloquear=True)
        if not pedido:
            raise NoEncontrado(f"No existe el pedido {pedido_id}")
        return pedido

    def delegar_recepcion(self, pedido_id: int, datos: DelegarRecepcion, usuario: Usuario) -> PedidoCompra:
        """RN-08: el encargado delega la carga de la compra en un empleado de mantenimiento."""
        pedido = self._pedido(pedido_id)
        if pedido.estado != EstadoPedido.pendiente:
            raise OperacionInvalida(f"El pedido {pedido_id} ya fue recibido")
        delegado = self.usuarios.obtener(Usuario, datos.usuario_id)
        if not delegado or delegado.rol not in (Rol.mantenimiento, Rol.encargado):
            raise OperacionInvalida("Solo se puede delegar en un usuario de mantenimiento o encargado")
        pedido.delegado_a_id = delegado.id
        self.s.commit()
        self.s.refresh(pedido)
        self.notificador.enviar(
            [delegado.email],
            f"Te delegaron la recepción del pedido #{pedido.id}",
            f"{usuario.nombre} te asignó cargar el stock y la ubicación del pedido de compra #{pedido.id}.",
        )
        return pedido

    def recibir_pedido(self, pedido_id: int, datos: RecepcionCrear, usuario: Usuario) -> PedidoCompra:
        """RN-08: al recibir la compra se carga stock físico y ubicación.

        La carga la hace un encargado o, si fue delegada, el usuario delegado.
        """
        pedido = self._pedido(pedido_id)
        if pedido.estado != EstadoPedido.pendiente:
            raise OperacionInvalida(f"El pedido {pedido_id} ya fue recibido")
        if usuario.rol != Rol.encargado and usuario.id != pedido.delegado_a_id:
            raise SinPermiso("La recepción la carga un encargado o el usuario en quien se delegó")
        pedidos_ids = {linea.repuesto_id for linea in self.pedidos.lineas(pedido.id)}
        for linea in datos.lineas:
            if linea.repuesto_id not in pedidos_ids:
                raise OperacionInvalida(f"El repuesto {linea.repuesto_id} no figura en el pedido {pedido_id}")
            repuesto = self._repuesto(linea.repuesto_id, bloquear=True)
            self._ingresar(repuesto, linea.cantidad, linea.ubicacion_codigo, linea.ubicacion_descripcion,
                           usuario, f"pedido:{pedido.id}")
        pedido.estado = EstadoPedido.recibido
        pedido.recibido_en = ahora()
        pedido.recibido_por_id = usuario.id
        self.s.commit()
        self.s.refresh(pedido)
        if usuario.rol != Rol.encargado:
            self._notificar(
                (Rol.encargado,),
                f"Pedido #{pedido.id} recibido: pendiente de supervisión",
                f"{usuario.nombre} cargó el stock recibido del pedido #{pedido.id}. Revisalo y marcalo como verificado.",
            )
        return pedido

    def verificar_recepcion(self, pedido_id: int, usuario: Usuario) -> PedidoCompra:
        """RN-08: el encargado supervisa la carga (propia o delegada) y la da por verificada."""
        pedido = self._pedido(pedido_id)
        if pedido.estado != EstadoPedido.recibido:
            raise OperacionInvalida(f"El pedido {pedido_id} todavía no fue recibido o ya está verificado")
        pedido.estado = EstadoPedido.verificado
        pedido.verificado_por_id = usuario.id
        pedido.verificado_en = ahora()
        self.s.commit()
        self.s.refresh(pedido)
        return pedido

    # --- lista de compras -------------------------------------------------------

    def _requerimiento_pendiente(self, requerimiento_id: int) -> RequerimientoCompra:
        requerimiento = self.pedidos.obtener(RequerimientoCompra, requerimiento_id, bloquear=True)
        if not requerimiento:
            raise NoEncontrado(f"No existe el requerimiento {requerimiento_id}")
        if requerimiento.estado != EstadoRequerimiento.pendiente:
            raise OperacionInvalida(f"El requerimiento {requerimiento_id} ya fue atendido")
        return requerimiento

    def crear_requerimiento(self, datos: RequerimientoCrear, usuario: Usuario) -> RequerimientoCompra:
        self._repuesto(datos.repuesto_id)
        requerimiento = RequerimientoCompra(**datos.model_dump(), creado_por_id=usuario.id)
        self.s.add(requerimiento)
        self.s.commit()
        self.s.refresh(requerimiento)
        return requerimiento

    def lista_compras(self) -> list[ItemListaCompras]:
        """Vista derivada (decisión de cátedra 2): bajo umbral + requerimientos pendientes."""
        items = [
            ItemListaCompras(
                origen="umbral",
                repuesto=RepuestoLeer.model_validate(r),
                cantidad_sugerida=r.umbral_minimo - r.stock_disponible + 1,
                motivo=f"Disponible {r.stock_disponible} ≤ umbral {r.umbral_minimo}",
            )
            for r in self.repuestos.bajo_umbral()
        ]
        for requerimiento in self.pedidos.requerimientos_pendientes():
            repuesto = self._repuesto(requerimiento.repuesto_id)
            items.append(
                ItemListaCompras(
                    origen=requerimiento.origen.value,
                    repuesto=RepuestoLeer.model_validate(repuesto),
                    cantidad_sugerida=requerimiento.cantidad,
                    motivo=requerimiento.motivo,
                    requerimiento_id=requerimiento.id,
                )
            )
        return items
