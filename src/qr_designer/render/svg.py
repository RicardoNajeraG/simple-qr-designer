"""Escena → SVG minificado por concatenación de texto."""

from __future__ import annotations

import base64
from pathlib import Path as FsPath

from qr_designer.scene.logo import svg_en_caja
from qr_designer.scene.primitives import Circle, Escena, Imagen, Path, Primitiva, Rect, Text

_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}


def _n(v: float) -> str:
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _path_d(points: tuple[tuple[float, float], ...]) -> str:
    if not points:
        return ""
    partes = [f"M{_n(points[0][0])} {_n(points[0][1])}"]
    for x, y in points[1:]:
        partes.append(f"L{_n(x)} {_n(y)}")
    partes.append("Z")
    return "".join(partes)


def _item_svg(item: Primitiva) -> str:
    if isinstance(item, Rect):
        bits = [
            "<rect",
            f' x="{_n(item.x)}"',
            f' y="{_n(item.y)}"',
            f' width="{_n(item.w)}"',
            f' height="{_n(item.h)}"',
            f' fill="{item.fill}"',
        ]
        if item.rx:
            bits.append(f' rx="{_n(item.rx)}"')
        if item.ry:
            bits.append(f' ry="{_n(item.ry)}"')
        bits.append("/>")
        return "".join(bits)
    if isinstance(item, Circle):
        return (
            f'<circle cx="{_n(item.cx)}" cy="{_n(item.cy)}" r="{_n(item.r)}"'
            f' fill="{item.fill}"/>'
        )
    if isinstance(item, Path):
        return f'<path d="{_path_d(item.points)}" fill="{item.fill}"/>'
    if isinstance(item, Text):
        anchor = item.anchor
        return (
            f'<text x="{_n(item.x)}" y="{_n(item.y)}" fill="{item.fill}"'
            f' font-size="{_n(item.font_size)}" text-anchor="{anchor}"'
            f' font-family="sans-serif">{_esc(item.text)}</text>'
        )
    if isinstance(item, Imagen):
        return _imagen_svg(item)
    raise TypeError(f"Primitiva desconocida: {type(item)!r}")


def _imagen_svg(item: Imagen) -> str:
    path = FsPath(item.ruta)
    try:
        bruto = path.read_bytes()
    except OSError:
        return ""
    if not bruto:
        return ""
    if path.suffix.lower() == ".svg":
        anidado = svg_en_caja(bruto, item.x, item.y, item.w, item.h)
        if anidado:
            return anidado
    mime = _MIME.get(path.suffix.lower(), "image/png")
    b64 = base64.b64encode(bruto).decode("ascii")
    return (
        f'<image href="data:{mime};base64,{b64}"'
        f' x="{_n(item.x)}" y="{_n(item.y)}"'
        f' width="{_n(item.w)}" height="{_n(item.h)}"'
        ' preserveAspectRatio="xMidYMid meet"/>'
    )


def escena_a_svg(escena: Escena) -> str:
    w, h = _n(escena.width), _n(escena.height)
    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">',
        f'<rect width="100%" height="100%" fill="{escena.background}"/>',
    ]
    for item in escena.items:
        partes.append(_item_svg(item))
    partes.append("</svg>")
    return "".join(partes)
