"""Fachada JSON-friendly: contenido + perfil dict → SVG / raster / evaluación."""

from __future__ import annotations

from typing import Any

from qr_designer.config.contrast import (
    correccion_para_matriz,
    ecc_recomendada_por_estilo,
    evaluar_contraste,
)
from qr_designer.config.models import Perfil, SolicitudQR
from qr_designer.core.encoder import MatrizQR, codificar
from qr_designer.export.exporter import ResultadoExport, exportar
from qr_designer.render.svg import escena_a_svg
from qr_designer.scene.builders import construir_escena
from qr_designer.scene.primitives import Escena
from qr_designer.service.dto import perfil_desde_dict, resultado_a_dict


def generar_svg(contenido: str, perfil_dict: dict[str, Any]) -> str:
    perfil = perfil_desde_dict(perfil_dict)
    escena = construir_escena(codificar(contenido, correccion_para_matriz(perfil)), perfil)
    return escena_a_svg(escena)


def exportar_qr(
    contenido: str,
    perfil_dict: dict[str, Any],
    formato: str,
    px_modulo: int | None = None,
) -> dict[str, Any]:
    perfil = perfil_desde_dict(perfil_dict)
    resultado: ResultadoExport = exportar(
        SolicitudQR(contenido, perfil), formato, px_modulo=px_modulo
    )
    return resultado_a_dict(resultado)


def evaluar(perfil_dict: dict[str, Any]) -> dict[str, Any]:
    perfil = perfil_desde_dict(perfil_dict)
    ev = evaluar_contraste(perfil)
    return {
        "ok": ev.ok,
        "invertido": ev.invertido,
        "bajo_contraste": ev.bajo_contraste,
        "baja_ocupacion": ev.baja_ocupacion,
        "ratio_modulos": ev.ratio_modulos,
        "ratio_ojos": ev.ratio_ojos,
        "ratio_marco": ev.ratio_marco,
        "fill_ratio": ev.fill_ratio,
        "advertencias": list(ev.advertencias),
        "ecc_recomendada": ecc_recomendada_por_estilo(perfil),
    }


def listar_logos() -> list[dict[str, str]]:
    from qr_designer.logos import listar_logos as catalogo

    return [{"id": e.id, "nombre": e.nombre} for e in catalogo()]


def previsualizar(
    contenido: str, perfil_dict: dict[str, Any]
) -> tuple[Escena | None, MatrizQR | None]:
    if not contenido or not str(contenido).strip():
        return None, None
    perfil = perfil_desde_dict(perfil_dict)
    matriz = codificar(contenido, correccion_para_matriz(perfil))
    return construir_escena(matriz, perfil), matriz
