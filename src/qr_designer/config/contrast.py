"""Contraste de luminancia, inversión y ocupación de módulos."""

from __future__ import annotations

from dataclasses import dataclass

from qr_designer.config.models import (
    ColorScheme,
    MarcoTipo,
    ModuloEstilo,
    Perfil,
    hex_a_rgb,
    parse_color,
)

UMBRAL_CONTRASTE = 3.0
UMBRAL_FILL = 0.70

FILL_RATIO: dict[ModuloEstilo, float] = {
    ModuloEstilo.CUADRADO: 1.0,
    ModuloEstilo.REDONDEADO: 0.95,
    ModuloEstilo.PUNTOS: 0.50,
    ModuloEstilo.GOTA: 0.55,
    ModuloEstilo.BARRAS_H: 0.70,
    ModuloEstilo.BARRAS_V: 0.70,
    ModuloEstilo.SQUIRCLE: 0.92,
}


def _canal_lineal(c: int) -> float:
    s = c / 255.0
    if s <= 0.04045:
        return s / 12.92
    return ((s + 0.055) / 1.055) ** 2.4


def luminancia_relativa(color: str) -> float:
    r, g, b = hex_a_rgb(parse_color(color))
    return 0.2126 * _canal_lineal(r) + 0.7152 * _canal_lineal(g) + 0.0722 * _canal_lineal(b)


def ratio_contraste(c1: str, c2: str) -> float:
    l1 = luminancia_relativa(c1)
    l2 = luminancia_relativa(c2)
    claro, oscuro = (l1, l2) if l1 >= l2 else (l2, l1)
    return (claro + 0.05) / (oscuro + 0.05)


def fill_ratio_estilo(estilo: ModuloEstilo) -> float:
    return FILL_RATIO[estilo]


def ecc_recomendada_por_estilo(perfil: Perfil) -> str:
    """Sugiere Q/H sin mutar el perfil. Valores: L/M/Q/H."""
    from qr_designer.config.models import Correccion

    ev = evaluar_contraste(perfil)
    actual = perfil.correccion
    if actual is Correccion.AUTO:
        base = Correccion.M
    else:
        base = actual
    if ev.invertido or ev.fill_ratio < UMBRAL_FILL or ev.ratio_modulos < UMBRAL_CONTRASTE:
        sugerida = Correccion.H
    elif ev.ratio_modulos < 4.5 or perfil.modulo_estilo in {
        ModuloEstilo.PUNTOS,
        ModuloEstilo.GOTA,
    }:
        sugerida = Correccion.Q
    else:
        sugerida = base
    orden = {Correccion.L: 0, Correccion.M: 1, Correccion.Q: 2, Correccion.H: 3}
    if orden.get(sugerida, 0) < orden.get(base, 0):
        return base.value
    return sugerida.value


@dataclass(frozen=True)
class EvaluacionContraste:
    ratio_modulos: float
    ratio_ojos: float
    ratio_marco: float
    invertido: bool
    fill_ratio: float
    advertencias: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.advertencias

    @property
    def bajo_contraste(self) -> bool:
        return self.ratio_modulos < UMBRAL_CONTRASTE or self.ratio_ojos < UMBRAL_CONTRASTE or (
            self.ratio_marco < UMBRAL_CONTRASTE
        )

    @property
    def baja_ocupacion(self) -> bool:
        return self.fill_ratio < UMBRAL_FILL


def evaluar_contraste(perfil: Perfil) -> EvaluacionContraste:
    colores: ColorScheme = perfil.colores
    ratio_m = ratio_contraste(colores.modulos, colores.fondo)
    ratio_o = ratio_contraste(colores.ojos, colores.fondo)
    ratio_r = ratio_contraste(colores.marco, colores.fondo)
    invertido = luminancia_relativa(colores.modulos) > luminancia_relativa(colores.fondo)
    fill = fill_ratio_estilo(perfil.modulo_estilo)
    avisos: list[str] = []
    if invertido:
        avisos.append(
            "QR invertido: los módulos son más claros que el fondo y muchos lectores fallan"
        )
    if ratio_m < UMBRAL_CONTRASTE:
        avisos.append(
            f"Contraste módulos/fondo bajo ({ratio_m:.2f}:1; mínimo orientativo {UMBRAL_CONTRASTE:.0f}:1)"
        )
    if ratio_o < UMBRAL_CONTRASTE:
        avisos.append(
            f"Contraste ojos/fondo bajo ({ratio_o:.2f}:1; mínimo orientativo {UMBRAL_CONTRASTE:.0f}:1)"
        )
    if perfil.marco_tipo is not MarcoTipo.NINGUNO and ratio_r < UMBRAL_CONTRASTE:
        avisos.append(
            f"Contraste marco/fondo bajo ({ratio_r:.2f}:1; mínimo orientativo {UMBRAL_CONTRASTE:.0f}:1)"
        )
    if fill < UMBRAL_FILL:
        avisos.append(
            f"Baja ocupación del módulo ({fill:.0%}) con estilo {perfil.modulo_estilo.value}; "
            "se recomienda corrección H"
        )
    return EvaluacionContraste(
        ratio_modulos=ratio_m,
        ratio_ojos=ratio_o,
        ratio_marco=ratio_r,
        invertido=invertido,
        fill_ratio=fill,
        advertencias=tuple(avisos),
    )
