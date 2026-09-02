"""UX testeable sin tkinter."""

from __future__ import annotations

from pathlib import Path

import pytest

from qr_designer.config.models import Correccion, MarcoTipo, ModuloEstilo, OjoEstilo
from qr_designer.config.presets import preset_clasico
from qr_designer.config.profiles import GestorPerfiles
from qr_designer.ui.viewmodel import ProgramadorManual, ViewModel


@pytest.fixture
def vm(tmp_path: Path) -> ViewModel:
    return ViewModel(
        gestor=GestorPerfiles(tmp_path / "profiles.json"),
        programador=ProgramadorManual(),
    )


def _flush(vm: ViewModel) -> None:
    assert isinstance(vm.programador, ProgramadorManual)
    vm.programador.flush()


@pytest.mark.unit
def test_rux01_url_deja_exportable_con_perfil_default(vm: ViewModel) -> None:
    assert vm.etiqueta_perfil == "Clásico"
    assert not vm.puede_exportar
    vm.set_url("https://example.com")
    assert vm.puede_exportar
    assert vm.acciones == 1
    assert vm.acciones + 1 <= 2  # el clic de exportar es el segundo
    assert vm.perfil.nombre == preset_clasico().nombre


@pytest.mark.unit
def test_exportar_deshabilitado_sin_contenido(vm: ViewModel) -> None:
    assert vm.escena is None
    assert not vm.puede_exportar
    with pytest.raises(ValueError, match="contenido"):
        vm.exportar("svg")


@pytest.mark.unit
def test_rux02_debounce_coalesce_rebuilds(vm: ViewModel) -> None:
    vm.set_url("https://example.com")
    assert vm.rebuilds == 1  # set_url es inmediato
    before = vm.rebuilds
    for color in ("#111111", "#222222", "#333333", "#444444"):
        vm.set_color("modulos", color)
    assert vm.rebuilds == before
    assert len(vm.programador.pendientes) == 1  # type: ignore[attr-defined]
    _flush(vm)
    assert vm.rebuilds == before + 1
    assert vm.perfil.colores.modulos == "#444444"


@pytest.mark.unit
def test_rux05_perfil_activo_y_modificado(vm: ViewModel) -> None:
    vm.set_url("https://example.com")
    assert vm.etiqueta_perfil == "Clásico"
    vm.set_modulo(ModuloEstilo.PUNTOS)
    _flush(vm)
    assert vm.modificado
    assert vm.etiqueta_perfil == "Clásico (modificado)"
    vm.guardar_perfil("Mia")
    assert vm.etiqueta_perfil == "Mia"
    assert not vm.modificado


@pytest.mark.unit
def test_rf08_advertencia_no_bloquea_export(vm: ViewModel) -> None:
    vm.set_url("https://example.com")
    vm.set_color("modulos", "#cccccc")
    _flush(vm)
    assert vm.advertencia_contraste
    assert vm.puede_exportar


@pytest.mark.unit
def test_avanzado_colapsado_por_defecto(vm: ViewModel) -> None:
    assert vm.avanzado_colapsado is True


@pytest.mark.unit
def test_ecc_recomendada_no_muta_preview(vm: ViewModel) -> None:
    vm.set_url("https://example.com")
    vm.set_modulo(ModuloEstilo.PUNTOS)
    _flush(vm)
    assert vm.matriz is not None
    assert vm.matriz.correccion is Correccion.M
    assert vm.ecc_recomendada == "H"
    assert vm.perfil.correccion is Correccion.M


@pytest.mark.unit
def test_guardar_y_exportar_son_acciones_distintas(vm: ViewModel, tmp_path: Path) -> None:
    vm.set_url("https://example.com")
    r = vm.exportar("svg")
    assert r.peso > 0
    assert vm.gestor.listar() == []
    vm.set_ojo(OjoEstilo.CIRCULO)
    _flush(vm)
    vm.guardar_perfil("Guardado")
    assert vm.gestor.obtener("Guardado").ojo_estilo is OjoEstilo.CIRCULO
    assert r.formato == "svg"


@pytest.mark.unit
def test_aplicar_perfil_resetea_modificado(vm: ViewModel) -> None:
    vm.set_url("https://example.com")
    vm.set_marco(MarcoTipo.PERIMETRO)
    _flush(vm)
    assert vm.modificado
    vm.aplicar_perfil("Clásico")
    _flush(vm)
    assert not vm.modificado
    assert vm.perfil.marco_tipo is MarcoTipo.NINGUNO
    assert vm.etiqueta_perfil == "Clásico"


@pytest.mark.unit
def test_duplicar_preset_crea_usuario(vm: ViewModel) -> None:
    copia = vm.gestor.duplicar("Clásico", "Mia")
    assert copia.nombre == "Mia"
    assert copia.modulo_estilo is preset_clasico().modulo_estilo
    assert vm.gestor.obtener("Clásico") == preset_clasico()
    assert [p.nombre for p in vm.gestor.listar()] == ["Mia"]


@pytest.mark.unit
def test_duplicar_perfil_no_cambia_origen_activo(vm: ViewModel) -> None:
    origen = vm.perfil_origen
    copia = vm.duplicar_perfil("Clásico", "Mia")
    assert copia.nombre == "Mia"
    assert copia.modulo_estilo is preset_clasico().modulo_estilo
    assert copia.ojo_estilo is preset_clasico().ojo_estilo
    assert vm.perfil_origen == origen
    assert vm.etiqueta_perfil == "Clásico"


@pytest.mark.unit
def test_eliminar_perfil_activo_vuelve_a_clasico(vm: ViewModel) -> None:
    vm.guardar_perfil("Mia")
    assert vm.perfil_origen == "Mia"
    vm.set_modulo(ModuloEstilo.PUNTOS)
    _flush(vm)
    assert vm.modificado
    vm.eliminar_perfil("Mia")
    _flush(vm)
    assert vm.perfil_origen == "Clásico"
    assert vm.etiqueta_perfil == "Clásico"
    assert not vm.modificado
    assert vm.gestor.listar() == []


@pytest.mark.unit
def test_eliminar_otro_usuario_no_cambia_el_activo(vm: ViewModel) -> None:
    vm.guardar_perfil("Mia")
    vm.gestor.guardar(vm.perfil.__class__(**{**vm.perfil.to_dict(), "nombre": "Otra"}))
    vm.eliminar_perfil("Otra")
    assert vm.perfil_origen == "Mia"
    assert vm.etiqueta_perfil == "Mia"
