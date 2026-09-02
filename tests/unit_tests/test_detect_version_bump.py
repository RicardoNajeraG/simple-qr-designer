"""El detector de bump de versión lee el mismo campo que la app."""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest

from qr_designer.meta import version_app

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "packaging" / "detect_version_bump.py"


@pytest.mark.unit
def test_detect_version_coincide_con_meta() -> None:
    ns = runpy.run_path(str(SCRIPT))
    assert ns["version_actual"]() == version_app()
    assert SCRIPT.is_file()
