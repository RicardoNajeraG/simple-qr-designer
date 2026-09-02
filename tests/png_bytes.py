"""PNG mínimo sin Pillow, para tests de escena/SVG."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


def png_rgb(ancho: int, alto: int, color: tuple[int, int, int] = (255, 0, 0)) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0)
    fila = b"\x00" + bytes(color) * ancho
    idat = zlib.compress(fila * alto, 9)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def escribir_png(path: Path, ancho: int = 1, alto: int = 1, color: tuple[int, int, int] = (255, 0, 0)) -> Path:
    path.write_bytes(png_rgb(ancho, alto, color))
    return path


def escribir_svg_rect(
    path: Path,
    ancho: int = 40,
    alto: int = 40,
    fill: str = "#ff0000",
) -> Path:
    path.write_text(
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}">'
            f'<rect width="{ancho}" height="{alto}" fill="{fill}"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )
    return path
