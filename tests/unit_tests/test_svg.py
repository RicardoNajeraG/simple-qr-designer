"""Tests golden y estructurales del renderizador SVG."""

from __future__ import annotations

import os
import unicodedata
from pathlib import Path

import pytest

from qr_designer.config.models import MarcoTipo, ModuloEstilo, OjoEstilo, Perfil
from qr_designer.config.presets import PRESETS
from qr_designer.core.encoder import codificar
from qr_designer.render.svg import escena_a_svg
from qr_designer.scene.builders import construir_escena

GOLDEN = Path(__file__).resolve().parents[1] / "mockups" / "golden_svg"
PAYLOAD = "https://example.com"
def _slug(nombre: str) -> str:
    nfkd = unicodedata.normalize("NFKD", nombre)
    plano = "".join(c for c in nfkd if not unicodedata.combining(c))
    return plano.lower().replace(" ", "_")


PRESUPUESTO_SVG_CLASICO = 20_000  # bytes; QR mediano, estilo cuadrado


def _svg_para(nombre: str, perfil: Perfil) -> str:
    escena = construir_escena(codificar(PAYLOAD), perfil)
    return escena_a_svg(escena)


def _assert_golden(nombre: str, svg: str) -> None:
    path = GOLDEN / f"{nombre}.svg"
    if os.environ.get("UPDATE_GOLDEN"):
        path.write_text(svg, encoding="utf-8")
    assert path.is_file(), f"Falta golden {path}; ejecuta UPDATE_GOLDEN=1"
    assert svg == path.read_text(encoding="utf-8")


@pytest.mark.unit
def test_svg_tiene_viewbox_y_va_minificado() -> None:
    svg = _svg_para("tmp", Perfil(nombre="c"))
    assert 'viewBox="0 0 ' in svg
    assert svg.startswith("<svg ")
    assert svg.endswith("</svg>")
    assert "\n" not in svg
    assert "  " not in svg
    assert "<?xml" not in svg
    assert 'rx="0"' not in svg


@pytest.mark.unit
def test_svg_coordenadas_redondeadas() -> None:
    svg = _svg_para("tmp", Perfil(nombre="c", modulo_estilo=ModuloEstilo.PUNTOS))
    import re

    for num in re.findall(r"[-+]?\d+\.\d+", svg):
        decimals = len(num.split(".", 1)[1])
        assert decimals <= 3


@pytest.mark.unit
def test_svg_determinista() -> None:
    p = Perfil(nombre="c", modulo_estilo=ModuloEstilo.GOTA, ojo_estilo=OjoEstilo.HOJA)
    a = _svg_para("a", p)
    b = _svg_para("b", p)
    assert a == b


@pytest.mark.unit
@pytest.mark.parametrize("estilo", list(ModuloEstilo))
def test_golden_por_estilo_modulo(estilo: ModuloEstilo) -> None:
    svg = _svg_para(estilo.value, Perfil(nombre=estilo.value, modulo_estilo=estilo))
    _assert_golden(f"modulo_{estilo.value}", svg)


@pytest.mark.unit
@pytest.mark.parametrize("estilo", list(OjoEstilo))
def test_golden_por_estilo_ojo(estilo: OjoEstilo) -> None:
    svg = _svg_para(estilo.value, Perfil(nombre=estilo.value, ojo_estilo=estilo))
    _assert_golden(f"ojo_{estilo.value}", svg)


@pytest.mark.unit
@pytest.mark.parametrize("marco", list(MarcoTipo))
def test_golden_por_marco(marco: MarcoTipo) -> None:
    svg = _svg_para(
        marco.value,
        Perfil(nombre=marco.value, marco_tipo=marco, marco_texto="QR"),
    )
    _assert_golden(f"marco_{marco.value}", svg)


@pytest.mark.unit
@pytest.mark.parametrize("perfil", PRESETS, ids=lambda p: p.nombre)
def test_golden_por_preset(perfil: Perfil) -> None:
    svg = _svg_para(perfil.nombre, perfil)
    _assert_golden(f"preset_{_slug(perfil.nombre)}", svg)


@pytest.mark.unit
def test_presupuesto_svg_clasico() -> None:
    svg = _svg_para("clasico", Perfil(nombre="Clásico"))
    assert len(svg.encode("utf-8")) < PRESUPUESTO_SVG_CLASICO
