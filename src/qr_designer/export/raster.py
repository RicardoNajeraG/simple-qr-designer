"""Rasterizado directo desde la escena. Importar este módulo carga Pillow."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from qr_designer.config.models import hex_a_rgb
from qr_designer.scene.primitives import Circle, Escena, Path, Rect, Text

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


def rasterizar(escena: Escena, ancho: int, alto: int, formato: str) -> bytes:
    curvas = escena_tiene_curvas(escena)
    factor = factor_supersample(ancho, alto) if curvas else 1
    img, usados = _dibujar(escena, ancho * factor, alto * factor)
    if factor > 1:
        img = img.resize((ancho, alto), Image.Resampling.LANCZOS)

    formato = formato.lower()
    buf = BytesIO()
    if formato == "png":
        if curvas:
            paletada = img.quantize(colors=64, dither=Image.Dither.NONE)
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
