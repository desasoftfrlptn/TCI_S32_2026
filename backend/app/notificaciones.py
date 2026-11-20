"""Puerto de notificación (RN-09) y sus adaptadores.

Los servicios solo conocen `Notificador`; el adaptador se elige por
configuración (NOTIFICADOR=log | smtp) sin tocar la lógica de negocio.
"""

import logging
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol

log = logging.getLogger("planta.notificaciones")


class Notificador(Protocol):
    def enviar(self, destinatarios: list[str], asunto: str, cuerpo: str) -> None: ...


class NotificadorLog:
    """Adaptador falso por defecto: escribe el correo en el log."""

    def enviar(self, destinatarios: list[str], asunto: str, cuerpo: str) -> None:
        log.info("CORREO para=%s asunto=%r\n%s", ", ".join(destinatarios), asunto, cuerpo)


class NotificadorSMTP:
    """Envía correo real por SMTP (Mailhog en desarrollo).

    Un fallo de envío se registra pero no revierte la operación de negocio,
    que ya fue confirmada en la base.
    """

    def __init__(self, host: str, puerto: int, remitente: str):
        self.host = host
        self.puerto = puerto
        self.remitente = remitente

    def enviar(self, destinatarios: list[str], asunto: str, cuerpo: str) -> None:
        mensaje = EmailMessage()
        mensaje["From"] = self.remitente
        mensaje["To"] = ", ".join(destinatarios)
        mensaje["Subject"] = asunto
        mensaje.set_content(cuerpo)
        try:
            with smtplib.SMTP(self.host, self.puerto, timeout=5) as smtp:
                smtp.send_message(mensaje)
        except (OSError, smtplib.SMTPException):
            log.exception("No se pudo enviar el correo %r a %s", asunto, destinatarios)


@dataclass
class Correo:
    destinatarios: list[str]
    asunto: str
    cuerpo: str


@dataclass
class NotificadorMemoria:
    """Adaptador para tests: guarda los correos enviados."""

    enviados: list[Correo] = field(default_factory=list)

    def enviar(self, destinatarios: list[str], asunto: str, cuerpo: str) -> None:
        self.enviados.append(Correo(destinatarios, asunto, cuerpo))
