"""Flujo completo de perfiles: guardar, aplicar, renombrar."""

from __future__ import annotations

from pathlib import Path

import pytest

from qr_designer.config.models import ColorScheme, ModuloEstilo, OjoEstilo, Perfil
from qr_designer.config.profiles import GestorPerfiles
from qr_designer.core.encoder import codificar
from qr_designer.scene.builders import construir_escena


@pytest.mark.integration
def test_guardar_aplicar_misma_escena(tmp_path: Path) -> None:
    gestor = GestorPerfiles(tmp_path / "profiles.json")
    original = Perfil(
        nombre="Marca",
        modulo_estilo=ModuloEstilo.REDONDEADO,
        ojo_estilo=OjoEstilo.HOJA,
        colores=ColorScheme(fondo="#fff8f0", modulos="#3a1f0a", ojos="#8b1e1e", marco="#3a1f0a"),
    )
    gestor.guardar(original)
    cargado = gestor.obtener("Marca")
    assert cargado == original
    matriz = codificar("https://example.com")
    a = construir_escena(matriz, original)
    b = construir_escena(matriz, cargado)
    assert a.geometry() == b.geometry()


@pytest.mark.integration
def test_renombrar_sigue_aplicando(tmp_path: Path) -> None:
    gestor = GestorPerfiles(tmp_path / "profiles.json")
    original = Perfil(nombre="Uno", modulo_estilo=ModuloEstilo.SQUIRCLE)
    gestor.guardar(original)
    gestor.renombrar("Uno", "Dos")
    matriz = codificar("payload-unico")
    antes = construir_escena(matriz, original)
    despues = construir_escena(matriz, gestor.obtener("Dos"))
    assert antes.geometry() == despues.geometry()
    nombres = {p.nombre for p in gestor.listar()}
    assert nombres == {"Dos"}
