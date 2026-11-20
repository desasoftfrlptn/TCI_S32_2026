"""RN-05 — Lo reservado no se usa en otra incidencia; liberar exige Encargado y aviso inmediato.
RN-10 — Ejecutar el preventivo descuenta el físico y libera la reserva en la misma transacción.
"""

from tests.conftest import como


def escenario(planta, fisico=5, reservado=4):
    repuesto = planta.repuesto(fisico=fisico, umbral=0)
    preventivo = planta.preventivo()
    reserva = planta.reservar(preventivo["id"], repuesto["id"], reservado)
    planta.maquina()
    correctiva = planta.reparacion_correctiva()
    return repuesto, preventivo, reserva, correctiva


def test_unidades_reservadas_no_se_pueden_usar_en_otra_incidencia(planta):
    repuesto, _, _, correctiva = escenario(planta, fisico=5, reservado=4)

    assert planta.usar(correctiva["id"], "RP-1", 2).status_code == 409
    assert planta.usar(correctiva["id"], "RP-1", 1).status_code == 201
    stock = planta.stock(repuesto["id"])
    assert (stock["stock_fisico"], stock["stock_reservado"], stock["stock_disponible"]) == (4, 4, 0)


def test_no_se_puede_reservar_mas_que_el_disponible(planta, client):
    repuesto = planta.repuesto(fisico=3, umbral=0)
    preventivo = planta.preventivo()

    r = client.post("/reservas", headers=como("encargado"),
                    json={"reparacion_id": preventivo["id"], "repuesto_id": repuesto["id"], "cantidad": 4})

    assert r.status_code == 409


def test_solo_se_reserva_para_mantenimiento_preventivo(planta, client):
    repuesto, _, _, correctiva = escenario(planta)

    r = client.post("/reservas", headers=como("encargado"),
                    json={"reparacion_id": correctiva["id"], "repuesto_id": repuesto["id"], "cantidad": 1})

    assert r.status_code == 409


def test_liberar_sin_rol_encargado_se_rechaza_y_la_reserva_sigue_activa(planta, client):
    repuesto, _, reserva, _ = escenario(planta)

    for usuario in ("mantenimiento", "operario", "gerencia"):
        r = client.post(f"/reservas/{reserva['id']}/liberar", headers=como(usuario), json={"motivo": "urgencia"})
        assert r.status_code == 403

    assert planta.stock(repuesto["id"])["stock_reservado"] == 4


def test_encargado_libera_la_reserva_y_se_avisa_de_inmediato(planta, client, correos):
    repuesto, preventivo, reserva, correctiva = escenario(planta)

    r = client.post(f"/reservas/{reserva['id']}/liberar", headers=como("encargado"),
                    json={"motivo": "Parada de la línea 2"})

    assert r.status_code == 200
    assert r.json()["estado"] == "liberada"
    assert planta.stock(repuesto["id"])["stock_disponible"] == 5
    aviso = correos.enviados[-1]
    assert aviso.asunto.startswith(f"Reserva #{reserva['id']} liberada")
    assert f"preventivo #{preventivo['id']}" in aviso.cuerpo
    assert set(aviso.destinatarios) == {"encargado@planta.local", "mantenimiento@planta.local"}
    # ahora sí se puede usar en la otra incidencia
    assert planta.usar(correctiva["id"], "RP-1", 5).status_code == 201


def test_una_reserva_liberada_no_se_libera_dos_veces(planta, client):
    _, _, reserva, _ = escenario(planta)
    client.post(f"/reservas/{reserva['id']}/liberar", headers=como("encargado"), json={"motivo": "x"})

    r = client.post(f"/reservas/{reserva['id']}/liberar", headers=como("encargado"), json={"motivo": "x"})

    assert r.status_code == 409


def test_rn10_ejecutar_preventivo_descuenta_fisico_y_consume_la_reserva(planta, client):
    repuesto, preventivo, reserva, _ = escenario(planta, fisico=5, reservado=4)

    r = client.post(f"/reparaciones/{preventivo['id']}/finalizar", headers=como("mantenimiento"),
                    json={"informe": "Preventivo ejecutado"})

    assert r.status_code == 200
    stock = planta.stock(repuesto["id"])
    assert (stock["stock_fisico"], stock["stock_reservado"]) == (1, 0)
    reservas = client.get("/reservas", headers=como("gerencia")).json()
    assert reservas[0]["id"] == reserva["id"] and reservas[0]["estado"] == "consumida"
    tipos = [m["tipo"] for m in client.get(f"/repuestos/{repuesto['id']}/movimientos", headers=como("gerencia")).json()]
    assert tipos == ["entrada", "reserva", "consumo"]
