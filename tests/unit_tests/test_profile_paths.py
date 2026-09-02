"""Rutas canónicas de profiles.json por SO y migración del legado."""

from __future__ import annotations

from pathlib import Path

import pytest

from qr_designer.config.profiles import (
    ruta_perfiles_canonica,
    ruta_perfiles_default,
    ruta_perfiles_legado,
)


@pytest.mark.unit
def test_win32_con_appdata(tmp_path: Path) -> None:
    appdata = tmp_path / "Roaming"
    ruta = ruta_perfiles_canonica("win32", tmp_path / "home", {"APPDATA": str(appdata)})
    assert ruta == appdata / "QR Designer" / "profiles.json"


@pytest.mark.unit
def test_win32_sin_appdata(tmp_path: Path) -> None:
    home = tmp_path / "home"
    ruta = ruta_perfiles_canonica("win32", home, {})
    assert ruta == home / "AppData" / "Roaming" / "QR Designer" / "profiles.json"


@pytest.mark.unit
def test_darwin(tmp_path: Path) -> None:
    home = tmp_path / "home"
    ruta = ruta_perfiles_canonica("darwin", home, {})
    assert ruta == home / "Library" / "Application Support" / "QR Designer" / "profiles.json"


@pytest.mark.unit
def test_linux(tmp_path: Path) -> None:
    home = tmp_path / "home"
    ruta = ruta_perfiles_canonica("linux", home, {})
    assert ruta == home / ".qr_designer" / "profiles.json"
    assert ruta == ruta_perfiles_legado(home)


@pytest.mark.unit
def test_migra_legado_si_no_hay_canonico(tmp_path: Path) -> None:
    home = tmp_path / "home"
    legado = ruta_perfiles_legado(home)
    legado.parent.mkdir(parents=True)
    legado.write_text('{"schema_version": 1, "perfiles": {}}', encoding="utf-8")
    canonica = ruta_perfiles_canonica("darwin", home, {})
    assert not canonica.exists()
    resuelta = ruta_perfiles_default("darwin", home, {})
    assert resuelta == canonica
    assert canonica.is_file()
    assert canonica.read_text(encoding="utf-8") == legado.read_text(encoding="utf-8")
    assert legado.is_file()


@pytest.mark.unit
def test_canonico_existente_no_se_pisa(tmp_path: Path) -> None:
    home = tmp_path / "home"
    legado = ruta_perfiles_legado(home)
    legado.parent.mkdir(parents=True)
    legado.write_text("LEGADO", encoding="utf-8")
    canonica = ruta_perfiles_canonica("darwin", home, {})
    canonica.parent.mkdir(parents=True)
    canonica.write_text("NUEVO", encoding="utf-8")
    resuelta = ruta_perfiles_default("darwin", home, {})
    assert resuelta == canonica
    assert canonica.read_text(encoding="utf-8") == "NUEVO"


@pytest.mark.unit
def test_copia_falla_usa_legado(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    legado = ruta_perfiles_legado(home)
    legado.parent.mkdir(parents=True)
    legado.write_text("{}", encoding="utf-8")

    def boom(*_a, **_k):
        raise OSError("disco lleno")

    monkeypatch.setattr("qr_designer.config.profiles.shutil.copy2", boom)
    resuelta = ruta_perfiles_default("darwin", home, {})
    assert resuelta == legado
    canonica = ruta_perfiles_canonica("darwin", home, {})
    assert not canonica.exists()
