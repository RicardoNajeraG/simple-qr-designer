"""Preview: píxeles enteros por módulo y paridad con el raster de export."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from qr_designer.config.models import Perfil
from qr_designer.render.preview import px_para_preview
from qr_designer.scene.builders import escena_desde_contenido
from qr_designer.scene.primitives import Escena

ROOT = Path(__file__).resolve().parents[2]
MAX_LADO = 320.0


def _escena_simple(ancho: float, alto: float) -> Escena:
    return Escena(
        width=ancho,
        height=alto,
        background="#ffffff",
        items=(),
        module_count=21,
        quiet_zone=4,
        origen_qr=(0.0, 0.0),
        pad=(0.0, 0.0, 0.0, 0.0),
    )


@pytest.mark.unit
def test_px_para_preview_maximiza_enteros() -> None:
    escena = _escena_simple(29.0, 29.0)
    px = px_para_preview(escena, MAX_LADO)
    assert px == 11
    assert escena.width * px <= MAX_LADO
    assert escena.width * (px + 1) > MAX_LADO


@pytest.mark.unit
def test_px_para_preview_minimo_uno() -> None:
    escena = _escena_simple(400.0, 400.0)
    assert px_para_preview(escena, 50.0) == 1


@pytest.mark.unit
def test_px_para_preview_exacto() -> None:
    escena = _escena_simple(10.0, 10.0)
    assert px_para_preview(escena, 10.0) == 1
    assert px_para_preview(escena, 20.0) == 2


@pytest.mark.unit
def test_px_para_preview_usa_el_lado_mayor() -> None:
    escena = _escena_simple(20.0, 40.0)
    assert px_para_preview(escena, 80.0) == 2


@pytest.mark.raster
@pytest.mark.unit
def test_preview_png_paridad_con_rasterizar() -> None:
    pytest.importorskip("PIL")
    from qr_designer.export.exporter import resolucion_recomendada
    from qr_designer.export.raster import rasterizar
    from qr_designer.render.preview import preview_png

    contenido = "https://example.com"
    perfil = Perfil(nombre="t")
    escena = escena_desde_contenido(contenido, perfil)
    px = px_para_preview(escena, MAX_LADO)
    ancho, alto = resolucion_recomendada(escena, px)
    assert preview_png(contenido, perfil, MAX_LADO) == rasterizar(escena, ancho, alto, "png")


@pytest.mark.unit
def test_import_preview_no_carga_pillow() -> None:
    codigo = (
        "import sys\n"
        "import qr_designer.render.preview\n"
        "malos = [m for m in sys.modules if m == 'PIL' or m.startswith('PIL.')]\n"
        "raise SystemExit(0 if not malos else 'Cargó: ' + ','.join(malos))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(ROOT / "src")},
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
