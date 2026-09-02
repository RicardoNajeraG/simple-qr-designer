"""Matriz + perfil → Escena de primitivas."""

from __future__ import annotations

import math

from qr_designer.config.models import (
    MarcoTipo,
    ModuloEstilo,
    OjoEstilo,
    Perfil,
)
from qr_designer.core.encoder import MatrizQR, codificar
from qr_designer.scene.primitives import Circle, Escena, Imagen, Path, Primitiva, Rect, Text
from qr_designer.scene.logo import FINDER_MARGEN, caja_logo, logo_desde_perfil

FRAME_GROSOR = 1.5
TEXT_BANDA = 3.0
MARCO_TEXTO_DEFECTO = "ESCANÉAME"
RADIO_PUNTO = 0.4
RADIO_REDONDEADO = 0.32
SQUIRCLE_N = 4.0
SQUIRCLE_PASOS = 24
GOTA_PASOS = 16
BARRA_GROSOR = 0.65


def _pad(perfil: Perfil) -> tuple[float, float, float, float]:
    if perfil.marco_tipo is MarcoTipo.NINGUNO:
        return (0.0, 0.0, 0.0, 0.0)
    g = FRAME_GROSOR
    if perfil.marco_tipo is MarcoTipo.ESCANEAME:
        return (g, g, g, g + TEXT_BANDA)
    return (g, g, g, g)


def _superellipse(cx: float, cy: float, a: float, b: float, n: float, pasos: int) -> tuple[tuple[float, float], ...]:
    pts: list[tuple[float, float]] = []
    exp = 2.0 / n
    for i in range(pasos):
        t = 2 * math.pi * i / pasos
        ct, st = math.cos(t), math.sin(t)
        pts.append(
            (
                cx + a * math.copysign(abs(ct) ** exp, ct),
                cy + b * math.copysign(abs(st) ** exp, st),
            )
        )
    return tuple(pts)


def _gota_puntos(x: float, y: float) -> tuple[tuple[float, float], ...]:
    cx, cy = x + 0.5, y + 0.5
    pts: list[tuple[float, float]] = []
    for i in range(GOTA_PASOS):
        t = 2 * math.pi * i / GOTA_PASOS
        base = 0.36
        extra = 0.16 * max(0.0, math.cos(t - math.pi / 4))
        r = base + extra
        pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return tuple(pts)


def _rounded_rect_points(
    x: float,
    y: float,
    w: float,
    h: float,
    radios: tuple[float, float, float, float],
    pasos_esquina: int = 4,
) -> tuple[tuple[float, float], ...]:
    """radios: TL, TR, BR, BL."""
    rtl, rtr, rbr, rbl = radios
    pts: list[tuple[float, float]] = []

    def arco(cx: float, cy: float, r: float, a0: float, a1: float) -> None:
        if r <= 0:
            pts.append((cx, cy))
            return
        for i in range(pasos_esquina + 1):
            a = a0 + (a1 - a0) * i / pasos_esquina
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))

    arco(x + rtl, y + rtl, rtl, math.pi, 3 * math.pi / 2)
    arco(x + w - rtr, y + rtr, rtr, 3 * math.pi / 2, 2 * math.pi)
    arco(x + w - rbr, y + h - rbr, rbr, 0, math.pi / 2)
    arco(x + rbl, y + h - rbl, rbl, math.pi / 2, math.pi)
    return tuple(pts)


def _modulo_primitiva(
    estilo: ModuloEstilo,
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str,
    pid: str,
) -> Primitiva:
    if estilo is ModuloEstilo.CUADRADO:
        return Rect(id=pid, x=x, y=y, w=w, h=h, fill=fill, role="modulo")
    if estilo is ModuloEstilo.REDONDEADO:
        return Rect(
            id=pid,
            x=x + 0.05,
            y=y + 0.05 * (h / w if w else 1),
            w=w - 0.1,
            h=h - 0.1,
            fill=fill,
            role="modulo",
            rx=min(RADIO_REDONDEADO, (w - 0.1) / 2),
            ry=min(RADIO_REDONDEADO, (h - 0.1) / 2),
        )
    if estilo is ModuloEstilo.PUNTOS:
        r = RADIO_PUNTO * min(w, h)
        return Circle(id=pid, cx=x + w / 2, cy=y + h / 2, r=r, fill=fill, role="modulo")
    if estilo is ModuloEstilo.GOTA:
        if w == 1 and h == 1:
            return Path(id=pid, points=_gota_puntos(x, y), fill=fill, role="modulo")
        pts = _gota_puntos(0, 0)
        sx, sy = w, h
        scaled = tuple((x + px * sx, y + py * sy) for px, py in pts)
        return Path(id=pid, points=scaled, fill=fill, role="modulo")
    if estilo is ModuloEstilo.SQUIRCLE:
        pts = _superellipse(x + w / 2, y + h / 2, w / 2, h / 2, SQUIRCLE_N, SQUIRCLE_PASOS)
        return Path(id=pid, points=pts, fill=fill, role="modulo")
    # barras: pill
    inset = (1 - BARRA_GROSOR) / 2
    if w >= h:
        return Rect(
            id=pid,
            x=x,
            y=y + inset * (h if h == 1 else 1),
            w=w,
            h=h * BARRA_GROSOR if h == 1 else BARRA_GROSOR,
            fill=fill,
            role="modulo",
            rx=BARRA_GROSOR / 2,
            ry=BARRA_GROSOR / 2,
        )
    return Rect(
        id=pid,
        x=x + inset,
        y=y,
        w=BARRA_GROSOR,
        h=h,
        fill=fill,
        role="modulo",
        rx=BARRA_GROSOR / 2,
        ry=BARRA_GROSOR / 2,
    )


def _celdas_modulo(matriz: MatrizQR) -> list[tuple[int, int]]:
    celdas = []
    for y in range(matriz.size):
        for x in range(matriz.size):
            if matriz.oscuro(x, y) and matriz.es_estilo_modulo(x, y):
                celdas.append((x, y))
    return celdas


def _barras_h(matriz: MatrizQR) -> list[tuple[int, int, int, int]]:
    """(x, y, w, h) en módulos."""
    n = matriz.size
    usado = [[False] * n for _ in range(n)]
    segs: list[tuple[int, int, int, int]] = []
    for y in range(n):
        x = 0
        while x < n:
            if matriz.oscuro(x, y) and matriz.es_estilo_modulo(x, y) and not usado[y][x]:
                x0 = x
                while x < n and matriz.oscuro(x, y) and matriz.es_estilo_modulo(x, y):
                    usado[y][x] = True
                    x += 1
                segs.append((x0, y, x - x0, 1))
            else:
                x += 1
    return segs


def _barras_v(matriz: MatrizQR) -> list[tuple[int, int, int, int]]:
    n = matriz.size
    usado = [[False] * n for _ in range(n)]
    segs: list[tuple[int, int, int, int]] = []
    for x in range(n):
        y = 0
        while y < n:
            if matriz.oscuro(x, y) and matriz.es_estilo_modulo(x, y) and not usado[y][x]:
                y0 = y
                while y < n and matriz.oscuro(x, y) and matriz.es_estilo_modulo(x, y):
                    usado[y][x] = True
                    y += 1
                segs.append((x, y0, 1, y - y0))
            else:
                y += 1
    return segs


def _modulos(matriz: MatrizQR, perfil: Perfil, ox: float, oy: float) -> list[Primitiva]:
    fill = perfil.colores.modulos
    estilo = perfil.modulo_estilo
    items: list[Primitiva] = []
    if estilo is ModuloEstilo.BARRAS_H:
        segs = _barras_h(matriz)
        for x, y, w, h in segs:
            items.append(
                _modulo_primitiva(estilo, ox + x, oy + y, w, h, fill, f"mod-{x}-{y}-{w}x{h}")
            )
        return items
    if estilo is ModuloEstilo.BARRAS_V:
        segs = _barras_v(matriz)
        for x, y, w, h in segs:
            items.append(
                _modulo_primitiva(estilo, ox + x, oy + y, w, h, fill, f"mod-{x}-{y}-{w}x{h}")
            )
        return items
    for x, y in _celdas_modulo(matriz):
        items.append(_modulo_primitiva(estilo, ox + x, oy + y, 1, 1, fill, f"mod-{x}-{y}"))
    return items


def _ojo(
    estilo: OjoEstilo,
    x: float,
    y: float,
    fill: str,
    fondo: str,
    esquina: str,
) -> list[Primitiva]:
    items: list[Primitiva] = []
    if estilo is OjoEstilo.CUADRADO:
        items.append(Rect(id=f"ojo-{esquina}-outer", x=x, y=y, w=7, h=7, fill=fill, role="ojo"))
        items.append(
            Rect(id=f"ojo-{esquina}-hueco", x=x + 1, y=y + 1, w=5, h=5, fill=fondo, role="ojo_hueco")
        )
        items.append(
            Rect(id=f"ojo-{esquina}-pupila", x=x + 2, y=y + 2, w=3, h=3, fill=fill, role="pupila")
        )
        return items
    if estilo is OjoEstilo.REDONDEADO:
        items.append(
            Rect(
                id=f"ojo-{esquina}-outer",
                x=x,
                y=y,
                w=7,
                h=7,
                fill=fill,
                role="ojo",
                rx=1.2,
                ry=1.2,
            )
        )
        items.append(
            Rect(
                id=f"ojo-{esquina}-hueco",
                x=x + 1,
                y=y + 1,
                w=5,
                h=5,
                fill=fondo,
                role="ojo_hueco",
                rx=0.8,
                ry=0.8,
            )
        )
        items.append(
            Rect(
                id=f"ojo-{esquina}-pupila",
                x=x + 2,
                y=y + 2,
                w=3,
                h=3,
                fill=fill,
                role="pupila",
                rx=0.5,
                ry=0.5,
            )
        )
        return items
    if estilo is OjoEstilo.CIRCULO:
        cx, cy = x + 3.5, y + 3.5
        items.append(Circle(id=f"ojo-{esquina}-outer", cx=cx, cy=cy, r=3.5, fill=fill, role="ojo"))
        items.append(Circle(id=f"ojo-{esquina}-hueco", cx=cx, cy=cy, r=2.5, fill=fondo, role="ojo_hueco"))
        items.append(Circle(id=f"ojo-{esquina}-pupila", cx=cx, cy=cy, r=1.5, fill=fill, role="pupila"))
        return items
    if estilo is OjoEstilo.SQUIRCLE:
        items.append(
            Path(
                id=f"ojo-{esquina}-outer",
                points=_superellipse(x + 3.5, y + 3.5, 3.5, 3.5, SQUIRCLE_N, SQUIRCLE_PASOS),
                fill=fill,
                role="ojo",
            )
        )
        items.append(
            Path(
                id=f"ojo-{esquina}-hueco",
                points=_superellipse(x + 3.5, y + 3.5, 2.5, 2.5, SQUIRCLE_N, SQUIRCLE_PASOS),
                fill=fondo,
                role="ojo_hueco",
            )
        )
        items.append(
            Path(
                id=f"ojo-{esquina}-pupila",
                points=_superellipse(x + 3.5, y + 3.5, 1.5, 1.5, SQUIRCLE_N, SQUIRCLE_PASOS),
                fill=fill,
                role="pupila",
            )
        )
        return items
    # hoja: una esquina afilada hacia afuera
    afilada = {
        "tl": (0.0, 1.4, 1.4, 1.4),
        "tr": (1.4, 0.0, 1.4, 1.4),
        "bl": (1.4, 1.4, 1.4, 0.0),
    }[esquina]
    items.append(
        Path(
            id=f"ojo-{esquina}-outer",
            points=_rounded_rect_points(x, y, 7, 7, afilada),
            fill=fill,
            role="ojo",
        )
    )
    items.append(
        Path(
            id=f"ojo-{esquina}-hueco",
            points=_rounded_rect_points(x + 1, y + 1, 5, 5, (0.9, 0.9, 0.9, 0.9)),
            fill=fondo,
            role="ojo_hueco",
        )
    )
    items.append(
        Path(
            id=f"ojo-{esquina}-pupila",
            points=_rounded_rect_points(x + 2, y + 2, 3, 3, (0.4, 0.4, 0.4, 0.4)),
            fill=fill,
            role="pupila",
        )
    )
    return items


def _ojos(matriz: MatrizQR, perfil: Perfil, ox: float, oy: float) -> list[Primitiva]:
    n = matriz.size
    pos = (("tl", 0, 0), ("tr", n - 7, 0), ("bl", 0, n - 7))
    items: list[Primitiva] = []
    for nombre, x, y in pos:
        items.extend(
            _ojo(
                perfil.ojo_estilo,
                ox + x,
                oy + y,
                perfil.colores.ojos,
                perfil.colores.fondo,
                nombre,
            )
        )
    return items


def _truncar_texto(texto: str, ancho: float, font_size: float) -> str:
    t = (texto or "").strip() or MARCO_TEXTO_DEFECTO
    t = t.upper()
    max_chars = max(1, int(ancho / max(font_size * 0.55, 0.1)))
    if len(t) > max_chars:
        return t[: max(1, max_chars - 1)] + "…"
    return t


def _marco(
    perfil: Perfil,
    inner: float,
    pad: tuple[float, float, float, float],
    total_w: float,
    total_h: float,
) -> list[Primitiva]:
    if perfil.marco_tipo is MarcoTipo.NINGUNO:
        return []
    fill = perfil.colores.marco
    fondo = perfil.colores.fondo
    g = pad[0]
    items: list[Primitiva] = []
    if perfil.marco_tipo in {MarcoTipo.PERIMETRO, MarcoTipo.ESCANEAME}:
        items.append(
            Rect(id="marco-outer", x=0, y=0, w=total_w, h=total_h, fill=fill, role="marco")
        )
        items.append(
            Rect(
                id="marco-hueco",
                x=g,
                y=g,
                w=inner,
                h=inner,
                fill=fondo,
                role="marco_hueco",
            )
        )
        if perfil.marco_tipo is MarcoTipo.ESCANEAME:
            font = TEXT_BANDA * 0.42
            cx = total_w / 2
            cy = g + inner + TEXT_BANDA * 0.62
            txt = _truncar_texto(perfil.marco_texto or "", inner, font)
            items.append(
                Text(
                    id="marco-texto",
                    x=cx,
                    y=cy,
                    text=txt,
                    fill=fondo,
                    font_size=font,
                    role="texto_marco",
                )
            )
        return items
    # banda: escuadras en las 4 esquinas, fuera de la quiet zone
    brazo = min(3.0, inner * 0.18)
    grosor = 0.55
    corners = (
        ("tl", 0.15, 0.15, 1, 1),
        ("tr", total_w - 0.15, 0.15, -1, 1),
        ("bl", 0.15, total_h - 0.15, 1, -1),
        ("br", total_w - 0.15, total_h - 0.15, -1, -1),
    )
    for nombre, x0, y0, sx, sy in corners:
        # horizontal
        hx = x0 if sx > 0 else x0 - brazo
        hy = y0 if sy > 0 else y0 - grosor
        items.append(
            Rect(
                id=f"marco-{nombre}-h",
                x=hx,
                y=hy,
                w=brazo,
                h=grosor,
                fill=fill,
                role="marco",
            )
        )
        vx = x0 if sx > 0 else x0 - grosor
        vy = y0 if sy > 0 else y0 - brazo
        items.append(
            Rect(
                id=f"marco-{nombre}-v",
                x=vx,
                y=vy,
                w=grosor,
                h=brazo,
                fill=fill,
                role="marco",
            )
        )
    return items


def _logo(perfil: Perfil, ox: float, oy: float, n: int) -> list[Primitiva]:
    ruta = logo_desde_perfil(perfil)
    if ruta is None:
        return []
    x, y, w, h = caja_logo(n)
    margen = min(
        0.35,
        max(0.0, x - FINDER_MARGEN),
        max(0.0, n - FINDER_MARGEN - (x + w)),
        max(0.0, y - FINDER_MARGEN),
        max(0.0, n - FINDER_MARGEN - (y + h)),
    )
    fondo = perfil.colores.fondo
    return [
        Rect(
            id="logo-fondo",
            x=ox + x - margen,
            y=oy + y - margen,
            w=w + 2 * margen,
            h=h + 2 * margen,
            fill=fondo,
            role="logo_fondo",
            rx=min(0.45, (w + 2 * margen) / 4),
            ry=min(0.45, (h + 2 * margen) / 4),
        ),
        Imagen(
            id="logo",
            x=ox + x,
            y=oy + y,
            w=w,
            h=h,
            ruta=str(ruta),
            role="logo",
        ),
    ]


def construir_escena(matriz: MatrizQR, perfil: Perfil) -> Escena:
    q = perfil.quiet_zone
    n = matriz.size
    inner = n + 2 * q
    pad = _pad(perfil)
    ox = pad[0] + q
    oy = pad[1] + q
    width = pad[0] + inner + pad[2]
    height = pad[1] + inner + pad[3]
    items: list[Primitiva] = []
    items.extend(_marco(perfil, inner, pad, width, height))
    items.extend(_modulos(matriz, perfil, ox, oy))
    items.extend(_ojos(matriz, perfil, ox, oy))
    items.extend(_logo(perfil, ox, oy, n))
    return Escena(
        width=width,
        height=height,
        background=perfil.colores.fondo,
        items=tuple(items),
        module_count=n,
        quiet_zone=q,
        origen_qr=(ox, oy),
        pad=pad,
    )


def escena_desde_contenido(contenido: str, perfil: Perfil) -> Escena:
    from qr_designer.config.contrast import correccion_para_matriz

    ecc = correccion_para_matriz(perfil, exportar=False)
    matriz = codificar(contenido, ecc)
    return construir_escena(matriz, perfil)


def celdas_tinta_modulo(matriz: MatrizQR) -> int:
    return len(_celdas_modulo(matriz))
