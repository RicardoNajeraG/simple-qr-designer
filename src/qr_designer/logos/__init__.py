"""Catálogo de logotipos empaquetados, referenciados por id (stem del archivo)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

EXTENSIONES = frozenset({".png", ".svg", ".jpg", ".jpeg", ".webp", ".gif"})


class LogoDesconocido(KeyError):
    """Id de catálogo que no corresponde a ningún archivo."""

    def __init__(self, ident: str) -> None:
        super().__init__(ident)
        self.id = ident


@dataclass(frozen=True)
class EntradaLogo:
    id: str
    nombre: str
    filename: str
    path: Path


def _nombre_visible(stem: str) -> str:
    return stem.replace("_", " ").strip() or stem


def _raiz_catalogo(raiz: Path | None = None) -> Path:
    if raiz is not None:
        return Path(raiz)
    trav = files("qr_designer.logos")
    try:
        return Path(os.fspath(trav))
    except TypeError:
        return Path(__file__).resolve().parent


def listar_logos(raiz: Path | None = None) -> tuple[EntradaLogo, ...]:
    directorio = _raiz_catalogo(raiz)
    if not directorio.is_dir():
        return ()
    vistos: set[str] = set()
    out: list[EntradaLogo] = []
    for path in sorted(directorio.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() not in EXTENSIONES:
            continue
        ident = path.stem
        if ident in vistos:
            continue
        vistos.add(ident)
        out.append(
            EntradaLogo(
                id=ident,
                nombre=_nombre_visible(ident),
                filename=path.name,
                path=path.resolve(),
            )
        )
    return tuple(out)


def resolver_logo(ident: str, raiz: Path | None = None) -> Path:
    clave = str(ident).strip()
    for entrada in listar_logos(raiz=raiz):
        if entrada.id == clave:
            return entrada.path
    raise LogoDesconocido(clave)
