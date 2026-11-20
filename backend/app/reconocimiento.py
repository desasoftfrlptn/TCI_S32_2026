"""Puerto de reconocimiento de repuestos a partir de una foto.

Adaptador por defecto: lee los códigos QR / de barras que aparecen en la foto
(la etiqueta del envase). Para reconocer la pieza por su aspecto se puede
implementar otro adaptador (por ejemplo, un modelo de visión) con la misma
interfaz, sin tocar el servicio.
"""

import io
from typing import Protocol

import zxingcpp
from PIL import Image, UnidentifiedImageError


class FotoInvalida(Exception):
    pass


class Reconocedor(Protocol):
    def codigos(self, foto: bytes) -> list[str]: ...


class ReconocedorCodigos:
    def codigos(self, foto: bytes) -> list[str]:
        try:
            imagen = Image.open(io.BytesIO(foto))
            imagen.load()
        except (UnidentifiedImageError, OSError) as error:
            raise FotoInvalida("El archivo no es una imagen válida") from error
        return [resultado.text.strip() for resultado in zxingcpp.read_barcodes(imagen) if resultado.text.strip()]
