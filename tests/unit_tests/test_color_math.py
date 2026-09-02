"""Conversión HSV/RGB y rueda: sin tkinter."""

from __future__ import annotations

import pytest

from qr_designer.config.models import hex_a_rgb
from qr_designer.ui.color_math import (
    clamp_byte,
    hsv_a_rgb,
    hsv_en_rueda,
    hex_a_rgba,
    rgb_a_hsv,
    rgba_a_hex,
)


def _assert_roundtrip(hex_color: str) -> None:
    r, g, b = hex_a_rgb(hex_color)
    h, s, v = rgb_a_hsv(r, g, b)
    r2, g2, b2 = hsv_a_rgb(h, s, v)
    assert abs(r - r2) <= 1
    assert abs(g - g2) <= 1
    assert abs(b - b2) <= 1


@pytest.mark.unit
def test_roundtrip_hsv_colores_conocidos() -> None:
    for color in ("#000000", "#ffffff", "#0b3d91", "#e0708a"):
        _assert_roundtrip(color)


@pytest.mark.unit
def test_rgba_a_hex_ignora_alfa() -> None:
    assert rgba_a_hex(11, 61, 145, 0) == "#0b3d91"
    assert rgba_a_hex(11, 61, 145, 255) == "#0b3d91"
    assert hex_a_rgba("#0b3d91") == (11, 61, 145, 255)


@pytest.mark.unit
def test_clamp_byte() -> None:
    assert clamp_byte(-1) == 0
    assert clamp_byte(300) == 255
    assert clamp_byte(14.4) == 14


@pytest.mark.unit
def test_hsv_en_rueda_centro_y_fuera() -> None:
    h, s = hsv_en_rueda(0, 0, 70)
    assert s == pytest.approx(0.0)
    assert 0.0 <= h < 1.0
    assert hsv_en_rueda(80, 0, 70) is None
    assert hsv_en_rueda(70.1, 0, 70) is None
    rojo = hsv_en_rueda(35, 0, 70)
    assert rojo is not None
    h_rojo, s_rojo = rojo
    assert s_rojo == pytest.approx(0.5, abs=0.02)
    assert h_rojo == pytest.approx(0.0, abs=0.02)
