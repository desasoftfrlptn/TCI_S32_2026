"""Exporta el contrato OpenAPI de la API a contrato/openapi.json.

Uso (desde backend/): uv run python -m scripts.exportar_openapi
El contrato es la fuente para el mock de Prism y para el frontend.
"""

import json
from pathlib import Path

from app.main import app

DESTINO = Path(__file__).resolve().parents[2] / "contrato" / "openapi.json"


def contrato() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n"


if __name__ == "__main__":
    DESTINO.write_text(contrato(), encoding="utf-8")
    print(f"Contrato exportado en {DESTINO}")
