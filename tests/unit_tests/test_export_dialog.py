"""Tests de resolución de ruta/formato de exportación (sin GUI)."""

from __future__ import annotations

from pathlib import Path

import pytest

from qr_designer.export.paths import filetypes_para, resolver_export


@pytest.mark.unit
def test_sin_extension_anade_la_del_formato() -> None:
    path, fmt = resolver_export("qr", "png")
    assert path == Path("qr.png")
    assert fmt == "png"


@pytest.mark.unit
def test_extension_incorrecta_se_corrige_al_formato_elegido() -> None:
    path, fmt = resolver_export("qr.svg", "png")
    assert path == Path("qr.png")
    assert fmt == "png"


@pytest.mark.unit
def test_webp_respeta_formato_y_extension() -> None:
    path, fmt = resolver_export("qr.webp", "webp")
    assert path == Path("qr.webp")
    assert fmt == "webp"


@pytest.mark.unit
def test_svg_explicito_con_otra_extension() -> None:
    path, fmt = resolver_export("/tmp/salida.png", "svg")
    assert path == Path("/tmp/salida.svg")
    assert fmt == "svg"


@pytest.mark.unit
def test_punto_en_el_formato_se_normaliza() -> None:
    path, fmt = resolver_export("out", ".PNG")
    assert path == Path("out.png")
    assert fmt == "png"


@pytest.mark.unit
def test_formato_invalido() -> None:
    with pytest.raises(ValueError, match="[Ff]ormato"):
        resolver_export("qr", "gif")


@pytest.mark.unit
def test_filetypes_png_primero() -> None:
    tipos = filetypes_para("png")
    assert tipos[0] == ("PNG", "*.png")
    assert ("SVG", "*.svg") in tipos
    assert ("WEBP", "*.webp") in tipos


@pytest.mark.unit
def test_filetypes_svg_primero() -> None:
    tipos = filetypes_para("svg")
    assert tipos[0] == ("SVG", "*.svg")
    assert ("PNG", "*.png") in tipos
    assert ("WEBP", "*.webp") in tipos


@pytest.mark.unit
def test_filetypes_webp_primero() -> None:
    assert filetypes_para(".WEBP")[0] == ("WEBP", "*.webp")


@pytest.mark.unit
def test_filetypes_formato_invalido() -> None:
    with pytest.raises(ValueError, match="[Ff]ormato"):
        filetypes_para("gif")
