"""Fixtures compartidos. No importan Pillow ni tkinter."""

from __future__ import annotations

from pathlib import Path

import pytest

MOCKUPS = Path(__file__).resolve().parent / "mockups"
PAYLOAD_REFERENCIA = "https://example.com"


@pytest.fixture
def payload_referencia() -> str:
    return PAYLOAD_REFERENCIA


@pytest.fixture
def dir_perfiles(tmp_path: Path) -> Path:
    return tmp_path / "qr_designer_home"
