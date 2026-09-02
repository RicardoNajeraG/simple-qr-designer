"""Rasteriza un SVG a RGBA con Pillow. Prefiere librsvg/Cairo; el fallback respeta CSS y fill heredado."""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw

from qr_designer.config.models import ColorInvalidoError, hex_a_rgb
from qr_designer.scene.logo import texto_svg, viewbox_svg

_SKIP = frozenset(
    {"defs", "clipPath", "mask", "symbol", "metadata", "style", "title", "desc", "script"}
)
_NO_DIBUJA = frozenset({"svg", "g", "a", "use"})
_NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_PATH_TOK = re.compile(r"[MmLlHhVvZzCcSsQqTtAa]|" + _NUM.pattern)
_RGB = re.compile(
    r"rgba?\(\s*([\d.]+%?)\s*[, ]\s*([\d.]+%?)\s*[, ]\s*([\d.]+%?)"
    r"(?:\s*[,/]\s*[\d.]+%?)?\s*\)",
    re.IGNORECASE,
)
_SS = 4
_SS_MAX = 2048


def svg_a_rgba(ruta: str | Path, ancho: int, alto: int) -> Image.Image:
    ancho = max(1, int(ancho))
    alto = max(1, int(alto))
    factor = _SS
    if max(ancho, alto) * factor > _SS_MAX:
        factor = max(1, _SS_MAX // max(ancho, alto))
    sw, sh = ancho * factor, alto * factor
    img = _svg_nativo(Path(ruta), sw, sh)
    if img.size != (ancho, alto):
        img = img.resize((ancho, alto), Image.Resampling.LANCZOS)
    return img


def _svg_nativo(path: Path, ancho: int, alto: int) -> Image.Image:
    bruto = path.read_bytes()
    png = _via_rsvg(bruto, ancho, alto)
    if png is None:
        png = _via_cairo(bruto, ancho, alto)
    if png is not None:
        return Image.open(BytesIO(png)).convert("RGBA")
    return _svg_simple_rgba(texto_svg(bruto), max(1, ancho), max(1, alto))


def _via_rsvg(bruto: bytes, ancho: int, alto: int) -> bytes | None:
    exe = shutil.which("rsvg-convert")
    if not exe:
        return None
    tmp = None
    proc = None
    try:
        fd, tmp = tempfile.mkstemp(suffix=".svg")
        try:
            os.write(fd, bruto)
        finally:
            os.close(fd)
        proc = subprocess.run(
            [exe, "-w", str(ancho), "-h", str(alto), "-f", "png", tmp],
            capture_output=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    if proc is None or proc.returncode != 0 or not proc.stdout.startswith(b"\x89PNG"):
        return None
    return proc.stdout


def _via_cairo(bruto: bytes, ancho: int, alto: int) -> bytes | None:
    try:
        import cairosvg
    except ImportError:
        return None
    try:
        png = cairosvg.svg2png(bytestring=bruto, output_width=ancho, output_height=alto)
    except Exception:
        return None
    return png if png and png.startswith(b"\x89PNG") else None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _estilo_bloque(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for parte in raw.split(";"):
        if ":" not in parte:
            continue
        k, v = parte.split(":", 1)
        out[k.strip().lower()] = v.replace("!important", "").strip()
    return out


def _estilo(el: ET.Element) -> dict[str, str]:
    return _estilo_bloque(el.get("style") or "")


def _hoja_estilos(root: ET.Element) -> dict[str, dict[str, str]]:
    reglas: dict[str, dict[str, str]] = {}
    for el in root.iter():
        if _local(el.tag) != "style":
            continue
        texto = re.sub(r"/\*.*?\*/", "", "".join(el.itertext()), flags=re.DOTALL)
        for m in re.finditer(r"([^{}]+)\{([^{}]+)\}", texto):
            props = _estilo_bloque(m.group(2))
            for sel in m.group(1).split(","):
                s = sel.strip()
                if s:
                    reglas.setdefault(s, {}).update(props)
    return reglas


def _css_de(el: ET.Element, reglas: dict[str, dict[str, str]]) -> dict[str, str]:
    out: dict[str, str] = {}
    tag = _local(el.tag)
    out.update(reglas.get(tag, {}))
    for cls in (el.get("class") or "").split():
        out.update(reglas.get(f".{cls}", {}))
        out.update(reglas.get(f"{tag}.{cls}", {}))
    ident = el.get("id")
    if ident:
        out.update(reglas.get(f"#{ident}", {}))
    return out


def _svg_color_rgb(valor: str) -> tuple[int, int, int] | None:
    v = valor.strip()
    if not v:
        return None
    bajo = v.lower()
    if bajo in ("none", "transparent") or bajo.startswith("url("):
        return None
    m = _RGB.match(v)
    if m:
        def canal(tok: str) -> int:
            tok = tok.strip()
            if tok.endswith("%"):
                return max(0, min(255, round(float(tok[:-1]) * 2.55)))
            return max(0, min(255, round(float(tok))))

        return canal(m.group(1)), canal(m.group(2)), canal(m.group(3))
    try:
        return hex_a_rgb(v)
    except ColorInvalidoError:
        return None


def _f(valor: str | None, default: float = 1.0) -> float:
    if valor is None or valor == "":
        return default
    try:
        return float(valor)
    except ValueError:
        return default


def _pick(nombre: str, estilo: dict[str, str], css: dict[str, str], el: ET.Element) -> str | None:
    if nombre in estilo:
        return estilo[nombre]
    if nombre in css:
        return css[nombre]
    return el.get(nombre)


def _rgba(
    fill: str,
    color: str,
    opacity: float,
    fill_opacity: float,
) -> tuple[int, int, int, int] | None:
    crudo = fill.strip() if fill else ""
    if not crudo:
        crudo = "#000000"
    if crudo.lower() == "currentcolor":
        crudo = color
    rgb = _svg_color_rgb(crudo)
    if rgb is None:
        return None
    a = max(0.0, min(1.0, opacity * fill_opacity))
    return (*rgb, int(round(a * 255)))


_IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
_TFN = re.compile(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(\s*([^)]*)\)", re.I)


def _mul_m(
    m1: tuple[float, float, float, float, float, float],
    m2: tuple[float, float, float, float, float, float],
) -> tuple[float, float, float, float, float, float]:
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _apply_m(
    m: tuple[float, float, float, float, float, float], x: float, y: float
) -> tuple[float, float]:
    a, b, c, d, e, f = m
    return a * x + c * y + e, b * x + d * y + f


def _tf_one(fn: str, nums: list[float]) -> tuple[float, float, float, float, float, float]:
    if fn == "translate":
        tx = nums[0] if nums else 0.0
        ty = nums[1] if len(nums) > 1 else 0.0
        return (1.0, 0.0, 0.0, 1.0, tx, ty)
    if fn == "scale":
        sx = nums[0] if nums else 1.0
        sy = nums[1] if len(nums) > 1 else sx
        return (sx, 0.0, 0.0, sy, 0.0, 0.0)
    if fn == "rotate":
        ang = math.radians(nums[0] if nums else 0.0)
        cos_a, sin_a = math.cos(ang), math.sin(ang)
        rot = (cos_a, sin_a, -sin_a, cos_a, 0.0, 0.0)
        if len(nums) >= 3:
            cx, cy = nums[1], nums[2]
            return _mul_m(_mul_m((1, 0, 0, 1, cx, cy), rot), (1, 0, 0, 1, -cx, -cy))
        return rot
    if fn == "matrix" and len(nums) >= 6:
        a, b, c, d, e, f = nums[:6]
        return (a, b, c, d, e, f)
    if fn == "skewx":
        t = math.tan(math.radians(nums[0] if nums else 0.0))
        return (1.0, 0.0, t, 1.0, 0.0, 0.0)
    if fn == "skewy":
        t = math.tan(math.radians(nums[0] if nums else 0.0))
        return (1.0, t, 0.0, 1.0, 0.0, 0.0)
    return _IDENT


def _parse_transform(s: str | None) -> tuple[float, float, float, float, float, float]:
    m = _IDENT
    if not s:
        return m
    for fn, args in _TFN.findall(s):
        nums = [float(x) for x in _NUM.findall(args)]
        m = _mul_m(m, _tf_one(fn.lower(), nums))
    return m


def _arc_points(
    x1: float,
    y1: float,
    rx: float,
    ry: float,
    phi_deg: float,
    fa: float,
    fs: float,
    x2: float,
    y2: float,
    n: int = 16,
) -> list[tuple[float, float]]:
    rx, ry = abs(rx), abs(ry)
    if rx < 1e-12 or ry < 1e-12:
        return [(x2, y2)]
    phi = math.radians(phi_deg % 360.0)
    cos_p, sin_p = math.cos(phi), math.sin(phi)
    dx = (x1 - x2) / 2.0
    dy = (y1 - y2) / 2.0
    x1p = cos_p * dx + sin_p * dy
    y1p = -sin_p * dx + cos_p * dy
    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1.0:
        sl = math.sqrt(lam)
        rx, ry = rx * sl, ry * sl
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    sign = 1.0 if (fa != 0) != (fs != 0) else -1.0
    coef = sign * math.sqrt(max(0.0, num / den)) if den else 0.0
    cxp = coef * (rx * y1p) / ry
    cyp = coef * -(ry * x1p) / rx
    cx = cos_p * cxp - sin_p * cyp + (x1 + x2) / 2.0
    cy = sin_p * cxp + cos_p * cyp + (y1 + y2) / 2.0

    def _ang(ux: float, uy: float, vx: float, vy: float) -> float:
        nrm = math.hypot(ux, uy) * math.hypot(vx, vy)
        if nrm == 0:
            return 0.0
        ang = math.acos(max(-1.0, min(1.0, (ux * vx + uy * vy) / nrm)))
        if ux * vy - uy * vx < 0:
            ang = -ang
        return ang

    ux, uy = (x1p - cxp) / rx, (y1p - cyp) / ry
    vx, vy = (-x1p - cxp) / rx, (-y1p - cyp) / ry
    theta1 = _ang(1.0, 0.0, ux, uy)
    dtheta = _ang(ux, uy, vx, vy)
    if fs == 0 and dtheta > 0:
        dtheta -= 2 * math.pi
    elif fs != 0 and dtheta < 0:
        dtheta += 2 * math.pi
    pts: list[tuple[float, float]] = []
    for i in range(1, n + 1):
        t = theta1 + dtheta * i / n
        ct, st = math.cos(t), math.sin(t)
        pts.append((cx + rx * ct * cos_p - ry * st * sin_p, cy + rx * ct * sin_p + ry * st * cos_p))
    return pts


def _floats(texto: str | None) -> list[float]:
    return [float(m.group(0)) for m in _NUM.finditer(texto or "")]


def _puntos(texto: str | None) -> list[tuple[float, float]]:
    nums = _floats(texto)
    return list(zip(nums[::2], nums[1::2], strict=False))


def _cubic(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int = 24,
) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for i in range(steps + 1):
        t = i / steps
        u = 1.0 - t
        x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts


def _quad(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    steps: int = 16,
) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for i in range(steps + 1):
        t = i / steps
        u = 1.0 - t
        x = u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]
        y = u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]
        pts.append((x, y))
    return pts


def _path_poligonos(d: str) -> list[list[tuple[float, float]]]:
    toks = _PATH_TOK.findall(d)
    i = 0
    cx = cy = sx = sy = 0.0
    cmd = "M"
    polys: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []

    def take(n: int) -> list[float] | None:
        nonlocal i
        if i + n > len(toks):
            return None
        vals: list[float] = []
        for k in range(n):
            t = toks[i + k]
            if t.isalpha():
                return None
            vals.append(float(t))
        i += n
        return vals

    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz":
                if cur:
                    polys.append(cur)
                cur = []
                cx, cy = sx, sy
                continue
        abs_ = cmd.isupper()
        c = cmd.upper()
        if c == "M":
            xy = take(2)
            if xy is None:
                break
            x, y = xy
            if not abs_:
                x += cx
                y += cy
            if cur:
                polys.append(cur)
            cur = [(x, y)]
            cx, cy = sx, sy = x, y
            cmd = "L" if abs_ else "l"
        elif c == "L":
            xy = take(2)
            if xy is None:
                break
            x, y = xy
            if not abs_:
                x += cx
                y += cy
            cur.append((x, y))
            cx, cy = x, y
        elif c == "H":
            xs = take(1)
            if xs is None:
                break
            x = xs[0] if abs_ else xs[0] + cx
            cur.append((x, cy))
            cx = x
        elif c == "V":
            ys = take(1)
            if ys is None:
                break
            y = ys[0] if abs_ else ys[0] + cy
            cur.append((cx, y))
            cy = y
        elif c == "C":
            vals = take(6)
            if vals is None:
                break
            x1, y1, x2, y2, x, y = vals
            if not abs_:
                x1 += cx
                y1 += cy
                x2 += cx
                y2 += cy
                x += cx
                y += cy
            cur.extend(_cubic((cx, cy), (x1, y1), (x2, y2), (x, y))[1:])
            cx, cy = x, y
        elif c == "Q":
            vals = take(4)
            if vals is None:
                break
            x1, y1, x, y = vals
            if not abs_:
                x1 += cx
                y1 += cy
                x += cx
                y += cy
            cur.extend(_quad((cx, cy), (x1, y1), (x, y))[1:])
            cx, cy = x, y
        elif c == "S":
            vals = take(4)
            if vals is None:
                break
            x2, y2, x, y = vals
            if not abs_:
                x2 += cx
                y2 += cy
                x += cx
                y += cy
            cur.extend(_cubic((cx, cy), (cx, cy), (x2, y2), (x, y))[1:])
            cx, cy = x, y
        elif c == "T":
            xy = take(2)
            if xy is None:
                break
            x, y = xy
            if not abs_:
                x += cx
                y += cy
            cur.append((x, y))
            cx, cy = x, y
        elif c == "A":
            vals = take(7)
            if vals is None:
                break
            rx, ry, phi, fa, fs, x, y = vals
            if not abs_:
                x += cx
                y += cy
            cur.extend(_arc_points(cx, cy, rx, ry, phi, fa, fs, x, y))
            cx, cy = x, y
        else:
            break
    if cur:
        polys.append(cur)
    return polys


def _href(el: ET.Element) -> str:
    return (
        el.get("href")
        or el.get("{http://www.w3.org/1999/xlink}href")
        or ""
    )


def _stroke_px(
    sw: float,
    m: tuple[float, float, float, float, float, float],
    scale: float,
) -> int:
    a, b, c, d, _e, _f = m
    mag = (math.hypot(a, b) + math.hypot(c, d)) / 2.0
    return max(1, round(sw * mag * scale))


def _svg_simple_rgba(texto: str, ancho: int, alto: int) -> Image.Image:
    minx, miny, vw, vh = viewbox_svg(texto)
    img = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    scale = min(ancho / vw, alto / vh)
    ox = (ancho - vw * scale) / 2.0 - minx * scale
    oy = (alto - vh * scale) / 2.0 - miny * scale

    def xy(
        x: float,
        y: float,
        m: tuple[float, float, float, float, float, float],
    ) -> tuple[float, float]:
        x, y = _apply_m(m, x, y)
        return (x * scale + ox, y * scale + oy)

    def pix(
        pts: list[tuple[float, float]],
        m: tuple[float, float, float, float, float, float],
    ) -> list[tuple[float, float]]:
        return [xy(x, y, m) for x, y in pts]

    root = ET.fromstring(texto_svg(texto))
    reglas = _hoja_estilos(root)
    ids: dict[str, ET.Element] = {}
    for el in root.iter():
        ident = el.get("id")
        if ident:
            ids[ident] = el

    def trazar(
        pts: list[tuple[float, float]],
        fill: tuple[int, int, int, int] | None,
        stroke: tuple[int, int, int, int] | None,
        sw: int,
        cerrado: bool,
    ) -> None:
        if fill is not None and len(pts) >= 3:
            draw.polygon(pts, fill=fill)
        if stroke is not None and len(pts) >= 2:
            linea = list(pts)
            if cerrado and linea[0] != linea[-1]:
                linea.append(linea[0])
            draw.line(linea, fill=stroke, width=sw)

    def pintar(
        el: ET.Element,
        m: tuple[float, float, float, float, float, float],
        fill: tuple[int, int, int, int] | None,
        stroke: tuple[int, int, int, int] | None,
        sw: int,
    ) -> None:
        name = _local(el.tag)
        if name == "rect":
            x = float(el.get("x", 0) or 0)
            y = float(el.get("y", 0) or 0)
            w = float(el.get("width", 0) or 0)
            h = float(el.get("height", 0) or 0)
            if w <= 0 or h <= 0:
                return
            pts = pix([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], m)
            trazar(pts, fill, stroke, sw, True)
        elif name == "circle":
            cx = float(el.get("cx", 0) or 0)
            cy = float(el.get("cy", 0) or 0)
            r = float(el.get("r", 0) or 0)
            if r <= 0:
                return
            x0, y0 = xy(cx - r, cy - r, m)
            x1, y1 = xy(cx + r, cy + r, m)
            kw: dict = {}
            if fill is not None:
                kw["fill"] = fill
            if stroke is not None:
                kw["outline"] = stroke
                kw["width"] = sw
            if kw:
                draw.ellipse([x0, y0, x1, y1], **kw)
        elif name == "ellipse":
            cx = float(el.get("cx", 0) or 0)
            cy = float(el.get("cy", 0) or 0)
            rx = float(el.get("rx", 0) or 0)
            ry = float(el.get("ry", 0) or 0)
            if rx <= 0 or ry <= 0:
                return
            x0, y0 = xy(cx - rx, cy - ry, m)
            x1, y1 = xy(cx + rx, cy + ry, m)
            kw = {}
            if fill is not None:
                kw["fill"] = fill
            if stroke is not None:
                kw["outline"] = stroke
                kw["width"] = sw
            if kw:
                draw.ellipse([x0, y0, x1, y1], **kw)
        elif name in {"polygon", "polyline"}:
            pts = pix(_puntos(el.get("points")), m)
            trazar(pts, fill, stroke, sw, name == "polygon")
        elif name == "line":
            x1 = float(el.get("x1", 0) or 0)
            y1 = float(el.get("y1", 0) or 0)
            x2 = float(el.get("x2", 0) or 0)
            y2 = float(el.get("y2", 0) or 0)
            trazar([xy(x1, y1, m), xy(x2, y2, m)], None, stroke, sw, False)
        elif name == "path":
            for poly in _path_poligonos(el.get("d") or ""):
                pts = pix(poly, m)
                cerrado = len(pts) >= 3 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1.5
                trazar(pts, fill, stroke, sw, cerrado)

    def walk(
        el: ET.Element,
        fill: str,
        color: str,
        opacity: float,
        fill_opacity: float,
        stroke: str,
        stroke_width: float,
        matrix: tuple[float, float, float, float, float, float],
        visiting: set[int],
    ) -> None:
        name = _local(el.tag)
        if name in _SKIP:
            return
        estilo = _estilo(el)
        css = _css_de(el, reglas)
        nuevo_fill = _pick("fill", estilo, css, el)
        if nuevo_fill is not None:
            fill = nuevo_fill
        nuevo_color = _pick("color", estilo, css, el)
        if nuevo_color is not None:
            color = nuevo_color
        nuevo_stroke = _pick("stroke", estilo, css, el)
        if nuevo_stroke is not None:
            stroke = nuevo_stroke
        nuevo_sw = _pick("stroke-width", estilo, css, el)
        if nuevo_sw is not None:
            stroke_width = _f(nuevo_sw, stroke_width)
        own_op = _pick("opacity", estilo, css, el)
        if own_op is not None:
            opacity *= _f(own_op, 1.0)
        own_fo = _pick("fill-opacity", estilo, css, el)
        if own_fo is not None:
            fill_opacity *= _f(own_fo, 1.0)
        tm = _mul_m(matrix, _parse_transform(el.get("transform")))
        if name == "use":
            href = _href(el)
            if href.startswith("#"):
                ref = ids.get(href[1:])
                oid = id(ref) if ref is not None else 0
                if ref is not None and oid not in visiting:
                    visiting.add(oid)
                    ux = float(el.get("x", 0) or 0)
                    uy = float(el.get("y", 0) or 0)
                    um = _mul_m(tm, (1.0, 0.0, 0.0, 1.0, ux, uy))
                    ref_name = _local(ref.tag)
                    if ref_name in {"symbol", "svg", "g", "defs"}:
                        for child in list(ref):
                            walk(
                                child, fill, color, opacity, fill_opacity,
                                stroke, stroke_width, um, visiting,
                            )
                    else:
                        walk(
                            ref, fill, color, opacity, fill_opacity,
                            stroke, stroke_width, um, visiting,
                        )
                    visiting.discard(oid)
            return
        if name not in _NO_DIBUJA:
            rgba = _rgba(fill, color, opacity, fill_opacity)
            stroke_rgba = _rgba(stroke, color, opacity, 1.0) if stroke else None
            sw = _stroke_px(stroke_width, tm, scale)
            pintar(el, tm, rgba, stroke_rgba, sw)
        for child in list(el):
            walk(child, fill, color, opacity, fill_opacity, stroke, stroke_width, tm, visiting)

    walk(root, "#000000", "#000000", 1.0, 1.0, "none", 1.0, _IDENT, set())
    return img
