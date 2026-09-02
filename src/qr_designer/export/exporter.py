"""Exportación a SVG / PNG / WEBP. Pillow solo se importa al rasterizar."""

from __future__ import annotations

from dataclasses import dataclass, replace

from qr_designer.config.contrast import correccion_para_matriz
from qr_designer.config.models import Perfil, SolicitudQR
from qr_designer.core.encoder import QRDesignerError, codificar
from qr_designer.render.svg import escena_a_svg
from qr_designer.scene.builders import construir_escena
from qr_designer.scene.logo import logo_desde_perfil, perfil_pide_logo
from qr_designer.scene.primitives import Escena

PX_MODULO_DEFECTO = 8
PX_MODULO_MIN = 1
DIMENSION_MAX = 4096
FORMATOS = frozenset({"svg", "png", "webp"})


class ExportacionError(QRDesignerError):
    pass


@dataclass(frozen=True)
class ResultadoExport:
    datos: bytes
    formato: str
    peso: int
    ancho: int
    alto: int
    advertencias: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "peso", len(self.datos))


def perfil_para_exportar(perfil: Perfil) -> Perfil:
    ecc = correccion_para_matriz(perfil, exportar=True)
    if ecc is perfil.correccion:
        return perfil
    return replace(perfil, correccion=ecc)


def construir_escena_export(solicitud: SolicitudQR) -> Escena:
    perfil = perfil_para_exportar(solicitud.perfil)
    matriz = codificar(solicitud.contenido, perfil.correccion)
    return construir_escena(matriz, perfil)


def resolucion_recomendada(escena: Escena, px_modulo: int = PX_MODULO_DEFECTO) -> tuple[int, int]:
    if px_modulo < PX_MODULO_MIN:
        raise ExportacionError(f"px por módulo debe ser ≥ {PX_MODULO_MIN}")
    ancho = max(1, round(escena.width * px_modulo))
    alto = max(1, round(escena.height * px_modulo))
    return ancho, alto


def exportar(
    solicitud: SolicitudQR,
    formato: str,
    px_modulo: int | None = None,
) -> ResultadoExport:
    fmt = formato.lower().lstrip(".")
    if fmt not in FORMATOS:
        raise ExportacionError(f"Formato no soportado: {formato}")
    escena = construir_escena_export(solicitud)
    avisos: list[str] = []
    if perfil_pide_logo(solicitud.perfil) and logo_desde_perfil(solicitud.perfil) is None:
        avisos.append("No se encontró el archivo del logotipo")
    if fmt == "svg":
        datos = escena_a_svg(escena).encode("utf-8")
        return ResultadoExport(
            datos=datos,
            formato="svg",
            peso=len(datos),
            ancho=round(escena.width),
            alto=round(escena.height),
            advertencias=tuple(avisos),
        )
    px = PX_MODULO_DEFECTO if px_modulo is None else px_modulo
    if px <= 1:
        avisos.append("px por módulo muy bajo: la lectura en pantalla o impresa puede fallar")
    ancho, alto = resolucion_recomendada(escena, px)
    if ancho > DIMENSION_MAX or alto > DIMENSION_MAX:
        raise ExportacionError(
            f"Resolución {ancho}×{alto} supera el máximo {DIMENSION_MAX}px; reduce px por módulo"
        )
    from qr_designer.export.raster import rasterizar

    datos = rasterizar(escena, ancho, alto, fmt)
    return ResultadoExport(
        datos=datos,
        formato=fmt,
        peso=len(datos),
        ancho=ancho,
        alto=alto,
        advertencias=tuple(avisos),
    )
