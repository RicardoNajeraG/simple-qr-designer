"""Presupuestos de tiempo (umbrales holgados para CI)."""

from __future__ import annotations

import time

import pytest

from qr_designer.config.presets import PRESET_PUNTOS, PRESET_REDONDEADO, preset_clasico
from qr_designer.core.encoder import codificar
from qr_designer.render.svg import escena_a_svg
from qr_designer.scene.builders import construir_escena

LIMITE_MS = 200  # 50 ms de meta local; holgado en CI
PAYLOAD = "https://example.com"


@pytest.mark.integration
def test_matriz_mas_svg_bajo_presupuesto() -> None:
    perfil = preset_clasico()
    t0 = time.perf_counter()
    matriz = codificar(PAYLOAD, perfil.correccion)
    svg = escena_a_svg(construir_escena(matriz, perfil))
    ms = (time.perf_counter() - t0) * 1000
    assert svg.startswith("<svg")
    assert ms < LIMITE_MS, f"{ms:.1f} ms ≥ {LIMITE_MS}"


@pytest.mark.integration
def test_aplicar_perfil_rebuild_bajo_presupuesto() -> None:
    matriz = codificar(PAYLOAD)
    construir_escena(matriz, preset_clasico())  # calienta
    t0 = time.perf_counter()
    escena = construir_escena(matriz, PRESET_PUNTOS)
    escena_a_svg(escena)
    ms = (time.perf_counter() - t0) * 1000
    assert escena.ids()
    assert ms < LIMITE_MS, f"{ms:.1f} ms ≥ {LIMITE_MS}"
    t0 = time.perf_counter()
    construir_escena(matriz, PRESET_REDONDEADO)
    ms = (time.perf_counter() - t0) * 1000
    assert ms < LIMITE_MS, f"{ms:.1f} ms ≥ {LIMITE_MS}"
