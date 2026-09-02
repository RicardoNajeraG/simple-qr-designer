"""Catálogo de logos empaquetados: listar y resolver por id."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.png_bytes import escribir_png


@pytest.mark.unit
def test_listar_logos_id_stem_y_orden(tmp_path: Path) -> None:
    from qr_designer.logos import listar_logos

    escribir_png(tmp_path / "zeta.png", 4, 4)
    escribir_png(tmp_path / "alfa.png", 4, 4)
    (tmp_path / "ignore.txt").write_text("no", encoding="utf-8")
    entradas = listar_logos(raiz=tmp_path)
    assert [e.id for e in entradas] == ["alfa", "zeta"]
    assert entradas[0].filename == "alfa.png"
    assert entradas[0].path.is_file()
    assert entradas[0].nombre


@pytest.mark.unit
def test_resolver_logo_y_id_desconocido(tmp_path: Path) -> None:
    from qr_designer.logos import LogoDesconocido, listar_logos, resolver_logo

    escribir_png(tmp_path / "wifi.png", 4, 4)
    ruta = resolver_logo("wifi", raiz=tmp_path)
    assert ruta == listar_logos(raiz=tmp_path)[0].path
    assert ruta.name == "wifi.png"
    with pytest.raises(LogoDesconocido):
        resolver_logo("no-existe", raiz=tmp_path)


@pytest.mark.unit
def test_catalogo_paquete_si_hay_archivos() -> None:
    from qr_designer.logos import listar_logos

    entradas = listar_logos()
    if not entradas:
        pytest.skip("sin logos empaquetados")
    assert all(e.path.is_file() for e in entradas)
    assert len({e.id for e in entradas}) == len(entradas)
