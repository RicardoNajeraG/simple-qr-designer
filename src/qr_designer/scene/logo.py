"""Hueco seguro para el logotipo, en coordenadas de módulo."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET

FINDER_MARGEN = 8
LOGO_FRAC = 0.22
LOGO_PAD = 1.0


def caja_logo(n: int) -> tuple[float, float, float, float]:
    """(x, y, w, h) centrada en la matriz, sin pisar finders ni separadores."""
    if n < 21:
        raise ValueError(f"Matriz QR demasiado pequeña para logo: {n}")
    usable = float(n - 2 * FINDER_MARGEN)
    max_lado = max(1.0, usable - 2 * LOGO_PAD)
    lado = min(float(n) * LOGO_FRAC, max_lado)
    x = (n - lado) / 2.0
    y = (n - lado) / 2.0
    return (x, y, lado, lado)


def ajustar_contain(
    caja: tuple[float, float, float, float],
    img_w: float,
    img_h: float,
) -> tuple[float, float, float, float]:
    """Ajusta la imagen dentro de `caja` sin recortar (letterbox)."""
    x, y, w, h = caja
    if img_w <= 0 or img_h <= 0:
        return caja
    escala = min(w / img_w, h / img_h)
    nw, nh = img_w * escala, img_h * escala
    return (x + (w - nw) / 2.0, y + (h - nh) / 2.0, nw, nh)


def ruta_logo_usable(ruta: str | None) -> Path | None:
    if not ruta or not str(ruta).strip():
        return None
    path = Path(str(ruta).strip())
    if path.is_file():
        return path
    return None


def logo_desde_perfil(perfil) -> Path | None:
    """Resuelve el archivo de logo: `logo_id` de catálogo gana sobre `logo_path`."""
    ident = getattr(perfil, "logo_id", None)
    if ident:
        from qr_designer.logos import LogoDesconocido, resolver_logo

        try:
            return resolver_logo(ident)
        except LogoDesconocido:
            return None
    return ruta_logo_usable(getattr(perfil, "logo_path", None))


def perfil_pide_logo(perfil) -> bool:
    return bool(getattr(perfil, "logo_id", None) or getattr(perfil, "logo_path", None))


def texto_svg(fuente: str | bytes) -> str:
    texto = fuente.decode("utf-8") if isinstance(fuente, bytes) else fuente
    texto = texto.lstrip("\ufeff")
    return re.sub(r"(?is)<!DOCTYPE[^>]*>", "", texto, count=1)


def _medida_svg(valor: str | None) -> float | None:
    if not valor:
        return None
    s = valor.strip()
    if s.endswith("%"):
        return None
    s = re.sub(r"(?i)(px|pt|em|ex|mm|cm|in|pc)$", "", s).strip()
    try:
        n = float(s)
    except ValueError:
        return None
    return n if n > 0 else None


def viewbox_svg(fuente: str | bytes) -> tuple[float, float, float, float]:
    """(minx, miny, width, height) del lienzo SVG."""
    root = ET.fromstring(texto_svg(fuente))
    vb = root.get("viewBox")
    if vb:
        partes = vb.replace(",", " ").split()
        if len(partes) == 4:
            minx, miny, w, h = (float(p) for p in partes)
            if w > 0 and h > 0:
                return minx, miny, w, h
    w = _medida_svg(root.get("width"))
    h = _medida_svg(root.get("height"))
    if w and h:
        return 0.0, 0.0, w, h
    return 0.0, 0.0, 100.0, 100.0


def dimensiones_svg(fuente: str | bytes) -> tuple[float, float]:
    _, _, w, h = viewbox_svg(fuente)
    return w, h


_DECL_XML = re.compile(r"<\?xml\b[^?]*\?>", re.IGNORECASE | re.DOTALL)
_TAG_SVG = re.compile(r"<svg\b[^>]*>", re.IGNORECASE)
_ATTR = re.compile(
    r'([:@A-Za-z_][\w:.-]*)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')',
)
_CIERRE_SVG = re.compile(r"</svg\s*>", re.IGNORECASE)


def _n_svg(v: float) -> str:
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _attrs_tag(tag: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _ATTR.finditer(tag):
        out[m.group(1)] = m.group(2) if m.group(2) is not None else m.group(3)
    return out


def svg_en_caja(fuente: str | bytes, x: float, y: float, w: float, h: float) -> str:
    """Inserta el dibujo del SVG en la caja, sin viewport interno que lo recorte."""
    texto = _DECL_XML.sub("", texto_svg(fuente)).strip()
    m = _TAG_SVG.search(texto)
    if not m:
        return ""
    minx, miny, vw, vh = viewbox_svg(texto)
    if vw <= 0 or vh <= 0 or w <= 0 or h <= 0:
        return ""
    tag = m.group(0)
    if tag.rstrip().endswith("/>"):
        inner = ""
    else:
        cierre = _CIERRE_SVG.search(texto)
        inner = texto[m.end() : cierre.start()] if cierre else texto[m.end() :]
    escala = min(w / vw, h / vh)
    ox = x + (w - vw * escala) / 2.0
    oy = y + (h - vh * escala) / 2.0
    attrs = _attrs_tag(tag)
    ns = [
        f'{k}="{v}"'
        for k, v in attrs.items()
        if k == "xmlns" or k.startswith("xmlns:")
    ]
    if not any(k == "xmlns" for k in attrs):
        ns.insert(0, 'xmlns="http://www.w3.org/2000/svg"')
    tf = (
        f"translate({_n_svg(ox)} {_n_svg(oy)}) "
        f"scale({_n_svg(escala)}) "
        f"translate({_n_svg(-minx)} {_n_svg(-miny)})"
    )
    extra = (" " + " ".join(ns)) if ns else ""
    return f'<g transform="{tf}"{extra}>{inner}</g>'
