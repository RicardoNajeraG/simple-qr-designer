"""Tema visual: DPI, Nunito empaquetada, fondo blanco e íconos."""

from __future__ import annotations

import pytest

from qr_designer.ui.fonts import (
    FAMILIA,
    RUTA_BOLD,
    RUTA_OFL,
    RUTA_REGULAR,
    familia_activa,
    registrar_fuentes,
)
from qr_designer.ui.theme import (
    AYUDA_ICONO,
    BANNER_HEADER,
    FONDO,
    PET_HEADER,
    SCRAPING_FONDO,
    TAMANOS_ICONO,
    escala_para_dpi,
    preferencias_fuente,
    ruta_icono,
)

LIMITE_ICONO_BYTES = 100_000
LIMITE_TTF_BYTES = 400_000


@pytest.mark.unit
def test_fondo_es_blanco_de_las_ilustraciones() -> None:
    assert FONDO.lower() == "#ffffff"


@pytest.mark.unit
@pytest.mark.parametrize(
    "dpi,esperado",
    [
        (72, 1.0),
        (96, pytest.approx(96 / 72)),
        (192, pytest.approx(192 / 72)),
        (36, 1.0),
        (300, 3.0),
    ],
)
def test_escala_para_dpi(dpi: float, esperado: float) -> None:
    assert escala_para_dpi(dpi) == esperado


@pytest.mark.unit
def test_escala_para_dpi_acota_rango() -> None:
    assert 1.0 <= escala_para_dpi(1) <= 3.0
    assert 1.0 <= escala_para_dpi(1000) <= 3.0


@pytest.mark.unit
def test_preferencias_fuente_windows_son_fallback() -> None:
    prefs = preferencias_fuente("win32")
    assert prefs[0] == "Segoe UI"
    assert "Segoe UI" in prefs


@pytest.mark.unit
def test_preferencias_fuente_macos_son_fallback() -> None:
    prefs = preferencias_fuente("darwin")
    assert "SF Pro Text" in prefs
    assert "Helvetica Neue" in prefs
    assert prefs[0] == "SF Pro Text"


@pytest.mark.unit
def test_preferencias_fuente_linux_son_fallback() -> None:
    prefs = preferencias_fuente("linux")
    assert prefs[:4] == ("Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans")


@pytest.mark.unit
def test_preferencias_fuente_desconocida_usa_linux() -> None:
    assert preferencias_fuente("freebsd") == preferencias_fuente("linux")


@pytest.mark.unit
@pytest.mark.parametrize(
    "max_px,tamano",
    [
        (32, 32),
        (48, 64),
        (64, 64),
        (128, 256),
        (256, 256),
        (512, 256),
    ],
)
def test_ruta_icono_elige_preescalado(max_px: int, tamano: int) -> None:
    path = ruta_icono(max_px)
    assert path.name == f"qr-designer-icon-{tamano}.png"
    assert path.is_file()
    assert path.stat().st_size < LIMITE_ICONO_BYTES


@pytest.mark.unit
def test_assets_icono_existen_y_pesan_poco() -> None:
    for tamano in TAMANOS_ICONO:
        path = ruta_icono(tamano)
        assert path.is_file(), f"falta {path.name}"
        assert path.stat().st_size < LIMITE_ICONO_BYTES
        assert path.stat().st_size > 0


@pytest.mark.unit
def test_assets_cabecera_pet_y_banner() -> None:
    assert PET_HEADER.is_file()
    assert BANNER_HEADER.is_file()
    assert PET_HEADER.stat().st_size < LIMITE_ICONO_BYTES * 2
    assert BANNER_HEADER.stat().st_size < 250_000


@pytest.mark.unit
def test_asset_scraping_de_exportacion() -> None:
    assert SCRAPING_FONDO.is_file()
    assert 0 < SCRAPING_FONDO.stat().st_size < 250_000


@pytest.mark.unit
def test_asset_ayuda_pequeno() -> None:
    assert AYUDA_ICONO.is_file()
    assert AYUDA_ICONO.name == "question_mark-h20.png"
    assert 0 < AYUDA_ICONO.stat().st_size < 20_000


@pytest.mark.unit
def test_nunito_estatica_y_licencia_ofl() -> None:
    assert FAMILIA == "Nunito"
    assert RUTA_REGULAR.is_file()
    assert RUTA_BOLD.is_file()
    assert RUTA_OFL.is_file()
    assert 1_000 < RUTA_REGULAR.stat().st_size < LIMITE_TTF_BYTES
    assert 1_000 < RUTA_BOLD.stat().st_size < LIMITE_TTF_BYTES
    texto = RUTA_OFL.read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE" in texto


@pytest.mark.unit
def test_registrar_fuentes_es_idempotente() -> None:
    assert registrar_fuentes() in {True, False}
    assert registrar_fuentes() in {True, False}


@pytest.mark.unit
def test_familia_activa_prefiere_nunito_si_esta() -> None:
    tk = pytest.importorskip("tkinter")
    from tkinter import font as tkfont

    try:
        registrar_fuentes()
        root = tk.Tk()
        root.withdraw()
    except tk.TclError as exc:
        pytest.skip(f"tkinter no disponible: {exc}")
    fam = familia_activa(root)
    disponibles = set(tkfont.families(root))
    if FAMILIA in disponibles:
        assert fam == FAMILIA
    else:
        assert fam in preferencias_fuente() or fam == "TkDefaultFont"
    root.destroy()
