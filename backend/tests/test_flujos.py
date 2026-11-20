"""Auth, incidencias, pedidos de compra, recepción y trazabilidad (RN-03/04/06/07/08/09)."""

from datetime import datetime, timezone

from app.models import Turno
from app.turnos import turno_de
from tests.conftest import como


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_sin_usuario_responde_401(client):
    assert client.get("/repuestos").status_code == 401
    assert client.get("/repuestos", headers=como("desconocido")).status_code == 401


def test_me_devuelve_el_rol(client):
    assert client.get("/me", headers=como("gerencia")).json()["rol"] == "gerencia"


def test_gerencia_es_solo_lectura(client):
    r = client.post("/maquinas", headers=como("gerencia"), json={"codigo": "X", "nombre": "X", "tipo": "x"})
    assert r.status_code == 403


def test_turno_se_deriva_del_timestamp():
    # Hora de Argentina = UTC-3
    assert turno_de(datetime(2026, 11, 20, 10, tzinfo=timezone.utc)) == Turno.manana  # 07 h
    assert turno_de(datetime(2026, 11, 20, 18, tzinfo=timezone.utc)) == Turno.tarde  # 15 h
    assert turno_de(datetime(2026, 11, 21, 2, tzinfo=timezone.utc)) == Turno.noche  # 23 h


def test_incidencia_identifica_la_maquina_por_codigo_y_notifica(planta, client, correos):
    maquina = planta.maquina("MAQ-F04")

    r = client.post("/incidencias", headers=como("operario"),
                    json={"maquina_codigo": "MAQ-F04", "titulo": "Pérdida", "descripcion": "Gotea", "prioridad": "alta"})

    assert r.status_code == 201
    assert r.json()["maquina_id"] == maquina["id"]
    assert r.json()["estado"] == "abierta"
    assert r.json()["turno"] in {"mañana", "tarde", "noche"}
    assert correos.enviados[-1].asunto.startswith(f"Incidencia #{r.json()['id']}")


def test_incidencia_con_maquina_inexistente_da_404(client):
    r = client.post("/incidencias", headers=como("operario"),
                    json={"maquina_codigo": "NO-EXISTE", "titulo": "x", "descripcion": "x"})
    assert r.status_code == 404


def test_foto_de_incidencia(planta, client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.servicios.UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr("app.rutas.incidencias.UPLOAD_DIR", str(tmp_path))
    planta.maquina()
    incidencia = client.post("/incidencias", headers=como("operario"),
                             json={"maquina_codigo": "MAQ-1", "titulo": "x", "descripcion": "x"}).json()

    r = client.post(f"/incidencias/{incidencia['id']}/fotos", headers=como("operario"),
                    files={"foto": ("falla.png", b"\x89PNG datos", "image/png")})
    assert r.status_code == 201
    assert client.get(f"/fotos/{r.json()['id']}", headers=como("encargado")).content == b"\x89PNG datos"

    r = client.post(f"/incidencias/{incidencia['id']}/fotos", headers=como("operario"),
                    files={"foto": ("x.txt", b"hola", "text/plain")})
    assert r.status_code == 409


def test_finalizar_correctiva_resuelve_la_incidencia_y_envia_informe(planta, client, correos):
    planta.maquina()
    reparacion = planta.reparacion_correctiva()
    assert client.get(f"/incidencias/{reparacion['incidencia_id']}", headers=como("gerencia")).json()["estado"] == "en_reparacion"

    client.post(f"/reparaciones/{reparacion['id']}/finalizar", headers=como("mantenimiento"),
                json={"informe": "Se cambió el sello"})

    assert client.get(f"/incidencias/{reparacion['incidencia_id']}", headers=como("gerencia")).json()["estado"] == "resuelta"
    assert correos.enviados[-1].asunto.startswith("Informe de resolución")
    assert set(correos.enviados[-1].destinatarios) == {"encargado@planta.local", "gerencia@planta.local"}


def test_pedido_de_compra_se_notifica_con_urgencia_a_encargados_y_gerencia(planta, client, correos):
    repuesto = planta.repuesto(fisico=0)

    r = client.post("/pedidos", headers=como("mantenimiento"),
                    json={"urgencia": "urgente", "lineas": [{"repuesto_id": repuesto["id"], "cantidad": 5}]})

    assert r.status_code == 201
    assert r.json()["estado"] == "pendiente"
    assert correos.enviados[-1].asunto == f"[URGENTE] Pedido de compra #{r.json()['id']}"
    assert set(correos.enviados[-1].destinatarios) == {"encargado@planta.local", "gerencia@planta.local"}


def test_recepcion_carga_stock_y_ubicacion_y_completa_la_trazabilidad(planta, client):
    repuesto = planta.repuesto(fisico=0)
    planta.maquina()
    pedido = client.post("/pedidos", headers=como("mantenimiento"),
                         json={"lineas": [{"repuesto_id": repuesto["id"], "cantidad": 5}]}).json()

    r = client.post(f"/pedidos/{pedido['id']}/recepcion", headers=como("encargado"),
                    json={"lineas": [{"repuesto_id": repuesto["id"], "cantidad": 5, "ubicacion_codigo": "b-04-09"}]})
    assert r.status_code == 200 and r.json()["estado"] == "recibido"
    stock = planta.stock(repuesto["id"])
    assert (stock["stock_fisico"], stock["ubicacion_codigo"]) == (5, "B-04-09")

    reparacion = planta.reparacion_correctiva()
    planta.usar(reparacion["id"], "RP-1", 1)
    historia = client.get(f"/repuestos/{repuesto['id']}/movimientos", headers=como("gerencia")).json()
    assert [(m["tipo"], m["referencia"]) for m in historia] == [
        ("entrada", f"pedido:{pedido['id']}"),
        ("salida", f"reparacion:{reparacion['id']}"),
    ]

    r = client.post(f"/pedidos/{pedido['id']}/recepcion", headers=como("encargado"),
                    json={"lineas": [{"repuesto_id": repuesto["id"], "cantidad": 5, "ubicacion_codigo": "B-04-09"}]})
    assert r.status_code == 409


def test_ubicacion_con_formato_invalido_se_rechaza(planta, client):
    repuesto = planta.repuesto(fisico=0)
    r = client.post(f"/repuestos/{repuesto['id']}/ingresos", headers=como("encargado"),
                    json={"cantidad": 1, "ubicacion_codigo": "pasillo a"})
    assert r.status_code == 422


def test_alta_de_maquina_con_su_lista_de_repuestos_y_busqueda_por_maquina(planta, client):
    repuesto = planta.repuesto("RP-9", fisico=0)

    r = client.post("/maquinas", headers=como("encargado"),
                    json={"codigo": "MAQ-NEW", "nombre": "Caldera nueva", "tipo": "caldera",
                          "repuesto_ids": [repuesto["id"]]})

    assert r.status_code == 201
    assert [x["codigo"] for x in r.json()["repuestos"]] == ["RP-9"]
    encontrados = client.get("/repuestos", params={"q": "caldera nueva"}, headers=como("operario")).json()
    assert [x["codigo"] for x in encontrados] == ["RP-9"]
    escaneado = client.get("/repuestos/codigo/RP-9", headers=como("operario")).json()
    assert escaneado["maquinas"][0]["codigo"] == "MAQ-NEW"


def test_movimientos_recientes_del_tablero(planta, client):
    repuesto = planta.repuesto(fisico=5)
    planta.maquina()
    reparacion = planta.reparacion_correctiva()
    planta.usar(reparacion["id"], "RP-1", 1)

    movimientos = client.get("/movimientos", params={"limite": 1}, headers=como("gerencia")).json()

    assert [(m["tipo"], m["repuesto_id"]) for m in movimientos] == [("salida", repuesto["id"])]
