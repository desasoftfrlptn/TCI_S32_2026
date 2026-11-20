"""El turno se deriva del timestamp (decisión de cátedra 4)."""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import PLANTA_TZ
from app.models import Turno


def turno_de(momento: datetime) -> Turno:
    """Mañana 06–14 h, tarde 14–22 h, noche 22–06 h (hora local de planta)."""
    hora = momento.astimezone(ZoneInfo(PLANTA_TZ)).hour
    if 6 <= hora < 14:
        return Turno.manana
    if 14 <= hora < 22:
        return Turno.tarde
    return Turno.noche
