"""Tests de presets y GestorPerfiles."""

from __future__ import annotations

import json
from pathlib import Path
from shutil import copyfile

import pytest

from qr_designer.config.models import ModuloEstilo, Perfil
from qr_designer.config.presets import NOMBRES_PRESET, PRESETS, preset_clasico
from qr_designer.config.profiles import (
    GestorPerfiles,
    PerfilCorrupto,
    PerfilNoEncontrado,
    PerfilProtegido,
    PerfilYaExiste,
    SCHEMA_VERSION,
)

MOCKUPS = Path(__file__).resolve().parents[1] / "mockups" / "profiles"


@pytest.fixture
def gestor(tmp_path: Path) -> GestorPerfiles:
    return GestorPerfiles(tmp_path / "profiles.json")


@pytest.mark.unit
def test_hay_cuatro_o_cinco_presets_y_clasico_es_default() -> None:
    assert 4 <= len(PRESETS) <= 5
    assert preset_clasico().nombre == "Clásico"
    assert preset_clasico().modulo_estilo is ModuloEstilo.CUADRADO


@pytest.mark.unit
def test_primera_ejecucion_sin_archivo_ofrece_default(gestor: GestorPerfiles) -> None:
    assert not gestor.ruta.exists()
    assert gestor.listar() == []
    assert gestor.por_defecto() == preset_clasico()
    assert gestor.obtener("Clásico") == preset_clasico()


@pytest.mark.unit
def test_crud_guardar_listar_obtener_eliminar(gestor: GestorPerfiles) -> None:
    p = Perfil(nombre="Mia", modulo_estilo=ModuloEstilo.GOTA)
    gestor.guardar(p)
    assert [x.nombre for x in gestor.listar()] == ["Mia"]
    assert gestor.obtener("Mia") == p
    gestor.eliminar("Mia")
    assert gestor.listar() == []
    with pytest.raises(PerfilNoEncontrado):
        gestor.obtener("Mia")


@pytest.mark.unit
def test_guardar_sin_overwrite_falla_si_existe(gestor: GestorPerfiles) -> None:
    gestor.guardar(Perfil(nombre="Mia"))
    with pytest.raises(PerfilYaExiste):
        gestor.guardar(Perfil(nombre="Mia", modulo_estilo=ModuloEstilo.PUNTOS))
    gestor.guardar(Perfil(nombre="Mia", modulo_estilo=ModuloEstilo.PUNTOS), overwrite=True)
    assert gestor.obtener("Mia").modulo_estilo is ModuloEstilo.PUNTOS


@pytest.mark.unit
def test_presets_no_se_sobrescriben_ni_borran(gestor: GestorPerfiles) -> None:
    with pytest.raises(PerfilProtegido):
        gestor.guardar(Perfil(nombre="Clásico"))
    with pytest.raises(PerfilProtegido):
        gestor.eliminar("Clásico")
    with pytest.raises(PerfilProtegido):
        gestor.renombrar("Clásico", "Otro")


@pytest.mark.unit
def test_renombrar_atomico(gestor: GestorPerfiles) -> None:
    gestor.guardar(Perfil(nombre="Alpha", modulo_estilo=ModuloEstilo.PUNTOS))
    gestor.renombrar("Alpha", "Beta")
    nombres = {p.nombre for p in gestor.listar()}
    assert nombres == {"Beta"}
    assert gestor.obtener("Beta").modulo_estilo is ModuloEstilo.PUNTOS
    with pytest.raises(PerfilNoEncontrado):
        gestor.obtener("Alpha")


@pytest.mark.unit
def test_renombrar_no_borra_si_falla_el_guardado(
    gestor: GestorPerfiles, monkeypatch: pytest.MonkeyPatch
) -> None:
    gestor.guardar(Perfil(nombre="Alpha"))
    original = gestor.ruta.read_text(encoding="utf-8")

    def boom(*_a, **_k):
        raise OSError("disco lleno")

    monkeypatch.setattr("qr_designer.config.profiles._atomic_write", boom)
    with pytest.raises(OSError):
        gestor.renombrar("Alpha", "Beta")
    assert gestor.ruta.read_text(encoding="utf-8") == original
    assert gestor.obtener("Alpha").nombre == "Alpha"


@pytest.mark.unit
def test_escritura_atomica_no_deja_tmp(gestor: GestorPerfiles) -> None:
    gestor.guardar(Perfil(nombre="Z"))
    leftovers = list(gestor.ruta.parent.glob(".profiles.*.tmp"))
    assert leftovers == []
    data = json.loads(gestor.ruta.read_text(encoding="utf-8"))
    assert data["schema_version"] == SCHEMA_VERSION


@pytest.mark.unit
def test_carga_valido_desde_mockup(tmp_path: Path) -> None:
    dest = tmp_path / "profiles.json"
    copyfile(MOCKUPS / "valido.json", dest)
    g = GestorPerfiles(dest)
    p = g.obtener("Marca")
    assert p.modulo_estilo is ModuloEstilo.PUNTOS


@pytest.mark.unit
def test_corrupto_backup_y_no_destruye(tmp_path: Path) -> None:
    dest = tmp_path / "profiles.json"
    copyfile(MOCKUPS / "corrupto.json", dest)
    before = dest.read_bytes()
    g = GestorPerfiles(dest)
    with pytest.raises(PerfilCorrupto):
        g.listar()
    assert dest.read_bytes() == before
    bak = dest.with_suffix(".json.bak")
    assert bak.exists()
    assert bak.read_bytes() == before


@pytest.mark.unit
def test_truncado_no_destruye(tmp_path: Path) -> None:
    dest = tmp_path / "profiles.json"
    copyfile(MOCKUPS / "truncado.json", dest)
    before = dest.read_bytes()
    g = GestorPerfiles(dest)
    with pytest.raises(PerfilCorrupto):
        g.listar()
    assert dest.read_bytes() == before


@pytest.mark.unit
def test_schema_v0_se_migra(tmp_path: Path) -> None:
    dest = tmp_path / "profiles.json"
    copyfile(MOCKUPS / "schema_v0.json", dest)
    g = GestorPerfiles(dest)
    p = g.obtener("Viejo")
    assert p.marco_tipo.value == "perimetro"
    data = json.loads(dest.read_text(encoding="utf-8"))
    assert data["schema_version"] == SCHEMA_VERSION
    assert "Viejo" in data["perfiles"]


@pytest.mark.unit
def test_preset_colado_en_json_se_ignora(gestor: GestorPerfiles) -> None:
    gestor.ruta.parent.mkdir(parents=True, exist_ok=True)
    gestor.ruta.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "perfiles": {
                    "Clásico": {
                        "nombre": "Clásico",
                        "modulo_estilo": "puntos",
                        "ojo_estilo": "cuadrado",
                        "marco_tipo": "ninguno",
                        "correccion": "M",
                        "colores": {
                            "fondo": "#ffffff",
                            "modulos": "#000000",
                            "ojos": "#000000",
                            "marco": "#000000",
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    assert gestor.obtener("Clásico") == preset_clasico()
    assert gestor.obtener("Clásico").modulo_estilo is not ModuloEstilo.PUNTOS
    assert all(p.nombre not in NOMBRES_PRESET for p in gestor.listar())


@pytest.mark.unit
def test_duplicar_clasico_crea_usuario_sin_tocar_preset(gestor: GestorPerfiles) -> None:
    copia = gestor.duplicar("Clásico", "Mia")
    assert copia.nombre == "Mia"
    assert copia.modulo_estilo is preset_clasico().modulo_estilo
    assert gestor.obtener("Clásico") == preset_clasico()
    assert [p.nombre for p in gestor.listar()] == ["Mia"]


@pytest.mark.unit
def test_duplicar_a_nombre_de_preset_falla(gestor: GestorPerfiles) -> None:
    with pytest.raises(PerfilProtegido):
        gestor.duplicar("Puntos", "Clásico")


@pytest.mark.unit
def test_duplicar_a_nombre_existente_falla(gestor: GestorPerfiles) -> None:
    gestor.guardar(Perfil(nombre="Mia"))
    with pytest.raises(PerfilYaExiste):
        gestor.duplicar("Clásico", "Mia")


@pytest.mark.unit
def test_schema_v1_sin_logo_carga_y_migra(tmp_path: Path) -> None:
    dest = tmp_path / "profiles.json"
    dest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "perfiles": {
                    "Mia": {
                        "nombre": "Mia",
                        "modulo_estilo": "cuadrado",
                        "ojo_estilo": "cuadrado",
                        "marco_tipo": "ninguno",
                        "correccion": "M",
                        "colores": {
                            "fondo": "#ffffff",
                            "modulos": "#000000",
                            "ojos": "#000000",
                            "marco": "#000000",
                        },
                        "quiet_zone": 4,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    g = GestorPerfiles(dest)
    p = g.obtener("Mia")
    assert p.logo_path is None
    assert p.logo_id is None
    data = json.loads(dest.read_text(encoding="utf-8"))
    assert data["schema_version"] == SCHEMA_VERSION
    assert SCHEMA_VERSION >= 3


@pytest.mark.unit
def test_guardar_y_duplicar_conservan_logo_path(gestor: GestorPerfiles, tmp_path: Path) -> None:
    logo = tmp_path / "marca.png"
    logo.write_text("no-es-png", encoding="utf-8")
    gestor.guardar(Perfil(nombre="Mia", logo_path=str(logo)))
    assert gestor.obtener("Mia").logo_path == str(logo)
    copia = gestor.duplicar("Mia", "Copia")
    assert copia.logo_path == str(logo)
    for p in PRESETS:
        assert p.logo_path is None
        assert p.logo_id is None


@pytest.mark.unit
def test_guardar_conserva_logo_id(gestor: GestorPerfiles) -> None:
    gestor.guardar(Perfil(nombre="Mia", logo_id="wifi"))
    assert gestor.obtener("Mia").logo_id == "wifi"
    copia = gestor.duplicar("Mia", "Copia")
    assert copia.logo_id == "wifi"


@pytest.mark.unit
def test_schema_v2_sin_logo_id_carga(tmp_path: Path) -> None:
    dest = tmp_path / "profiles.json"
    dest.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "perfiles": {
                    "Mia": {
                        "nombre": "Mia",
                        "modulo_estilo": "cuadrado",
                        "ojo_estilo": "cuadrado",
                        "marco_tipo": "ninguno",
                        "correccion": "M",
                        "colores": {
                            "fondo": "#ffffff",
                            "modulos": "#000000",
                            "ojos": "#000000",
                            "marco": "#000000",
                        },
                        "quiet_zone": 4,
                        "logo_path": "/tmp/x.png",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    g = GestorPerfiles(dest)
    p = g.obtener("Mia")
    assert p.logo_path == "/tmp/x.png"
    assert p.logo_id is None
    data = json.loads(dest.read_text(encoding="utf-8"))
    assert data["schema_version"] == SCHEMA_VERSION


@pytest.mark.unit
def test_es_preset() -> None:
    from qr_designer.config.profiles import es_preset

    assert es_preset("Clásico")
    assert es_preset("Puntos")
    assert not es_preset("Mia")
