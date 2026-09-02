"""Geometría del hueco de logotipo: caja segura y contain."""

from __future__ import annotations

import pytest

from qr_designer.scene.logo import (
    FINDER_MARGEN,
    LOGO_FRAC,
    ajustar_contain,
    caja_logo,
    dimensiones_svg,
    svg_en_caja,
)


def _solapa(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


@pytest.mark.unit
@pytest.mark.parametrize("n", [21, 25, 29, 33, 45])
def test_caja_logo_centrada_dentro_de_zona_segura(n: int) -> None:
    x, y, w, h = caja_logo(n)
    assert w == pytest.approx(h)
    assert x == pytest.approx(y)
    assert x + w / 2 == pytest.approx(n / 2)
    assert x >= FINDER_MARGEN - 1e-9
    assert y >= FINDER_MARGEN - 1e-9
    assert x + w <= n - FINDER_MARGEN + 1e-9
    assert y + h <= n - FINDER_MARGEN + 1e-9
    usable = n - 2 * FINDER_MARGEN
    assert w <= usable + 1e-9
    if n * LOGO_FRAC <= usable - 2:
        assert w == pytest.approx(n * LOGO_FRAC)


@pytest.mark.unit
def test_caja_logo_independiente_del_tamano_de_imagen() -> None:
    a = caja_logo(25)
    b = caja_logo(25)
    assert a == b
    c64 = ajustar_contain(a, 64, 64)
    c2k = ajustar_contain(a, 2000, 500)
    assert a == caja_logo(25)
    assert c64[2] == pytest.approx(c64[3])
    assert c2k[2] > c2k[3]
    assert c2k[2] == pytest.approx(a[2])


@pytest.mark.unit
def test_contain_apaisada_deja_bandas_y_cuadrada_llena() -> None:
    caja = caja_logo(29)
    _, _, cw, ch = caja
    ax, ay, aw, ah = ajustar_contain(caja, 200, 80)
    assert aw == pytest.approx(cw)
    assert ah < ch
    assert ax == pytest.approx(caja[0])
    assert ay > caja[1]
    qx, qy, qw, qh = ajustar_contain(caja, 80, 80)
    assert qw == pytest.approx(cw)
    assert qh == pytest.approx(ch)
    assert qx == pytest.approx(caja[0])
    assert qy == pytest.approx(caja[1])


@pytest.mark.unit
@pytest.mark.parametrize("n", [21, 25, 29, 41])
def test_caja_logo_no_solapa_finders(n: int) -> None:
    logo = caja_logo(n)
    finders = ((0.0, 0.0, 7.0, 7.0), (n - 7.0, 0.0, 7.0, 7.0), (0.0, n - 7.0, 7.0, 7.0))
    for f in finders:
        assert not _solapa(logo, f)


@pytest.mark.unit
def test_dimensiones_svg_viewbox_y_medidas() -> None:
    assert dimensiones_svg(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 40"/>'
    ) == (80.0, 40.0)
    assert dimensiones_svg(
        '<svg xmlns="http://www.w3.org/2000/svg" width="10px" height="20"/>'
    ) == (10.0, 20.0)
    assert dimensiones_svg(
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 10 50 25"/>'
    ) == (50.0, 25.0)


@pytest.mark.unit
def test_svg_en_caja_conserva_color_y_anida_vector() -> None:
    crudo = (
        '<?xml version="1.0"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" width="24px" height="24px" viewBox="0 0 24 24">'
        '<style>.marca{fill:#00aa44}</style>'
        '<g fill="#112233"><path class="marca" d="M0 0h24v24H0z"/></g>'
        "</svg>"
    )
    out = svg_en_caja(crudo, 1.5, 2.25, 6, 6)
    assert "<?xml" not in out
    assert "fill:#00aa44" in out
    assert 'fill="#112233"' in out
    assert ".marca{fill:#00aa44}" in out
    assert out.strip().startswith("<g")
    assert "translate(" in out
    assert "scale(" in out
    assert "data:image" not in out
    assert "<svg" not in out.lower()
