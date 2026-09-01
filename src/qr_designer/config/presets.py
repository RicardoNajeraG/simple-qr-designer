"""Presets de fábrica. Inmutables: no se persisten ni se pueden borrar."""

from __future__ import annotations

from qr_designer.config.models import (
    ColorScheme,
    Correccion,
    MarcoTipo,
    ModuloEstilo,
    OjoEstilo,
    Perfil,
)

PRESET_CLASICO = Perfil(nombre="Clásico")

PRESET_REDONDEADO = Perfil(
    nombre="Redondeado",
    modulo_estilo=ModuloEstilo.REDONDEADO,
    ojo_estilo=OjoEstilo.REDONDEADO,
    colores=ColorScheme(fondo="#fffaf3", modulos="#1a1a1a", ojos="#1a1a1a", marco="#1a1a1a"),
)

PRESET_PUNTOS = Perfil(
    nombre="Puntos",
    modulo_estilo=ModuloEstilo.PUNTOS,
    ojo_estilo=OjoEstilo.CIRCULO,
    correccion=Correccion.H,
    colores=ColorScheme(fondo="#ffffff", modulos="#0b3d91", ojos="#0b3d91", marco="#0b3d91"),
)

PRESET_ESCANEAME = Perfil(
    nombre="Escanéame",
    marco_tipo=MarcoTipo.ESCANEAME,
    marco_texto="ESCANÉAME",
    colores=ColorScheme(fondo="#ffffff", modulos="#111111", ojos="#111111", marco="#111111"),
)

PRESET_BARRAS = Perfil(
    nombre="Barras",
    modulo_estilo=ModuloEstilo.BARRAS_H,
    ojo_estilo=OjoEstilo.SQUIRCLE,
    colores=ColorScheme(fondo="#f4efe6", modulos="#3d2914", ojos="#3d2914", marco="#3d2914"),
)

PRESETS: tuple[Perfil, ...] = (
    PRESET_CLASICO,
    PRESET_REDONDEADO,
    PRESET_PUNTOS,
    PRESET_ESCANEAME,
    PRESET_BARRAS,
)

NOMBRES_PRESET: frozenset[str] = frozenset(p.nombre for p in PRESETS)


def preset_por_nombre(nombre: str) -> Perfil | None:
    for p in PRESETS:
        if p.nombre == nombre:
            return p
    return None


def preset_clasico() -> Perfil:
    return PRESET_CLASICO
