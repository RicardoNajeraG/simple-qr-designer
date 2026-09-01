"""CLI end-to-end: genera archivo y reporta peso."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.integration
def test_cli_svg_reporta_peso(tmp_path: Path) -> None:
    destino = tmp_path / "qr.svg"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "qr_designer",
            "--url",
            "https://example.com",
            "--preset",
            "Clásico",
            "-o",
            str(destino),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert destino.is_file()
    peso = destino.stat().st_size
    assert peso > 0
    assert str(peso) in proc.stdout
    assert "bytes" in proc.stdout
    assert destino.read_bytes().startswith(b"<svg")


@pytest.mark.integration
@pytest.mark.raster
def test_cli_png_decodificable(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    destino = tmp_path / "qr.png"
    payload = "https://example.com/cli"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "qr_designer",
            "--url",
            payload,
            "-o",
            str(destino),
            "--format",
            "png",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert destino.is_file()
    assert "bytes" in proc.stdout
    zxingcpp = pytest.importorskip("zxingcpp")
    from io import BytesIO

    from PIL import Image

    img = Image.open(BytesIO(destino.read_bytes())).convert("RGB")
    leidos = zxingcpp.read_barcodes(img)
    assert leidos
    assert leidos[0].text == payload
