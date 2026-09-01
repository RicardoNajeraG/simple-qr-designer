"""Primitivas vectoriales inmutables. Sin Pillow ni tkinter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union


def _r(v: float) -> float:
    return round(float(v), 6)


@dataclass(frozen=True)
class Rect:
    id: str
    x: float
    y: float
    w: float
    h: float
    fill: str
    role: str
    rx: float = 0.0
    ry: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _r(self.x))
        object.__setattr__(self, "y", _r(self.y))
        object.__setattr__(self, "w", _r(self.w))
        object.__setattr__(self, "h", _r(self.h))
        object.__setattr__(self, "rx", _r(self.rx))
        object.__setattr__(self, "ry", _r(self.ry))

    def geometry(self) -> tuple:
        return ("rect", self.id, self.x, self.y, self.w, self.h, self.rx, self.ry, self.role)


@dataclass(frozen=True)
class Circle:
    id: str
    cx: float
    cy: float
    r: float
    fill: str
    role: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "cx", _r(self.cx))
        object.__setattr__(self, "cy", _r(self.cy))
        object.__setattr__(self, "r", _r(self.r))

    def geometry(self) -> tuple:
        return ("circle", self.id, self.cx, self.cy, self.r, self.role)


@dataclass(frozen=True)
class Path:
    id: str
    points: tuple[tuple[float, float], ...]
    fill: str
    role: str

    def __post_init__(self) -> None:
        pts = tuple((_r(x), _r(y)) for x, y in self.points)
        object.__setattr__(self, "points", pts)

    def geometry(self) -> tuple:
        return ("path", self.id, self.points, self.role)


@dataclass(frozen=True)
class Text:
    id: str
    x: float
    y: float
    text: str
    fill: str
    font_size: float
    role: str = "texto_marco"
    anchor: str = "middle"

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _r(self.x))
        object.__setattr__(self, "y", _r(self.y))
        object.__setattr__(self, "font_size", _r(self.font_size))

    def geometry(self) -> tuple:
        return ("text", self.id, self.x, self.y, self.text, self.font_size, self.anchor, self.role)


Primitiva = Union[Rect, Circle, Path, Text]


@dataclass(frozen=True)
class Escena:
    width: float
    height: float
    background: str
    items: tuple[Primitiva, ...]
    module_count: int
    quiet_zone: int
    origen_qr: tuple[float, float]
    pad: tuple[float, float, float, float]

    def __post_init__(self) -> None:
        object.__setattr__(self, "width", _r(self.width))
        object.__setattr__(self, "height", _r(self.height))
        ox, oy = self.origen_qr
        object.__setattr__(self, "origen_qr", (_r(ox), _r(oy)))
        object.__setattr__(self, "pad", tuple(_r(v) for v in self.pad))  # type: ignore[arg-type]

    def ids(self) -> tuple[str, ...]:
        return tuple(i.id for i in self.items)

    def geometry(self) -> tuple:
        return (self.width, self.height, self.origen_qr, self.pad, tuple(i.geometry() for i in self.items))

    def por_rol(self, role: str) -> tuple[Primitiva, ...]:
        return tuple(i for i in self.items if i.role == role)
