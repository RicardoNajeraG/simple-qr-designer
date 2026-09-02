"""Tests de contraste, inversión y fill-ratio."""

from __future__ import annotations

import pytest

from qr_designer.config.contrast import (
    UMBRAL_CONTRASTE,
    UMBRAL_FILL,
    ecc_recomendada_por_estilo,
    evaluar_contraste,
    fill_ratio_estilo,
    ratio_contraste,
    luminancia_relativa,
)
from qr_designer.config.models import (
    ColorScheme,
    MarcoTipo,
    ModuloEstilo,
    Perfil,
)


@pytest.mark.unit
def test_negro_sobre_blanco_es_21_a_1() -> None:
    ratio = ratio_contraste("#000000", "#ffffff")
    assert ratio == pytest.approx(21.0, rel=1e-3)


@pytest.mark.unit
def test_colores_iguales_ratio_1() -> None:
    assert ratio_contraste("#abcabc", "#ABCABC") == pytest.approx(1.0)
    assert ratio_contraste("#000000", "#000000") == pytest.approx(1.0)


@pytest.mark.unit
def test_hex_mayusculas_minusculas_equivalentes() -> None:
    assert luminancia_relativa("#AaBbCc") == luminancia_relativa("#aabbcc")
    assert ratio_contraste("#FF0000", "#00ff00") == ratio_contraste("#ff0000", "#00FF00")


@pytest.mark.unit
def test_par_en_limite_3_a_1() -> None:
    # Gris #949494 sobre blanco ≈ 3.05:1; #959595 ≈ 2.99
    alto = ratio_contraste("#767676", "#ffffff")
    assert alto >= UMBRAL_CONTRASTE
    bajo = ratio_contraste("#959595", "#ffffff")
    assert bajo < UMBRAL_CONTRASTE


@pytest.mark.unit
def test_fill_ratio_puntos_y_gota_bajo_umbral() -> None:
    assert fill_ratio_estilo(ModuloEstilo.PUNTOS) < UMBRAL_FILL
    assert fill_ratio_estilo(ModuloEstilo.GOTA) < UMBRAL_FILL
    assert fill_ratio_estilo(ModuloEstilo.CUADRADO) >= UMBRAL_FILL
    assert fill_ratio_estilo(ModuloEstilo.BARRAS_H) >= UMBRAL_FILL - 1e-9


@pytest.mark.unit
def test_advertencia_qr_invertido() -> None:
    perfil = Perfil(
        nombre="inv",
        colores=ColorScheme(fondo="#000000", modulos="#ffffff"),
    )
    ev = evaluar_contraste(perfil)
    assert ev.invertido
    assert any("invert" in a.lower() or "claro" in a.lower() for a in ev.advertencias)
    assert not ev.ok


@pytest.mark.unit
def test_advertencia_baja_ocupacion_puntos() -> None:
    perfil = Perfil(nombre="p", modulo_estilo=ModuloEstilo.PUNTOS)
    ev = evaluar_contraste(perfil)
    assert ev.baja_ocupacion
    assert ev.fill_ratio < UMBRAL_FILL
    assert any("ocupación" in a.lower() or "ocupacion" in a.lower() for a in ev.advertencias)


@pytest.mark.unit
def test_clasico_sin_advertencias() -> None:
    perfil = Perfil(nombre="Clásico")
    ev = evaluar_contraste(perfil)
    assert ev.ok
    assert not ev.invertido
    assert not ev.bajo_contraste
    assert not ev.baja_ocupacion
    assert ev.ratio_modulos == pytest.approx(21.0, rel=1e-3)


@pytest.mark.unit
def test_bajo_contraste_modulos_ojos_y_marco() -> None:
    perfil = Perfil(
        nombre="bajo",
        marco_tipo=MarcoTipo.PERIMETRO,
        colores=ColorScheme(
            fondo="#ffffff",
            modulos="#959595",
            ojos="#aaaaaa",
            marco="#cccccc",
        ),
    )
    ev = evaluar_contraste(perfil)
    assert ev.bajo_contraste
    assert ev.ratio_modulos < UMBRAL_CONTRASTE
    assert ev.ratio_ojos < UMBRAL_CONTRASTE
    assert ev.ratio_marco < UMBRAL_CONTRASTE
    assert len(ev.advertencias) >= 3


@pytest.mark.unit
def test_alfa_implicito_no_cambia_rgb() -> None:
    assert ratio_contraste("#000000ff", "#ffffffff") == pytest.approx(21.0, rel=1e-3)


@pytest.mark.unit
def test_logo_recomienda_ecc_h() -> None:
    perfil = Perfil(nombre="l", logo_path="/tmp/logo.png")
    assert ecc_recomendada_por_estilo(perfil) == "H"
    ev = evaluar_contraste(perfil)
    assert any("logotipo" in a.lower() or "logo" in a.lower() for a in ev.advertencias)


@pytest.mark.unit
def test_logo_id_tambien_recomienda_ecc_h(monkeypatch) -> None:
    from qr_designer.logos import LogoDesconocido

    def _resolver(ident: str, raiz=None):
        raise LogoDesconocido(ident)

    monkeypatch.setattr("qr_designer.logos.resolver_logo", _resolver)
    perfil = Perfil(nombre="l", logo_id="wifi")
    assert ecc_recomendada_por_estilo(perfil) == "H"
    ev = evaluar_contraste(perfil)
    assert any("logotipo" in a.lower() or "logo" in a.lower() for a in ev.advertencias)
    assert any("no se encontró" in a.lower() or "no se encontro" in a.lower() for a in ev.advertencias)
