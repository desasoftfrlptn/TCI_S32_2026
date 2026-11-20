import os

# Hash rápido en tests: las contraseñas de prueba no necesitan 600k iteraciones.
os.environ.setdefault("PBKDF2_ITERACIONES", "1000")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app.db import get_session  # noqa: E402
from app.deps import get_notificador  # noqa: E402
from app.main import app  # noqa: E402
from app.notificaciones import NotificadorMemoria  # noqa: E402
from app.seed import crear_usuarios  # noqa: E402
from app.seguridad import crear_token  # noqa: E402


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        crear_usuarios(session)
        yield session


@pytest.fixture
def correos():
    return NotificadorMemoria()


@pytest.fixture
def client(session, correos):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_notificador] = lambda: correos
    yield TestClient(app)
    app.dependency_overrides.clear()


def como(usuario: str) -> dict[str, str]:
    """Header de autenticación con un token válido para `usuario`."""
    return {"Authorization": f"Bearer {crear_token(usuario)}"}


class Planta:
    """Atajos para armar escenarios a través de la API."""

    def __init__(self, client: TestClient):
        self.c = client

    def repuesto(self, codigo="RP-1", fisico=10, umbral=2) -> dict:
        r = self.c.post("/repuestos", headers=como("encargado"),
                        json={"codigo": codigo, "nombre": f"Repuesto {codigo}", "umbral_minimo": umbral})
        assert r.status_code == 201, r.text
        if fisico:
            r = self.c.post(f"/repuestos/{r.json()['id']}/ingresos", headers=como("encargado"),
                            json={"cantidad": fisico, "ubicacion_codigo": "A-01-01"})
            assert r.status_code == 200, r.text
        return r.json()

    def maquina(self, codigo="MAQ-1") -> dict:
        r = self.c.post("/maquinas", headers=como("encargado"),
                        json={"codigo": codigo, "nombre": f"Máquina {codigo}", "tipo": "caldera"})
        assert r.status_code == 201, r.text
        return r.json()

    def reparacion_correctiva(self, maquina_codigo="MAQ-1") -> dict:
        r = self.c.post("/incidencias", headers=como("operario"),
                        json={"maquina_codigo": maquina_codigo, "titulo": "Falla", "descripcion": "Detalle"})
        assert r.status_code == 201, r.text
        r = self.c.post("/reparaciones", headers=como("mantenimiento"),
                        json={"tipo": "correctiva", "descripcion": "Arreglo", "incidencia_id": r.json()["id"]})
        assert r.status_code == 201, r.text
        return r.json()

    def preventivo(self) -> dict:
        r = self.c.post("/reparaciones", headers=como("encargado"),
                        json={"tipo": "preventiva", "descripcion": "Preventivo mensual"})
        assert r.status_code == 201, r.text
        return r.json()

    def reservar(self, reparacion_id: int, repuesto_id: int, cantidad: int) -> dict:
        r = self.c.post("/reservas", headers=como("encargado"),
                        json={"reparacion_id": reparacion_id, "repuesto_id": repuesto_id, "cantidad": cantidad})
        assert r.status_code == 201, r.text
        return r.json()

    def usar(self, reparacion_id: int, codigo: str, cantidad: int, usuario="mantenimiento"):
        return self.c.post(f"/reparaciones/{reparacion_id}/usos", headers=como(usuario),
                           json={"repuesto_codigo": codigo, "cantidad": cantidad})

    def stock(self, repuesto_id: int) -> dict:
        return self.c.get(f"/repuestos/{repuesto_id}", headers=como("gerencia")).json()


@pytest.fixture
def planta(client):
    return Planta(client)
