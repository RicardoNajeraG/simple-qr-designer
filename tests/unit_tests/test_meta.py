"""Versión leída de pyproject.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from qr_designer import __version__
from qr_designer.meta import REPO_URL, version_app

RAIZ = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_version_app_igual_a_pyproject() -> None:
    with (RAIZ / "pyproject.toml").open("rb") as fh:
        datos = tomllib.load(fh)
    assert version_app() == datos["project"]["version"]
    assert __version__ == datos["project"]["version"]


@pytest.mark.unit
def test_repo_url_apunta_al_proyecto() -> None:
    assert REPO_URL == "https://github.com/RicardoNajeraG/simple-qr-designer"
