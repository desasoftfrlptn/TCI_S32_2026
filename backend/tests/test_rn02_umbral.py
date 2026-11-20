"""RN-02 — Si stock disponible <= umbral mínimo: alerta + aparece en la lista de compras."""

from tests.conftest import como


def alertas(correos):
    return [c for c in correos.enviados if c.asunto.startswith("Alerta de umbral")]


def test_uso_que_alcanza_el_umbral_genera_alerta_y_entra_en_lista_de_compras(planta, client, correos):
    planta.repuesto(fisico=5, umbral=2)
    planta.maquina()
    reparacion = planta.reparacion_correctiva()

    planta.usar(reparacion["id"], "RP-1", 3)  # disponible 2 == umbral

    assert len(alertas(correos)) == 1
    assert alertas(correos)[0].destinatarios == ["encargado@planta.local"]
    lista = client.get("/lista-compras", headers=como("encargado")).json()
    assert [r["codigo"] for r in lista] == ["RP-1"]
    assert lista[0]["bajo_umbral"] is True


def test_uso_que_deja_stock_sobre_el_umbral_no_alerta(planta, client, correos):
    planta.repuesto(fisico=5, umbral=2)
    planta.maquina()
    reparacion = planta.reparacion_correctiva()

    planta.usar(reparacion["id"], "RP-1", 2)  # disponible 3 > umbral

    assert alertas(correos) == []
    assert client.get("/lista-compras", headers=como("encargado")).json() == []


def test_el_umbral_se_evalua_sobre_el_disponible_no_sobre_el_fisico(planta, client, correos):
    repuesto = planta.repuesto(fisico=5, umbral=2)
    preventivo = planta.preventivo()

    planta.reservar(preventivo["id"], repuesto["id"], 3)  # físico 5, disponible 2

    assert planta.stock(repuesto["id"])["stock_fisico"] == 5
    assert len(alertas(correos)) == 1
    assert [r["codigo"] for r in client.get("/lista-compras", headers=como("gerencia")).json()] == ["RP-1"]


def test_operario_no_ve_la_lista_de_compras(client):
    assert client.get("/lista-compras", headers=como("operario")).status_code == 403
