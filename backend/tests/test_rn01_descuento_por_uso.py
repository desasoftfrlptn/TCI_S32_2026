"""RN-01 — Usar un repuesto descuenta la cantidad del stock físico; nunca queda negativo."""

from tests.conftest import como


def test_uso_descuenta_la_cantidad_del_stock_fisico(planta):
    repuesto = planta.repuesto(fisico=10)
    planta.maquina()
    reparacion = planta.reparacion_correctiva()

    r = planta.usar(reparacion["id"], "RP-1", 3)

    assert r.status_code == 201
    assert r.json()["cantidad"] == 3
    assert planta.stock(repuesto["id"])["stock_fisico"] == 7


def test_uso_queda_registrado_como_movimiento_de_salida(planta, client):
    repuesto = planta.repuesto(fisico=5)
    planta.maquina()
    reparacion = planta.reparacion_correctiva()
    planta.usar(reparacion["id"], "RP-1", 2)

    movimientos = client.get(f"/repuestos/{repuesto['id']}/movimientos", headers=como("gerencia")).json()

    assert [(m["tipo"], m["cantidad"]) for m in movimientos] == [("entrada", 5), ("salida", 2)]
    assert movimientos[-1]["referencia"] == f"reparacion:{reparacion['id']}"


def test_uso_que_dejaria_stock_negativo_se_rechaza(planta):
    repuesto = planta.repuesto(fisico=2)
    planta.maquina()
    reparacion = planta.reparacion_correctiva()

    r = planta.usar(reparacion["id"], "RP-1", 3)

    assert r.status_code == 409
    assert "pedido de compra" in r.json()["detail"]
    assert planta.stock(repuesto["id"])["stock_fisico"] == 2


def test_se_puede_usar_hasta_la_ultima_unidad(planta):
    repuesto = planta.repuesto(fisico=2)
    planta.maquina()
    reparacion = planta.reparacion_correctiva()

    assert planta.usar(reparacion["id"], "RP-1", 2).status_code == 201
    assert planta.stock(repuesto["id"])["stock_fisico"] == 0
    assert planta.usar(reparacion["id"], "RP-1", 1).status_code == 409


def test_cantidad_debe_ser_al_menos_uno(planta):
    planta.repuesto()
    planta.maquina()
    reparacion = planta.reparacion_correctiva()

    assert planta.usar(reparacion["id"], "RP-1", 0).status_code == 422


def test_operario_no_puede_registrar_uso(planta):
    planta.repuesto()
    planta.maquina()
    reparacion = planta.reparacion_correctiva()

    assert planta.usar(reparacion["id"], "RP-1", 1, usuario="operario").status_code == 403


def test_no_se_registra_uso_en_reparacion_finalizada(planta, client):
    planta.repuesto()
    planta.maquina()
    reparacion = planta.reparacion_correctiva()
    client.post(f"/reparaciones/{reparacion['id']}/finalizar", headers=como("mantenimiento"),
                json={"informe": "Listo"})

    assert planta.usar(reparacion["id"], "RP-1", 1).status_code == 409
