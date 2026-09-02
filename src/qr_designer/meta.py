"""Metadatos de la aplicación: versión desde pyproject y URL del repo."""

from __future__ import annotations

import sys
import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

REPO_URL = "https://github.com/RicardoNajeraG/simple-qr-designer"
_NOMBRE_DIST = "qr-designer"


def _version_desde_toml(ruta: Path) -> str | None:
    try:
        with ruta.open("rb") as fh:
            datos = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return None
    valor = datos.get("project", {}).get("version")
    return str(valor) if valor else None


def _rutas_pyproject() -> list[Path]:
    rutas: list[Path] = []
    try:
        rutas.append(Path(__file__).resolve().parents[2] / "pyproject.toml")
    except IndexError:
        pass
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        rutas.append(Path(meipass) / "pyproject.toml")
    if getattr(sys, "frozen", False):
        rutas.append(Path(sys.executable).resolve().parent / "pyproject.toml")
    return rutas


def version_app() -> str:
    """Versión publicada en pyproject.toml (o metadatos del paquete instalado)."""
    for ruta in _rutas_pyproject():
        desde_toml = _version_desde_toml(ruta)
        if desde_toml:
            return desde_toml
    try:
        return version(_NOMBRE_DIST)
    except PackageNotFoundError:
        return "0.0.0"
