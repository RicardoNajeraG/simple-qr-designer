"""Conversión HSV/RGB y geometría de la rueda. Sin tkinter."""

from __future__ import annotations

import colorsys
import math

from qr_designer.config.models import hex_a_rgb


def clamp_byte(n: float | int) -> int:
    return max(0, min(255, int(round(float(n)))))


def rgb_a_hsv(r: int, g: int, b: int) -> tuple[float, float, float]:
    return colorsys.rgb_to_hsv(
        clamp_byte(r) / 255.0,
        clamp_byte(g) / 255.0,
        clamp_byte(b) / 255.0,
    )


def hsv_a_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    rr, gg, bb = colorsys.hsv_to_rgb(
        h % 1.0,
        max(0.0, min(1.0, s)),
        max(0.0, min(1.0, v)),
    )
    return clamp_byte(rr * 255), clamp_byte(gg * 255), clamp_byte(bb * 255)


def rgba_a_hex(r: int, g: int, b: int, a: int = 255) -> str:
    del a
    return f"#{clamp_byte(r):02x}{clamp_byte(g):02x}{clamp_byte(b):02x}"


def hex_a_rgba(color: str) -> tuple[int, int, int, int]:
    r, g, b = hex_a_rgb(color)
    return r, g, b, 255


def hsv_en_rueda(x: float, y: float, radio: float) -> tuple[float, float] | None:
    """Offsets desde el centro (y hacia abajo). Devuelve (h, s) en [0, 1] o None."""
    dist = math.hypot(x, y)
    if radio <= 0 or dist > radio + 1e-9:
        return None
    s = 0.0 if dist == 0 else min(1.0, dist / radio)
    h = (math.atan2(-y, x) / (2 * math.pi)) % 1.0
    return h, s
