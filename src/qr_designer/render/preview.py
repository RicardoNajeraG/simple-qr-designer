"""Preview raster con el mismo pipeline que el export. Pillow se importa perezoso."""

from __future__ import annotations

from qr_designer.config.models import Perfil
from qr_designer.scene.builders import escena_desde_contenido
from qr_designer.scene.primitives import Escena

PREVIEW_MAX_LADO = 400.0


def px_para_preview(escena: Escena, max_lado: float = PREVIEW_MAX_LADO) -> int:
    """Píxeles enteros por módulo, el máximo que cabe en max_lado."""
    lado = max(float(escena.width), float(escena.height), 1.0)
    return max(1, int(float(max_lado) // lado))


def preview_png(
    contenido: str,
    perfil: Perfil,
    max_lado: float = PREVIEW_MAX_LADO,
) -> bytes:
    from qr_designer.export.exporter import resolucion_recomendada
    from qr_designer.export.raster import rasterizar

    escena = escena_desde_contenido(contenido, perfil)
    px = px_para_preview(escena, max_lado)
    ancho, alto = resolucion_recomendada(escena, px)
    return rasterizar(escena, ancho, alto, "png")
