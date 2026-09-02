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


@pytest.mark.integration
def test_cli_logo_embebe_en_svg(tmp_path: Path) -> None:
    from tests.png_bytes import escribir_png

    logo = escribir_png(tmp_path / "logo.png", 3, 3)
    destino = tmp_path / "qr.svg"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "qr_designer",
            "--url",
            "https://example.com",
            "--logo",
            str(logo),
            "-o",
            str(destino),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    datos = destino.read_text(encoding="utf-8")
    assert "<image" in datos
    assert "data:image" in datos


@pytest.mark.integration
def test_cli_logo_svg_embebe_en_svg(tmp_path: Path) -> None:
    from tests.png_bytes import escribir_svg_rect

    logo = escribir_svg_rect(tmp_path / "logo.svg")
    destino = tmp_path / "qr.svg"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "qr_designer",
            "--url",
            "https://example.com",
            "--logo",
            str(logo),
            "-o",
            str(destino),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    datos = destino.read_text(encoding="utf-8")
    assert datos.lower().count("<svg") == 1
    assert "data:image/svg+xml" not in datos
    assert 'fill="#ff0000"' in datos
    assert "<g transform=" in datos
