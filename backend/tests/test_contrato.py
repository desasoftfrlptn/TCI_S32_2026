"""El contrato publicado (contrato/openapi.json) debe coincidir con la API real."""

from scripts.exportar_openapi import DESTINO, contrato


def test_contrato_openapi_actualizado():
    assert DESTINO.exists(), "Falta el contrato: uv run python -m scripts.exportar_openapi"
    assert DESTINO.read_text(encoding="utf-8") == contrato(), (
        "El contrato quedó desactualizado: uv run python -m scripts.exportar_openapi"
    )
