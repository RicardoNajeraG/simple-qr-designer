"""DTO: dict <-> modelos de dominio. Sin tkinter ni Pillow."""

from __future__ import annotations

from typing import Any

from qr_designer.config.models import Perfil
from qr_designer.export.exporter import ResultadoExport


def perfil_a_dict(perfil: Perfil) -> dict[str, Any]:
    return perfil.to_dict()


def perfil_desde_dict(data: dict[str, Any]) -> Perfil:
    if not isinstance(data, dict):
        raise ValueError("El perfil debe ser un objeto JSON")
    return Perfil.from_dict(data)


def resultado_a_dict(resultado: ResultadoExport) -> dict[str, Any]:
    return {
        "datos": resultado.datos,
        "formato": resultado.formato,
        "peso": resultado.peso,
        "ancho": resultado.ancho,
        "alto": resultado.alto,
        "advertencias": list(resultado.advertencias),
    }


def resultado_desde_dict(data: dict[str, Any]) -> ResultadoExport:
    return ResultadoExport(
        datos=data["datos"],
        formato=data["formato"],
        peso=int(data["peso"]),
        ancho=int(data["ancho"]),
        alto=int(data["alto"]),
        advertencias=tuple(data.get("advertencias") or ()),
    )
