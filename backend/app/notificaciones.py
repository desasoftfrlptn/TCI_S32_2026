"""Puerto de notificación (RN-09) y sus adaptadores.

El correo real se enchufa implementando `Notificador` (por ejemplo, SMTP contra
Mailhog) sin tocar los servicios.
"""

import logging
from dataclasses import dataclass, field
from typing import Protocol

log = logging.getLogger("planta.notificaciones")


class Notificador(Protocol):
    def enviar(self, destinatarios: list[str], asunto: str, cuerpo: str) -> None: ...


class NotificadorLog:
    """Adaptador falso por defecto: escribe el correo en el log."""

    def enviar(self, destinatarios: list[str], asunto: str, cuerpo: str) -> None:
        log.info("CORREO para=%s asunto=%r\n%s", ", ".join(destinatarios), asunto, cuerpo)


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
