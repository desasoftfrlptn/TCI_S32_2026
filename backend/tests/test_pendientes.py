"""Autenticación real, correo SMTP, delegación/supervisión (RN-08),
requerimientos manuales en la lista de compras y reconocimiento por foto."""

import io
import smtplib
from datetime import timedelta

import jwt
import zxingcpp
from PIL import Image

from app.config import JWT_SECRET
from app.models import ahora
from app.notificaciones import NotificadorSMTP
from tests.conftest import como

# --- autenticación -------------------------------------------------------------


def login(client, usuario, password):
    return client.post("/auth/login", data={"username": usuario, "password": password})


def test_login_con_credenciales_correctas_devuelve_un_token_que_sirve(client):
    r = login(client, "encargado", "planta123")

    assert r.status_code == 200
    assert r.json()["usuario"]["rol"] == "encargado"
    token = r.json()["access_token"]
    assert client.get("/me", headers={"Authorization": f"Bearer {token}"}).json()["usuario"] == "encargado"


def test_login_con_password_incorrecta_responde_401(client):
    assert login(client, "encargado", "otra").status_code == 401
    assert login(client, "nadie", "planta123").status_code == 401


def test_token_vencido_o_adulterado_responde_401(client):
    vencido = jwt.encode({"sub": "encargado", "exp": ahora() - timedelta(minutes=1)}, JWT_SECRET, "HS256")
    adulterado = jwt.encode({"sub": "encargado", "exp": ahora() + timedelta(hours=1)}, "un-secreto-distinto-de-al-menos-32-bytes", "HS256")

    for token in (vencido, adulterado, "basura"):
        assert client.get("/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_las_contrasenas_no_se_guardan_en_texto_plano(session):
    from sqlmodel import select

    from app.models import Usuario

    usuario = session.exec(select(Usuario)).first()
    assert "planta123" not in usuario.password_hash
    assert usuario.password_hash.startswith("pbkdf2_sha256$")


# --- correo SMTP ---------------------------------------------------------------


def test_notificador_smtp_envia_el_mensaje(monkeypatch):
    enviados = []

    class SMTPFalso:
        def __init__(self, host, puerto, timeout):
            assert (host, puerto) == ("mailhog", 1025)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def send_message(self, mensaje):
            enviados.append(mensaje)

    monkeypatch.setattr(smtplib, "SMTP", SMTPFalso)
    NotificadorSMTP("mailhog", 1025, "planta@planta.local").enviar(["a@x", "b@x"], "Asunto", "Cuerpo")

    assert enviados[0]["To"] == "a@x, b@x"
    assert enviados[0]["Subject"] == "Asunto"


def test_si_el_servidor_de_correo_falla_la_operacion_no_se_rompe(monkeypatch):
    def caido(*args, **kwargs):
        raise ConnectionRefusedError

    monkeypatch.setattr(smtplib, "SMTP", caido)
    NotificadorSMTP("mailhog", 1025, "planta@planta.local").enviar(["a@x"], "Asunto", "Cuerpo")


# --- RN-08: delegación y supervisión ------------------------------------------


def pedido_pendiente(planta, client):
    repuesto = planta.repuesto(fisico=0)
    pedido = client.post("/pedidos", headers=como("mantenimiento"),
                         json={"lineas": [{"repuesto_id": repuesto["id"], "cantidad": 3}]}).json()
    return repuesto, pedido


def recibir(client, pedido, repuesto, usuario):
    return client.post(f"/pedidos/{pedido['id']}/recepcion", headers=como(usuario),
                       json={"lineas": [{"repuesto_id": repuesto["id"], "cantidad": 3, "ubicacion_codigo": "A-01-02"}]})


def id_de(client, usuario):
    return client.get("/me", headers=como(usuario)).json()["id"]


def test_mantenimiento_no_recibe_una_compra_que_no_le_delegaron(planta, client):
    repuesto, pedido = pedido_pendiente(planta, client)

    assert recibir(client, pedido, repuesto, "mantenimiento").status_code == 403


def test_encargado_delega_la_recepcion_y_luego_la_supervisa(planta, client, correos):
    repuesto, pedido = pedido_pendiente(planta, client)
    mantenimiento_id = id_de(client, "mantenimiento")

    r = client.post(f"/pedidos/{pedido['id']}/delegar", headers=como("encargado"), json={"usuario_id": mantenimiento_id})
    assert r.status_code == 200 and r.json()["delegado_a_id"] == mantenimiento_id
    assert correos.enviados[-1].destinatarios == ["mantenimiento@planta.local"]

    r = recibir(client, pedido, repuesto, "mantenimiento")
    assert r.status_code == 200
    assert (r.json()["estado"], r.json()["recibido_por_id"]) == ("recibido", mantenimiento_id)
    assert planta.stock(repuesto["id"])["stock_fisico"] == 3
    assert "pendiente de supervisión" in correos.enviados[-1].asunto

    r = client.post(f"/pedidos/{pedido['id']}/verificar", headers=como("encargado"))
    assert r.status_code == 200
    assert r.json()["estado"] == "verificado"
    assert r.json()["verificado_por_id"] == id_de(client, "encargado")


def test_solo_el_encargado_delega_y_verifica(planta, client):
    repuesto, pedido = pedido_pendiente(planta, client)

    r = client.post(f"/pedidos/{pedido['id']}/delegar", headers=como("mantenimiento"), json={"usuario_id": 1})
    assert r.status_code == 403
    recibir(client, pedido, repuesto, "encargado")
    assert client.post(f"/pedidos/{pedido['id']}/verificar", headers=como("mantenimiento")).status_code == 403


def test_no_se_delega_en_operario_ni_gerencia(planta, client):
    _, pedido = pedido_pendiente(planta, client)

    for usuario in ("operario", "gerencia"):
        r = client.post(f"/pedidos/{pedido['id']}/delegar", headers=como("encargado"),
                        json={"usuario_id": id_de(client, usuario)})
        assert r.status_code == 409


def test_no_se_verifica_un_pedido_sin_recibir(planta, client):
    _, pedido = pedido_pendiente(planta, client)

    assert client.post(f"/pedidos/{pedido['id']}/verificar", headers=como("encargado")).status_code == 409


# --- lista de compras con requerimientos manuales -----------------------------


def test_requerimientos_manuales_aparecen_en_la_lista_y_se_atienden_con_un_pedido(planta, client):
    repuesto = planta.repuesto(fisico=10, umbral=2)  # no está bajo umbral

    r = client.post("/requerimientos", headers=como("encargado"),
                    json={"repuesto_id": repuesto["id"], "cantidad": 4, "origen": "prevision",
                          "motivo": "Parada anual de planta en enero"})
    assert r.status_code == 201
    requerimiento = r.json()

    lista = client.get("/lista-compras", headers=como("encargado")).json()
    assert [(i["origen"], i["cantidad_sugerida"], i["requerimiento_id"]) for i in lista] == [
        ("prevision", 4, requerimiento["id"])
    ]

    r = client.post("/pedidos", headers=como("encargado"),
                    json={"lineas": [{"repuesto_id": repuesto["id"], "cantidad": 4}],
                          "requerimiento_ids": [requerimiento["id"]]})
    assert r.status_code == 201
    assert client.get("/lista-compras", headers=como("encargado")).json() == []

    r = client.post("/pedidos", headers=como("encargado"),
                    json={"lineas": [{"repuesto_id": repuesto["id"], "cantidad": 4}],
                          "requerimiento_ids": [requerimiento["id"]]})
    assert r.status_code == 409


def test_solo_el_encargado_carga_requerimientos(planta, client):
    repuesto = planta.repuesto()
    r = client.post("/requerimientos", headers=como("mantenimiento"),
                    json={"repuesto_id": repuesto["id"], "cantidad": 1, "origen": "especifico", "motivo": "x"})
    assert r.status_code == 403


# --- reconocimiento por foto ---------------------------------------------------


def foto_con_codigo(texto: str) -> bytes:
    codigo = zxingcpp.create_barcode(texto, zxingcpp.BarcodeFormat.QRCode).to_image(scale=6)
    alto, ancho = codigo.shape[:2]
    lienzo = Image.new("RGB", (ancho + 200, alto + 200), "white")  # el código ocupa parte de la foto
    lienzo.paste(Image.frombytes("L", (ancho, alto), bytes(memoryview(codigo))), (100, 100))
    buffer = io.BytesIO()
    lienzo.save(buffer, "JPEG")
    return buffer.getvalue()


def reconocer(client, contenido: bytes, tipo="image/jpeg"):
    return client.post("/repuestos/reconocer", headers=como("operario"), files={"foto": ("foto.jpg", contenido, tipo)})


def test_reconoce_el_repuesto_por_foto_e_informa_lo_pedido(planta, client):
    repuesto = planta.repuesto("RP-2048", fisico=4)
    maquina = client.post("/maquinas", headers=como("encargado"),
                          json={"codigo": "MAQ-F04", "nombre": "Fraccionadora F-04", "tipo": "fraccionador",
                                "repuesto_ids": [repuesto["id"]]}).json()

    r = reconocer(client, foto_con_codigo("RP-2048"))

    assert r.status_code == 200
    datos = r.json()
    assert (datos["codigo"], datos["nombre"], datos["stock_disponible"], datos["ubicacion_codigo"]) == (
        "RP-2048", "Repuesto RP-2048", 4, "A-01-01"
    )
    assert [m["codigo"] for m in datos["maquinas"]] == [maquina["codigo"]]


def test_foto_sin_codigo_o_con_codigo_desconocido_da_404(planta, client):
    planta.repuesto("RP-2048")
    blanca = io.BytesIO()
    Image.new("RGB", (200, 200), "white").save(blanca, "PNG")

    assert reconocer(client, blanca.getvalue(), "image/png").status_code == 404
    r = reconocer(client, foto_con_codigo("NO-EXISTE"))
    assert r.status_code == 404 and "NO-EXISTE" in r.json()["detail"]


def test_archivo_que_no_es_imagen_se_rechaza(client):
    assert reconocer(client, b"no soy una imagen", "image/jpeg").status_code == 409
