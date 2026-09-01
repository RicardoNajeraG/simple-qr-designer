"""Tests del encoder QR y clasificación de módulos."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qr_designer.config.models import Correccion
from qr_designer.core.encoder import (
    ContenidoDemasiadoLargoError,
    ContenidoVacioError,
    MatrizQR,
    TipoModulo,
    codificar,
)

MOCKUPS = Path(__file__).resolve().parents[1] / "mockups" / "matrices"


def _cargar_mockup(nombre: str) -> dict:
    return json.loads((MOCKUPS / nombre).read_text(encoding="utf-8"))


@pytest.mark.unit
def test_contenido_vacio_error() -> None:
    with pytest.raises(ContenidoVacioError):
        codificar("")
    with pytest.raises(ContenidoVacioError):
        codificar("   ")


@pytest.mark.unit
def test_contenido_demasiado_largo() -> None:
    with pytest.raises(ContenidoDemasiadoLargoError):
        codificar("x" * 4000, Correccion.H)


@pytest.mark.unit
def test_unicode_en_url() -> None:
    m = codificar("https://ejemplo.com/año")
    assert m.size >= 21
    assert m.version >= 1
    assert isinstance(m.modules[0][0], bool)


@pytest.mark.unit
def test_ecc_cambia_la_matriz() -> None:
    payload = "https://example.com"
    m_l = codificar(payload, Correccion.L)
    m_h = codificar(payload, Correccion.H)
    assert m_l.correccion is Correccion.L
    assert m_h.correccion is Correccion.H
    assert m_l.modules != m_h.modules


@pytest.mark.unit
def test_auto_usa_m_sin_mutar() -> None:
    m = codificar("HI", Correccion.AUTO)
    assert m.correccion is Correccion.M


@pytest.mark.unit
def test_payload_corto_version_1() -> None:
    m = codificar("HI", Correccion.M)
    assert m.version == 1
    assert m.size == 21


@pytest.mark.unit
def test_matriz_determinista_contra_mockup() -> None:
    esperado = _cargar_mockup("example_com_M.json")
    m = codificar(esperado["contenido"], Correccion(esperado["correccion"]))
    assert m.version == esperado["version"]
    assert m.size == esperado["size"]
    bits = [[int(c) for c in fila] for fila in m.modules]
    assert bits == esperado["modules"]


@pytest.mark.unit
def test_finders_separadores_y_timing_version_1() -> None:
    m = codificar("HI", Correccion.M)
    n = m.size
    # Finder superior izquierdo 7x7
    for y in range(7):
        for x in range(7):
            assert m.tipo(x, y) is TipoModulo.FINDER
    # Separador
    for i in range(8):
        assert m.tipo(7, i) is TipoModulo.SEPARADOR
        assert m.tipo(i, 7) is TipoModulo.SEPARADOR
    # Timing en fila/columna 6 entre finders
    assert m.tipo(8, 6) is TipoModulo.TIMING
    assert m.tipo(6, 8) is TipoModulo.TIMING
    # Esquina de datos
    assert m.tipo(n - 9, n - 9) is TipoModulo.DATO
    # Finder no se pisa con alignment en v1
    assert all(
        m.tipo(x, y) is not TipoModulo.ALIGNMENT
        for y in range(n)
        for x in range(n)
    )


@pytest.mark.unit
def test_alignment_version_2() -> None:
    m = codificar("https://example.com", Correccion.M)
    assert m.version >= 2
    # El alignment de v2 está centrado en (18, 18)
    assert m.tipo(18, 18) is TipoModulo.ALIGNMENT
    assert m.tipo(16, 16) is TipoModulo.ALIGNMENT
    assert m.tipo(20, 20) is TipoModulo.ALIGNMENT
    # No solapa el finder
    assert m.tipo(0, 0) is TipoModulo.FINDER


@pytest.mark.unit
def test_separadores_de_los_tres_ojos() -> None:
    m = codificar("HI")
    n = m.size
    assert m.tipo(n - 8, 0) is TipoModulo.SEPARADOR
    assert m.tipo(0, n - 8) is TipoModulo.SEPARADOR


@pytest.mark.unit
def test_matriz_inmutable_y_acceso() -> None:
    m = codificar("HI")
    assert isinstance(m, MatrizQR)
    with pytest.raises(Exception):
        m.version = 99  # type: ignore[misc]
    assert m.oscuro(0, 0) is True
    assert m.oscuro(7, 0) is False
