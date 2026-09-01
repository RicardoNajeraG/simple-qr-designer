"""Resolución pura de ruta de salida y formato (sin tkinter)."""

from __future__ import annotations

from pathlib import Path

FORMATOS = frozenset({"svg", "png", "webp"})
_ETIQUETAS: tuple[tuple[str, str], ...] = (("svg", "SVG"), ("png", "PNG"), ("webp", "WEBP"))


def _normalizar_formato(formato_elegido: str) -> str:
    fmt = str(formato_elegido).lower().lstrip(".")
    if fmt not in FORMATOS:
        raise ValueError(f"Formato no soportado: {formato_elegido}")
    return fmt


def resolver_export(path_elegido: str | Path, formato_elegido: str) -> tuple[Path, str]:
    """Fuerza la extensión al formato elegido. El formato gana sobre el sufijo del path."""
    fmt = _normalizar_formato(formato_elegido)
    path = Path(path_elegido)
    return path.with_suffix(f".{fmt}"), fmt


def filetypes_para(formato: str) -> list[tuple[str, str]]:
    """Filtros del diálogo de guardado, con el formato elegido primero."""
    fmt = _normalizar_formato(formato)
    todos = [(etiqueta, f"*.{ext}") for ext, etiqueta in _ETIQUETAS]
    primero = next(par for par in todos if par[1] == f"*.{fmt}")
    return [primero, *[par for par in todos if par != primero]]
