"""Tests de Perfil, ColorScheme, enums y SolicitudQR."""

from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError

from qr_designer.config.models import (
    ColorInvalidoError,
    ColorScheme,
    Correccion,
    MarcoTipo,
    ModuloEstilo,
    OjoEstilo,
    Perfil,
    SolicitudQR,
    parse_color,
)


@pytest.mark.unit
def test_perfil_es_frozen() -> None:
    perfil = Perfil(nombre="x")
    with pytest.raises(FrozenInstanceError):
        perfil.nombre = "otro"  # type: ignore[misc]


@pytest.mark.unit
def test_perfil_defaults_clasicos() -> None:
    perfil = Perfil(nombre="Clásico")
    assert perfil.modulo_estilo is ModuloEstilo.CUADRADO
    assert perfil.ojo_estilo is OjoEstilo.CUADRADO
    assert perfil.marco_tipo is MarcoTipo.NINGUNO
    assert perfil.marco_texto is None
    assert perfil.correccion is Correccion.M
    assert perfil.quiet_zone == 4
    assert perfil.colores.fondo == "#ffffff"
    assert perfil.colores.modulos == "#000000"
    assert perfil.colores.ojos == "#000000"
    assert perfil.colores.marco == "#000000"


@pytest.mark.unit
def test_quiet_zone_minimo_es_4() -> None:
    with pytest.raises(ValueError, match="quiet zone"):
        Perfil(nombre="x", quiet_zone=3)


@pytest.mark.unit
@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("#000", "#000000"),
        ("#FFF", "#ffffff"),
        ("#AbCdEf", "#abcdef"),
        ("ffffff", "#ffffff"),
        ("white", "#ffffff"),
        ("WHITE", "#ffffff"),
        ("black", "#000000"),
        ("#11223344", "#112233"),
        ("navy", "#000080"),
    ],
)
def test_parse_color_acepta_hex_y_nombres(texto: str, esperado: str) -> None:
    assert parse_color(texto) == esperado


@pytest.mark.unit
@pytest.mark.parametrize("texto", ["", "no-color", "#gg0000", "#12", "12345", "#"])
def test_parse_color_rechaza_basura(texto: str) -> None:
    with pytest.raises(ColorInvalidoError):
        parse_color(texto)


@pytest.mark.unit
def test_colorscheme_normaliza_en_construccion() -> None:
    cs = ColorScheme(fondo="WHITE", modulos="#000", ojos="#F00", marco="navy")
    assert cs.fondo == "#ffffff"
    assert cs.modulos == "#000000"
    assert cs.ojos == "#ff0000"
    assert cs.marco == "#000080"


@pytest.mark.unit
def test_colorscheme_rechaza_color_invalido() -> None:
    with pytest.raises(ColorInvalidoError):
        ColorScheme(fondo="xyz")


@pytest.mark.unit
def test_enum_modulo_rechaza_valor_invalido() -> None:
    with pytest.raises(ValueError):
        ModuloEstilo("estrellas")


@pytest.mark.unit
def test_solicitud_agrupa_contenido_y_perfil_sin_url_en_perfil() -> None:
    perfil = Perfil(nombre="p")
    sol = SolicitudQR(contenido="https://example.com", perfil=perfil)
    assert sol.contenido == "https://example.com"
    assert not hasattr(perfil, "url")
    assert "url" not in perfil.to_dict()
    assert "contenido" not in perfil.to_dict()


@pytest.mark.unit
def test_serializacion_dict_redonda_e_ignora_url_colada() -> None:
    original = Perfil(
        nombre="Marca",
        modulo_estilo=ModuloEstilo.PUNTOS,
        ojo_estilo=OjoEstilo.CIRCULO,
        marco_tipo=MarcoTipo.ESCANEAME,
        marco_texto="SCAN",
        correccion=Correccion.H,
        colores=ColorScheme(fondo="#eee", modulos="#111", ojos="#222", marco="#333"),
        quiet_zone=5,
    )
    data = original.to_dict()
    data["url"] = "https://no-debe-guardarse.com"
    restaurado = Perfil.from_dict(data)
    assert restaurado == original
    assert "url" not in restaurado.to_dict()


@pytest.mark.unit
def test_from_dict_acepta_strings_de_enum() -> None:
    perfil = Perfil.from_dict(
        {
            "nombre": "x",
            "modulo_estilo": "gota",
            "ojo_estilo": "hoja",
            "marco_tipo": "banda",
            "correccion": "Q",
            "colores": {"fondo": "#fff", "modulos": "#000", "ojos": "#000", "marco": "#000"},
        }
    )
    assert perfil.modulo_estilo is ModuloEstilo.GOTA
    assert perfil.ojo_estilo is OjoEstilo.HOJA
    assert perfil.marco_tipo is MarcoTipo.BANDA
    assert perfil.correccion is Correccion.Q
