"""Metadatos de la aplicación: versión desde pyproject y URL del repo."""

from __future__ import annotations

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


def version_app() -> str:
    """Versión publicada en pyproject.toml (o metadatos del paquete instalado)."""
    raiz = Path(__file__).resolve().parents[2]
    desde_toml = _version_desde_toml(raiz / "pyproject.toml")
    if desde_toml:
        return desde_toml
    try:
        return version(_NOMBRE_DIST)
    except PackageNotFoundError:
        return "0.0.0"
