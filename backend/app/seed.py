"""Datos iniciales de demostración. Idempotente: no hace nada si ya hay usuarios.

Uso: python -m app.seed
"""

from sqlmodel import Session, select

from app.config import SEED_PASSWORD
from app.models import (
    Maquina,
    MovimientoStock,
    Reparacion,
    Repuesto,
    Reserva,
    Rol,
    TipoMovimiento,
    TipoReparacion,
    Usuario,
)
from app.seguridad import hashear_password

USUARIOS = [
    ("operario", "Operario de demostración", "operario@planta.local", Rol.operario),
    ("mantenimiento", "Mantenimiento de demostración", "mantenimiento@planta.local", Rol.mantenimiento),
    ("encargado", "Encargado de demostración", "encargado@planta.local", Rol.encargado),
    ("gerencia", "Gerencia de demostración", "gerencia@planta.local", Rol.gerencia),
]

MAQUINAS = [
    ("MAQ-F04", "Fraccionadora F-04", "fraccionador"),
    ("MAQ-BT03", "Banda transportadora BT-03", "banda de transporte"),
    ("MAQ-E07", "Etiquetadora E-07", "etiquetadora"),
    ("MAQ-C01", "Caldera C-01", "caldera"),
]

# código, nombre, descripción, físico, umbral, ubicación, detalle, máquinas
REPUESTOS = [
    ("RP-2048", "Sello mecánico 32 mm", "Sello sanitario de carburo de silicio para bomba centrífuga.",
     4, 3, "A-03-12", "Pasillo A · Estante 03 · Nivel 12", ["MAQ-F04"]),
    ("RP-1190", "Rodamiento 6205-2RS", "Rodamiento rígido de bolas, sellado en ambos lados.",
     2, 4, "B-01-07", "Pasillo B · Estante 01 · Nivel 07", ["MAQ-BT03"]),
    ("IN-4421", "Filtro HEPA H14", "Filtro absoluto para módulo de flujo laminar 610 × 610 mm.",
     8, 2, "C-02-04", "Sector limpio C · Estante 02 · Nivel 04", []),
    ("RP-8870", "Correa dentada T10", "Correa de transmisión de poliuretano, ancho 25 mm.",
     0, 2, "A-06-02", "Pasillo A · Estante 06 · Nivel 02", ["MAQ-E07"]),
    ("IN-3022", "Aceite grado alimenticio", "Lubricante sintético NSF H1, envase de 1 litro.",
     18, 6, "D-01-03", "Depósito químico D · Estante 01 · Nivel 03", ["MAQ-C01"]),
    ("RP-5204", "Electroválvula 1/2”", "Electroválvula sanitaria de acero inoxidable, 24 VCC.",
     7, 3, "B-04-09", "Pasillo B · Estante 04 · Nivel 09", ["MAQ-F04"]),
]

# Reservas para un mantenimiento preventivo planificado: código → cantidad
RESERVAS = {"RP-2048": 2, "IN-4421": 1, "IN-3022": 4}


def crear_usuarios(session: Session, password: str = SEED_PASSWORD) -> None:
    password_hash = hashear_password(password)
    for usuario, nombre, email, rol in USUARIOS:
        session.add(Usuario(usuario=usuario, nombre=nombre, email=email, rol=rol, password_hash=password_hash))
    session.commit()


def cargar_demo(session: Session) -> None:
    encargado = session.exec(select(Usuario).where(Usuario.rol == Rol.encargado)).one()
    maquinas = {codigo: Maquina(codigo=codigo, nombre=nombre, tipo=tipo) for codigo, nombre, tipo in MAQUINAS}
    session.add_all(maquinas.values())

    repuestos: dict[str, Repuesto] = {}
    for codigo, nombre, descripcion, fisico, umbral, ubicacion, detalle, de_maquinas in REPUESTOS:
        repuesto = Repuesto(
            codigo=codigo, nombre=nombre, descripcion=descripcion, stock_fisico=fisico,
            umbral_minimo=umbral, ubicacion_codigo=ubicacion, ubicacion_descripcion=detalle,
            maquinas=[maquinas[m] for m in de_maquinas],
        )
        repuestos[codigo] = repuesto
        session.add(repuesto)
    session.flush()

    for repuesto in repuestos.values():
        if repuesto.stock_fisico:
            session.add(MovimientoStock(repuesto_id=repuesto.id, tipo=TipoMovimiento.entrada,
                                        cantidad=repuesto.stock_fisico, usuario_id=encargado.id,
                                        referencia="carga inicial"))

    preventivo = Reparacion(tipo=TipoReparacion.preventiva, descripcion="Mantenimiento preventivo mensual")
    session.add(preventivo)
    session.flush()
    for codigo, cantidad in RESERVAS.items():
        repuesto = repuestos[codigo]
        repuesto.stock_reservado += cantidad
        reserva = Reserva(reparacion_id=preventivo.id, repuesto_id=repuesto.id, cantidad=cantidad,
                          creada_por_id=encargado.id)
        session.add(reserva)
        session.flush()
        session.add(MovimientoStock(repuesto_id=repuesto.id, tipo=TipoMovimiento.reserva, cantidad=cantidad,
                                    usuario_id=encargado.id, referencia=f"reserva:{reserva.id}"))
    session.commit()


def main() -> None:
    from app.db import engine

    with Session(engine) as session:
        if session.exec(select(Usuario)).first():
            print("Seed: la base ya tiene datos, no se carga nada.")
            return
        crear_usuarios(session)
        cargar_demo(session)
        print("Seed: datos de demostración cargados.")


if __name__ == "__main__":
    main()
