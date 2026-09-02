"""Rasterizado directo desde la escena. Importar este módulo carga Pillow."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path as FsPath
from xml.etree.ElementTree import ParseError

from PIL import Image, ImageDraw, ImageFont

from qr_designer.config.models import hex_a_rgb
from qr_designer.scene.logo import ajustar_contain, dimensiones_svg
from qr_designer.scene.primitives import Circle, Escena, Imagen, Path, Rect, Text

FACTOR_SUPERSAMPLE = 4
MAX_INTERMEDIO = 8192


def _color(fill: str) -> tuple[int, int, int]:
    return hex_a_rgb(fill)


def escena_tiene_curvas(escena: Escena) -> bool:
    for item in escena.items:
        if isinstance(item, (Circle, Path)):
            return True
        if isinstance(item, Rect) and (item.rx or item.ry):
            return True
    return False


def escena_tiene_logo(escena: Escena) -> bool:
    return any(isinstance(item, Imagen) for item in escena.items)


def factor_supersample(ancho: int, alto: int, factor: int = FACTOR_SUPERSAMPLE) -> int:
    max_lado = max(int(ancho), int(alto), 1)
    if max_lado * factor > MAX_INTERMEDIO:
        factor = MAX_INTERMEDIO // max_lado
    return max(1, factor)


def _dibujar(escena: Escena, ancho: int, alto: int) -> tuple[Image.Image, set[tuple[int, int, int]]]:
    sx, sy = ancho / escena.width, alto / escena.height
    rgb = _color(escena.background)
    img = Image.new("RGB", (ancho, alto), rgb)
    draw = ImageDraw.Draw(img)
    usados = {rgb}

    def sx_pt(x: float, y: float) -> tuple[int, int]:
        return round(x * sx), round(y * sy)

    for item in escena.items:
        if isinstance(item, Imagen):
            continue
        fill = _color(item.fill)
        usados.add(fill)
        if isinstance(item, Rect):
            x0, y0 = sx_pt(item.x, item.y)
            x1, y1 = sx_pt(item.x + item.w, item.y + item.h)
            if x1 <= x0:
                x1 = x0 + 1
            if y1 <= y0:
                y1 = y0 + 1
            if item.rx or item.ry:
                rx = max(0, round(item.rx * sx))
                ry = max(0, round(item.ry * sy))
                rad = min(rx, ry)
                draw.rounded_rectangle([x0, y0, x1, y1], radius=rad, fill=fill)
            else:
                draw.rectangle([x0, y0, x1, y1], fill=fill)
        elif isinstance(item, Circle):
            r = max(1, round(item.r * min(sx, sy)))
            cx, cy = sx_pt(item.cx, item.cy)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
        elif isinstance(item, Path):
            pts = [sx_pt(x, y) for x, y in item.points]
            if len(pts) >= 3:
                draw.polygon(pts, fill=fill)
        elif isinstance(item, Text):
            try:
                font = ImageFont.load_default(size=max(8, round(item.font_size * min(sx, sy))))
            except TypeError:
                font = ImageFont.load_default()
            draw.text(
                sx_pt(item.x, item.y),
                item.text,
                fill=fill,
                font=font,
                anchor="ms" if item.anchor == "middle" else None,
            )
    return img, usados


def _dimensiones_logo(ruta: str) -> tuple[float, float]:
    path = FsPath(ruta)
    if path.suffix.lower() == ".svg":
        return dimensiones_svg(path.read_bytes())
    with Image.open(path) as im:
        return float(im.width), float(im.height)


def _logo_rgba(ruta: str, dw: int, dh: int) -> Image.Image:
    path = FsPath(ruta)
    if path.suffix.lower() == ".svg":
        from qr_designer.export.svg_raster import svg_a_rgba

        return svg_a_rgba(path, dw, dh)
    logo = Image.open(path).convert("RGBA")
    return logo.resize((dw, dh), Image.Resampling.LANCZOS)


def _pegar_logos(escena: Escena, img: Image.Image, ancho: int, alto: int) -> Image.Image:
    sx, sy = ancho / escena.width, alto / escena.height
    out = img.convert("RGBA")
    for item in escena.items:
        if not isinstance(item, Imagen):
            continue
        try:
            iw, ih = _dimensiones_logo(item.ruta)
            fit = ajustar_contain((item.x, item.y, item.w, item.h), iw, ih)
            dw = max(1, round(fit[2] * sx))
            dh = max(1, round(fit[3] * sy))
            logo = _logo_rgba(item.ruta, dw, dh)
        except (OSError, ValueError, ParseError):
            continue
        px = round(fit[0] * sx)
        py = round(fit[1] * sy)
        capa = Image.new("RGBA", out.size, (0, 0, 0, 0))
        capa.paste(logo, (px, py), logo)
        out = Image.alpha_composite(out, capa)
    return out.convert("RGB")


def rasterizar(escena: Escena, ancho: int, alto: int, formato: str) -> bytes:
    curvas = escena_tiene_curvas(escena)
    con_logo = escena_tiene_logo(escena)
    factor = factor_supersample(ancho, alto) if curvas else 1
    img, usados = _dibujar(escena, ancho * factor, alto * factor)
    if factor > 1:
        img = img.resize((ancho, alto), Image.Resampling.LANCZOS)
    if con_logo:
        img = _pegar_logos(escena, img, ancho, alto)

    formato = formato.lower()
    buf = BytesIO()
    if formato == "png":
        if con_logo:
            img.save(buf, format="PNG", optimize=True, compress_level=9)
        elif curvas:
            paletada = img.quantize(colors=64, dither=Image.Dither.NONE)
            paletada.save(buf, format="PNG", optimize=True, compress_level=9)
        else:
            paletada = _a_paleta(img, usados)
            paletada.save(buf, format="PNG", optimize=True, compress_level=9)
    elif formato == "webp":
        img.save(buf, format="WEBP", lossless=True, quality=100, method=4)
    else:
        raise ValueError(f"Raster no soporta {formato}")
    return buf.getvalue()


def _a_paleta(img: Image.Image, colores: set[tuple[int, int, int]]) -> Image.Image:
    lista = list(colores)
    pal = Image.new("P", (1, 1))
    raw: list[int] = []
    for r, g, b in lista:
        raw.extend([r, g, b])
    raw.extend([0, 0, 0] * (256 - len(lista)))
    pal.putpalette(raw)
    return img.quantize(palette=pal, dither=Image.Dither.NONE)
