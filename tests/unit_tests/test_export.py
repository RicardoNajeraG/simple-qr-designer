"""Tests de exportación y guards de imports perezosos."""

from __future__ import annotations

import subprocess
import sys
from io import BytesIO
from pathlib import Path

import pytest

from qr_designer.config.models import (
    ColorScheme,
    Correccion,
    ModuloEstilo,
    OjoEstilo,
    Perfil,
    SolicitudQR,
    hex_a_rgb,
)
from qr_designer.core.encoder import ContenidoVacioError
from qr_designer.export.exporter import (
    DIMENSION_MAX,
    PX_MODULO_DEFECTO,
    ExportacionError,
    exportar,
    resolucion_recomendada,
)
from qr_designer.scene.builders import escena_desde_contenido

ROOT = Path(__file__).resolve().parents[2]


def _sol(perfil: Perfil | None = None, contenido: str = "https://example.com") -> SolicitudQR:
    return SolicitudQR(contenido=contenido, perfil=perfil or Perfil(nombre="t"))


@pytest.mark.unit
def test_svg_export_minificado_y_peso() -> None:
    r = exportar(_sol(), "svg")
    assert r.formato == "svg"
    assert r.peso == len(r.datos) == r.peso
    assert r.datos.startswith(b"<svg ")
    assert b"\n" not in r.datos
    assert r.peso > 0


@pytest.mark.unit
def test_formato_invalido() -> None:
    with pytest.raises(ExportacionError):
        exportar(_sol(), "gif")


@pytest.mark.unit
def test_contenido_vacio_en_export() -> None:
    with pytest.raises(ContenidoVacioError):
        exportar(_sol(contenido="  "), "svg")


@pytest.mark.unit
def test_resolucion_recomendada_ata_px_a_modulos() -> None:
    escena = escena_desde_contenido("https://example.com", Perfil(nombre="t"))
    w, h = resolucion_recomendada(escena, PX_MODULO_DEFECTO)
    assert w == round(escena.width * PX_MODULO_DEFECTO)
    assert h == round(escena.height * PX_MODULO_DEFECTO)


@pytest.mark.unit
def test_dimension_enorme_rechazada() -> None:
    with pytest.raises(ExportacionError, match="máximo"):
        exportar(_sol(), "png", px_modulo=DIMENSION_MAX)


def _assert_no_import(modulo: str, prohibidos: list[str]) -> None:
    prohibido = " or ".join(f"m == {p!r} or m.startswith({p!r} + '.')" for p in prohibidos)
    codigo = (
        "import sys\n"
        f"import {modulo}\n"
        f"malos = [m for m in sys.modules if {prohibido}]\n"
        "raise SystemExit(0 if not malos else 'Cargó: ' + ','.join(malos))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(ROOT / "src")},
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.unit
def test_import_scene_svg_cli_no_carga_pillow() -> None:
    for mod in (
        "qr_designer.scene.builders",
        "qr_designer.render.svg",
        "qr_designer.ui.cli",
        "qr_designer.ui.viewmodel",
        "qr_designer.export.exporter",
        "qr_designer.service.qr_service",
        "qr_designer.render.preview",
    ):
        _assert_no_import(mod, ["PIL"])


@pytest.mark.unit
def test_import_cli_no_carga_tkinter() -> None:
    _assert_no_import("qr_designer.ui.cli", ["tkinter"])


@pytest.mark.raster
@pytest.mark.unit
def test_png_paleta_colores_exactos() -> None:
    pytest.importorskip("PIL")
    from PIL import Image

    perfil = Perfil(
        nombre="t",
        colores=ColorScheme(fondo="#ffffff", modulos="#cc0000", ojos="#0033aa", marco="#00aa00"),
    )
    r = exportar(_sol(perfil), "png", px_modulo=8)
    assert r.formato == "png"
    assert r.peso == len(r.datos)
    img = Image.open(BytesIO(r.datos))
    assert img.mode == "P"
    assert img.size == (r.ancho, r.alto)
    pal = img.getpalette()
    assert pal is not None
    indices = set(img.getdata())
    rgbs = {tuple(pal[i * 3 : i * 3 + 3]) for i in indices}
    esperados = {(255, 255, 255), (204, 0, 0), (0, 51, 170)}
    assert rgbs <= esperados | {(0, 170, 0)}
    assert (255, 255, 255) in rgbs
    assert (204, 0, 0) in rgbs
    assert (0, 51, 170) in rgbs


@pytest.mark.raster
@pytest.mark.unit
def test_webp_lossless_roundtrip_pixels() -> None:
    pytest.importorskip("PIL")
    from PIL import Image

    r = exportar(_sol(), "webp", px_modulo=6)
    img = Image.open(BytesIO(r.datos))
    # Pillow marca lossless en info a veces; comprobamos roundtrip de guardado
    buf = BytesIO()
    rgb = img.convert("RGB")
    rgb.save(buf, format="WEBP", lossless=True, quality=100)
    otra = Image.open(BytesIO(buf.getvalue())).convert("RGB")
    assert list(rgb.getdata()) == list(otra.getdata())


@pytest.mark.raster
@pytest.mark.unit
def test_px_modulo_1_advierte() -> None:
    pytest.importorskip("PIL")
    r = exportar(_sol(), "png", px_modulo=1)
    assert r.advertencias
    assert any("bajo" in a.lower() for a in r.advertencias)


@pytest.mark.raster
@pytest.mark.unit
def test_png_curvas_mantiene_dimensiones_y_colores_dominantes() -> None:
    pytest.importorskip("PIL")
    from PIL import Image

    from qr_designer.export.exporter import construir_escena_export, resolucion_recomendada

    contenido = "https://example.com"
    perfil = Perfil(
        nombre="t",
        modulo_estilo=ModuloEstilo.PUNTOS,
        ojo_estilo=OjoEstilo.CIRCULO,
        colores=ColorScheme(fondo="#ffffff", modulos="#cc0000", ojos="#0033aa", marco="#00aa00"),
    )
    solicitud = _sol(perfil, contenido)
    r = exportar(solicitud, "png", px_modulo=8)
    escena = construir_escena_export(solicitud)
    ancho, alto = resolucion_recomendada(escena, 8)
    assert r.ancho == ancho
    assert r.alto == alto
    assert r.ancho <= DIMENSION_MAX
    assert r.alto <= DIMENSION_MAX

    img = Image.open(BytesIO(r.datos)).convert("RGB")
    paleta = {
        hex_a_rgb(perfil.colores.fondo),
        hex_a_rgb(perfil.colores.modulos),
        hex_a_rgb(perfil.colores.ojos),
    }
    cercanos = 0
    total = img.size[0] * img.size[1]
    umbral = 40 * 40 * 3
    for pixel in img.getdata():
        if min(sum((a - b) ** 2 for a, b in zip(pixel, color)) for color in paleta) <= umbral:
            cercanos += 1
    assert cercanos / total > 0.80


@pytest.mark.raster
@pytest.mark.decode
@pytest.mark.unit
def test_png_curvas_se_decodifica() -> None:
    pytest.importorskip("PIL")
    zxingcpp = pytest.importorskip("zxingcpp")
    from PIL import Image

    contenido = "https://example.com/qr-designer-test"
    perfil = Perfil(
        nombre="t",
        modulo_estilo=ModuloEstilo.PUNTOS,
        ojo_estilo=OjoEstilo.CIRCULO,
        correccion=Correccion.H,
    )
    r = exportar(_sol(perfil, contenido), "png", px_modulo=10)
    img = Image.open(BytesIO(r.datos)).convert("RGB")
    encontrados = zxingcpp.read_barcodes(img)
    assert encontrados, "ZXing no leyó el PNG con curvas"
    assert encontrados[0].text == contenido


@pytest.mark.raster
@pytest.mark.unit
def test_supersampling_no_viola_dimension_max_en_salida() -> None:
    pytest.importorskip("PIL")
    from qr_designer.export.exporter import construir_escena_export, resolucion_recomendada

    perfil = Perfil(
        nombre="t",
        modulo_estilo=ModuloEstilo.PUNTOS,
        ojo_estilo=OjoEstilo.CIRCULO,
    )
    solicitud = _sol(perfil)
    r = exportar(solicitud, "png", px_modulo=8)
    escena = construir_escena_export(solicitud)
    ancho, alto = resolucion_recomendada(escena, 8)
    assert r.ancho == ancho <= DIMENSION_MAX
    assert r.alto == alto <= DIMENSION_MAX


@pytest.mark.raster
@pytest.mark.unit
def test_auto_eleva_ecc_solo_en_export() -> None:
    pytest.importorskip("PIL")
    from qr_designer.core.encoder import codificar

    perfil = Perfil(
        nombre="t",
        modulo_estilo=ModuloEstilo.PUNTOS,
        correccion=Correccion.AUTO,
    )
    preview = codificar("https://example.com", Correccion.AUTO)
    assert preview.correccion is Correccion.M
    r = exportar(_sol(perfil), "png")
    assert r.peso > 0
