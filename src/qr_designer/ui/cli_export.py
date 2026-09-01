"""Exportación headless por argv. No importa tkinter ni Pillow al cargar el módulo."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from qr_designer.config.models import SolicitudQR
from qr_designer.config.presets import preset_clasico, preset_por_nombre
from qr_designer.export.exporter import exportar


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="qr-designer",
        description="Genera códigos QR personalizables (SVG/PNG/WEBP).",
    )
    p.add_argument("--url", "--text", dest="url", help="Contenido a codificar")
    p.add_argument("-o", "--output", help="Ruta de salida")
    p.add_argument("--preset", default="Clásico", help="Nombre de preset de fábrica")
    p.add_argument("--format", choices=("svg", "png", "webp"), help="Formato (si no se infiere de -o)")
    p.add_argument("--px", type=int, default=None, help="Píxeles por módulo (PNG/WEBP)")
    return p


def exportar_desde_argv(argv: Sequence[str]) -> int:
    ns = _parser().parse_args(list(argv))
    if not ns.url or not ns.output:
        _parser().error("se requiere --url y -o/--output")
    perfil = preset_por_nombre(ns.preset) or preset_clasico()
    if ns.preset != "Clásico" and preset_por_nombre(ns.preset) is None:
        raise SystemExit(f"Preset desconocido: {ns.preset}")
    destino = Path(ns.output)
    fmt = ns.format or destino.suffix.lstrip(".").lower() or "svg"
    resultado = exportar(SolicitudQR(contenido=ns.url, perfil=perfil), fmt, px_modulo=ns.px)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(resultado.datos)
    print(
        f"Exportado {destino} ({resultado.peso} bytes, {resultado.ancho}×{resultado.alto} {resultado.formato})"
    )
    return 0
