"""Modelos de configuración: perfil, colores y solicitud."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

_HEX_DIGITS = frozenset("0123456789abcdef")

COLORES_NOMBRE: dict[str, str] = {
    "black": "#000000",
    "white": "#ffffff",
    "red": "#ff0000",
    "green": "#008000",
    "blue": "#0000ff",
    "navy": "#000080",
    "yellow": "#ffff00",
    "cyan": "#00ffff",
    "magenta": "#ff00ff",
    "gray": "#808080",
    "grey": "#808080",
    "orange": "#ffa500",
    "purple": "#800080",
    "pink": "#ffc0cb",
    "brown": "#a52a2a",
}

QUIET_ZONE_MIN = 4


class ColorInvalidoError(ValueError):
    """Color que no se puede interpretar como hex o nombre conocido."""


class ModuloEstilo(StrEnum):
    CUADRADO = "cuadrado"
    REDONDEADO = "redondeado"
    PUNTOS = "puntos"
    GOTA = "gota"
    BARRAS_H = "barras_h"
    BARRAS_V = "barras_v"
    SQUIRCLE = "squircle"


class OjoEstilo(StrEnum):
    CUADRADO = "cuadrado"
    REDONDEADO = "redondeado"
    CIRCULO = "circulo"
    HOJA = "hoja"
    SQUIRCLE = "squircle"


class MarcoTipo(StrEnum):
    NINGUNO = "ninguno"
    PERIMETRO = "perimetro"
    ESCANEAME = "escaneame"
    BANDA = "banda"


class Correccion(StrEnum):
    L = "L"
    M = "M"
    Q = "Q"
    H = "H"
    AUTO = "auto"


def parse_color(value: str) -> str:
    """Normaliza a `#rrggbb` en minúsculas. El canal alfa, si viene, se descarta."""
    if not isinstance(value, str) or not value.strip():
        raise ColorInvalidoError(f"Color inválido: {value!r}")
    crudo = value.strip().lower()
    if crudo in COLORES_NOMBRE:
        return COLORES_NOMBRE[crudo]
    hexpart = crudo[1:] if crudo.startswith("#") else crudo
    if not hexpart or any(c not in _HEX_DIGITS for c in hexpart):
        raise ColorInvalidoError(f"Color inválido: {value!r}")
    if len(hexpart) == 3:
        return "#" + "".join(c * 2 for c in hexpart)
    if len(hexpart) == 6:
        return "#" + hexpart
    if len(hexpart) == 8:
        return "#" + hexpart[:6]
    raise ColorInvalidoError(f"Color inválido: {value!r}")


def hex_a_rgb(color: str) -> tuple[int, int, int]:
    n = parse_color(color)
    return int(n[1:3], 16), int(n[3:5], 16), int(n[5:7], 16)


@dataclass(frozen=True)
class ColorScheme:
    fondo: str = "#ffffff"
    modulos: str = "#000000"
    ojos: str = "#000000"
    marco: str = "#000000"

    def __post_init__(self) -> None:
        object.__setattr__(self, "fondo", parse_color(self.fondo))
        object.__setattr__(self, "modulos", parse_color(self.modulos))
        object.__setattr__(self, "ojos", parse_color(self.ojos))
        object.__setattr__(self, "marco", parse_color(self.marco))

    def to_dict(self) -> dict[str, str]:
        return {
            "fondo": self.fondo,
            "modulos": self.modulos,
            "ojos": self.ojos,
            "marco": self.marco,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ColorScheme:
        kwargs: dict[str, str] = {}
        for clave in ("fondo", "modulos", "ojos", "marco"):
            if clave in data and data[clave] is not None:
                kwargs[clave] = str(data[clave])
        return cls(**kwargs)


@dataclass(frozen=True)
class Perfil:
    nombre: str
    modulo_estilo: ModuloEstilo = ModuloEstilo.CUADRADO
    ojo_estilo: OjoEstilo = OjoEstilo.CUADRADO
    marco_tipo: MarcoTipo = MarcoTipo.NINGUNO
    marco_texto: str | None = None
    correccion: Correccion = Correccion.M
    colores: ColorScheme = field(default_factory=ColorScheme)
    quiet_zone: int = QUIET_ZONE_MIN
    logo_path: str | None = None
    logo_id: str | None = None

    def __post_init__(self) -> None:
        if not self.nombre or not str(self.nombre).strip():
            raise ValueError("El perfil necesita un nombre")
        object.__setattr__(self, "nombre", str(self.nombre).strip())
        if isinstance(self.modulo_estilo, str):
            object.__setattr__(self, "modulo_estilo", ModuloEstilo(self.modulo_estilo))
        if isinstance(self.ojo_estilo, str):
            object.__setattr__(self, "ojo_estilo", OjoEstilo(self.ojo_estilo))
        if isinstance(self.marco_tipo, str):
            object.__setattr__(self, "marco_tipo", MarcoTipo(self.marco_tipo))
        if isinstance(self.correccion, str):
            object.__setattr__(self, "correccion", Correccion(self.correccion))
        if not isinstance(self.colores, ColorScheme):
            object.__setattr__(self, "colores", ColorScheme.from_dict(self.colores))
        if self.quiet_zone < QUIET_ZONE_MIN:
            raise ValueError(
                f"La quiet zone debe ser al menos {QUIET_ZONE_MIN} módulos"
            )
        ruta = self.logo_path
        if ruta is not None:
            limpio = str(ruta).strip()
            object.__setattr__(self, "logo_path", limpio or None)
        ident = self.logo_id
        if ident is not None:
            limpio_id = str(ident).strip()
            object.__setattr__(self, "logo_id", limpio_id or None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nombre": self.nombre,
            "modulo_estilo": self.modulo_estilo.value,
            "ojo_estilo": self.ojo_estilo.value,
            "marco_tipo": self.marco_tipo.value,
            "marco_texto": self.marco_texto,
            "correccion": self.correccion.value,
            "colores": self.colores.to_dict(),
            "quiet_zone": self.quiet_zone,
            "logo_path": self.logo_path,
            "logo_id": self.logo_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Perfil:
        conocidos = {
            "nombre",
            "modulo_estilo",
            "ojo_estilo",
            "marco_tipo",
            "marco_texto",
            "correccion",
            "colores",
            "quiet_zone",
            "logo_path",
            "logo_id",
        }
        kwargs: dict[str, Any] = {k: data[k] for k in conocidos if k in data}
        if "colores" in kwargs and isinstance(kwargs["colores"], Mapping):
            kwargs["colores"] = ColorScheme.from_dict(kwargs["colores"])
        return cls(**kwargs)


@dataclass(frozen=True)
class SolicitudQR:
    contenido: str
    perfil: Perfil
