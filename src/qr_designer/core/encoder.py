"""Encoder QR: segno queda detrás de MatrizQR."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from itertools import product

import segno
from segno.encoder import DataOverflowError as SegnoOverflow

from qr_designer.config.models import Correccion

# Posiciones de patrones de alineación (ISO/IEC 18004), por versión.
_ALIGNMENT: dict[int, tuple[int, ...]] = {
    1: (),
    2: (6, 18),
    3: (6, 22),
    4: (6, 26),
    5: (6, 30),
    6: (6, 34),
    7: (6, 22, 38),
    8: (6, 24, 42),
    9: (6, 26, 46),
    10: (6, 28, 50),
    11: (6, 30, 54),
    12: (6, 32, 58),
    13: (6, 34, 62),
    14: (6, 26, 46, 66),
    15: (6, 26, 48, 70),
    16: (6, 26, 50, 74),
    17: (6, 30, 54, 78),
    18: (6, 30, 56, 82),
    19: (6, 30, 58, 86),
    20: (6, 34, 62, 90),
    21: (6, 28, 50, 72, 94),
    22: (6, 26, 50, 74, 98),
    23: (6, 30, 54, 78, 102),
    24: (6, 28, 54, 80, 106),
    25: (6, 32, 58, 84, 110),
    26: (6, 30, 58, 86, 114),
    27: (6, 34, 62, 90, 118),
    28: (6, 26, 50, 74, 98, 122),
    29: (6, 30, 54, 78, 102, 126),
    30: (6, 26, 52, 78, 104, 130),
    31: (6, 30, 56, 82, 108, 134),
    32: (6, 34, 60, 86, 112, 138),
    33: (6, 30, 58, 86, 114, 142),
    34: (6, 34, 62, 90, 118, 146),
    35: (6, 30, 54, 78, 102, 126, 150),
    36: (6, 24, 50, 76, 102, 128, 154),
    37: (6, 28, 54, 80, 106, 132, 158),
    38: (6, 32, 58, 84, 110, 136, 162),
    39: (6, 26, 54, 82, 110, 138, 166),
    40: (6, 30, 58, 86, 114, 142, 170),
}


class QRDesignerError(Exception):
    """Error base del producto."""


class ContenidoVacioError(QRDesignerError):
    """No hay nada que codificar."""


class ContenidoDemasiadoLargoError(QRDesignerError):
    """El payload no cabe ni en un QR versión 40."""


class TipoModulo(StrEnum):
    DATO = "dato"
    FINDER = "finder"
    SEPARADOR = "separador"
    TIMING = "timing"
    ALIGNMENT = "alignment"


@dataclass(frozen=True)
class MatrizQR:
    contenido: str
    version: int
    correccion: Correccion
    size: int
    modules: tuple[tuple[bool, ...], ...]
    tipos: tuple[tuple[TipoModulo, ...], ...]

    def oscuro(self, x: int, y: int) -> bool:
        return self.modules[y][x]

    def tipo(self, x: int, y: int) -> TipoModulo:
        return self.tipos[y][x]

    def es_estilo_modulo(self, x: int, y: int) -> bool:
        """Módulos que se pintan con el estilo de dato (no ojos ni separadores)."""
        return self.tipos[y][x] in {
            TipoModulo.DATO,
            TipoModulo.TIMING,
            TipoModulo.ALIGNMENT,
        }


def _ecc_segno(correccion: Correccion) -> str:
    if correccion is Correccion.AUTO:
        return "m"
    return correccion.value.lower()


def _clasificar(n: int, version: int) -> tuple[tuple[TipoModulo, ...], ...]:
    grid = [[TipoModulo.DATO] * n for _ in range(n)]

    def marcar_rect(x0: int, y0: int, x1: int, y1: int, tipo: TipoModulo) -> None:
        for y in range(y0, y1):
            for x in range(x0, x1):
                if 0 <= x < n and 0 <= y < n:
                    grid[y][x] = tipo

    finders = ((0, 0), (n - 7, 0), (0, n - 7))
    for fx, fy in finders:
        marcar_rect(fx, fy, fx + 7, fy + 7, TipoModulo.FINDER)

    # Separadores de 1 módulo alrededor de cada finder.
    marcar_rect(0, 7, 8, 8, TipoModulo.SEPARADOR)
    marcar_rect(7, 0, 8, 8, TipoModulo.SEPARADOR)
    marcar_rect(n - 8, 7, n, 8, TipoModulo.SEPARADOR)
    marcar_rect(n - 8, 0, n - 7, 8, TipoModulo.SEPARADOR)
    marcar_rect(0, n - 8, 8, n - 7, TipoModulo.SEPARADOR)
    marcar_rect(7, n - 8, 8, n, TipoModulo.SEPARADOR)

    # Timing (no pisa finders; sí puede pisar lo que sea DATO).
    for i in range(8, n - 8):
        if grid[6][i] is TipoModulo.DATO:
            grid[6][i] = TipoModulo.TIMING
        if grid[i][6] is TipoModulo.DATO:
            grid[i][6] = TipoModulo.TIMING

    centros = _ALIGNMENT.get(version, ())
    for cx, cy in product(centros, centros):
        # Omitir alignments que coinciden con finders.
        if (cx, cy) in ((6, 6), (6, n - 7), (n - 7, 6)):
            continue
        marcar_rect(cx - 2, cy - 2, cx + 3, cy + 3, TipoModulo.ALIGNMENT)

    return tuple(tuple(fila) for fila in grid)


def codificar(contenido: str, correccion: Correccion = Correccion.M) -> MatrizQR:
    if not isinstance(contenido, str) or not contenido.strip():
        raise ContenidoVacioError("El contenido a codificar está vacío")
    ecc_usada = Correccion.M if correccion is Correccion.AUTO else correccion
    try:
        qr = segno.make_qr(contenido, error=_ecc_segno(ecc_usada), boost_error=False)
    except SegnoOverflow as exc:
        raise ContenidoDemasiadoLargoError(str(exc)) from exc
    n = len(qr.matrix)
    modules = tuple(tuple(bool(cell) for cell in fila) for fila in qr.matrix)
    tipos = _clasificar(n, int(qr.version))
    return MatrizQR(
        contenido=contenido,
        version=int(qr.version),
        correccion=ecc_usada,
        size=n,
        modules=modules,
        tipos=tipos,
    )
