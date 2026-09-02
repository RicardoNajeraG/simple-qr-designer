"""Rasterizador SVG: color heredado, CSS y suavizado."""

from __future__ import annotations

import pytest


@pytest.mark.raster
@pytest.mark.unit
def test_svg_simple_hereda_fill_del_grupo() -> None:
    pytest.importorskip("PIL")
    from qr_designer.export.svg_raster import _svg_simple_rgba

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<g fill="#00aa44"><rect width="10" height="10"/></g>'
        "</svg>"
    )
    img = _svg_simple_rgba(svg, 20, 20)
    r, g, b, a = img.getpixel((10, 10))
    assert a > 200
    assert r < 40 and g > 140 and b < 80


@pytest.mark.raster
@pytest.mark.unit
def test_svg_simple_respeta_css_y_rgb() -> None:
    pytest.importorskip("PIL")
    from qr_designer.export.svg_raster import _svg_simple_rgba

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        "<style>.marca{fill:rgb(0, 128, 255)}</style>"
        '<rect class="marca" width="10" height="10"/>'
        "</svg>"
    )
    img = _svg_simple_rgba(svg, 16, 16)
    r, g, b, a = img.getpixel((8, 8))
    assert a > 200
    assert r < 40 and 100 < g < 160 and b > 200


@pytest.mark.raster
@pytest.mark.unit
def test_svg_a_rgba_suaviza_borde(tmp_path) -> None:
    pytest.importorskip("PIL")
    from qr_designer.export.svg_raster import svg_a_rgba

    ruta = tmp_path / "circulo.svg"
    ruta.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<circle cx="50" cy="50" r="40" fill="#ff0000"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )
    img = svg_a_rgba(ruta, 32, 32).convert("RGBA")
    colores = img.getcolors(maxcolors=8192)
    assert colores is None or len(colores) > 8


@pytest.mark.raster
@pytest.mark.unit
def test_svg_simple_aplica_translate() -> None:
    pytest.importorskip("PIL")
    from qr_designer.export.svg_raster import _svg_simple_rgba

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<g transform="translate(5 0)">'
        '<rect width="5" height="10" fill="#ff0000"/>'
        "</g>"
        "</svg>"
    )
    img = _svg_simple_rgba(svg, 20, 20)
    izq = img.getpixel((2, 10))
    der = img.getpixel((17, 10))
    assert izq[3] < 40
    assert der[0] > 200 and der[3] > 200


@pytest.mark.raster
@pytest.mark.unit
def test_svg_simple_resuelve_use_y_stroke() -> None:
    pytest.importorskip("PIL")
    from qr_designer.export.svg_raster import _svg_simple_rgba

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<defs><rect id="r" width="10" height="10" fill="#00aa44"/></defs>'
        '<use href="#r"/>'
        "</svg>"
    )
    img = _svg_simple_rgba(svg, 16, 16)
    r, g, b, a = img.getpixel((8, 8))
    assert a > 200 and g > 140 and r < 40

    trazo = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" fill="none"'
        ' stroke="#0000ff" stroke-width="2">'
        '<rect x="1" y="1" width="8" height="8"/>'
        "</svg>"
    )
    img2 = _svg_simple_rgba(trazo, 40, 40)
    borde = img2.getpixel((4, 20))
    centro = img2.getpixel((20, 20))
    assert borde[2] > 150 and borde[3] > 80
    assert centro[3] < 40
