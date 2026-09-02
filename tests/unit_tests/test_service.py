"""Tests de la fachada de servicio JSON-friendly."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from qr_designer.config.models import ColorInvalidoError, Perfil
from qr_designer.config.presets import preset_clasico
from qr_designer.service.dto import perfil_a_dict, perfil_desde_dict
from qr_designer.service.profile_service import ProfileService
from qr_designer.service.qr_service import evaluar, exportar_qr, generar_svg, previsualizar

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_generar_svg_devuelve_str_minificado() -> None:
    svg = generar_svg("https://example.com", perfil_a_dict(preset_clasico()))
    assert isinstance(svg, str)
    assert svg.startswith("<svg ")
    assert "\n" not in svg


@pytest.mark.unit
def test_exportar_svg_dict_con_bytes() -> None:
    out = exportar_qr("hola mundo", perfil_a_dict(Perfil(nombre="t")), "svg")
    assert isinstance(out["datos"], bytes)
    assert out["formato"] == "svg"
    assert out["peso"] == len(out["datos"])
    assert out["ancho"] > 0 and out["alto"] > 0
    assert isinstance(out["advertencias"], list)


@pytest.mark.unit
def test_evaluar_devuelve_dict_serializable() -> None:
    ev = evaluar(perfil_a_dict(preset_clasico()))
    assert ev["ok"] is True
    assert isinstance(ev["advertencias"], list)
    assert ev["ecc_recomendada"] in {"L", "M", "Q", "H"}


@pytest.mark.unit
def test_perfil_invalido_error_serializable() -> None:
    with pytest.raises((ColorInvalidoError, ValueError)):
        perfil_desde_dict(
            {
                "nombre": "malo",
                "colores": {"fondo": "no-es-color", "modulos": "#000", "ojos": "#000", "marco": "#000"},
            }
        )


@pytest.mark.unit
def test_preview_vacio_es_none() -> None:
    escena, matriz = previsualizar("  ", perfil_a_dict(preset_clasico()))
    assert escena is None and matriz is None


@pytest.mark.unit
def test_preview_texto_plano_construye_escena() -> None:
    escena, matriz = previsualizar("solo texto, no url", perfil_a_dict(preset_clasico()))
    assert escena is not None
    assert matriz is not None
    assert matriz.contenido == "solo texto, no url"


@pytest.mark.unit
def test_profile_service_crud_dict(tmp_path: Path) -> None:
    svc = ProfileService(tmp_path / "profiles.json")
    assert svc.listar() == []
    d = perfil_a_dict(Perfil(nombre="Web"))
    svc.guardar(d)
    assert svc.obtener("Web")["nombre"] == "Web"
    svc.renombrar("Web", "API")
    assert svc.obtener("API")["modulo_estilo"] == "cuadrado"
    svc.eliminar("API")
    assert svc.listar() == []


@pytest.mark.unit
def test_profile_service_duplicar(tmp_path: Path) -> None:
    svc = ProfileService(tmp_path / "profiles.json")
    copia = svc.duplicar("Clásico", "Mia")
    assert copia["nombre"] == "Mia"
    assert copia["modulo_estilo"] == "cuadrado"
    assert svc.obtener("Clásico")["nombre"] == "Clásico"


@pytest.mark.unit
def test_import_service_no_carga_pillow_ni_tkinter() -> None:
    codigo = (
        "import sys\n"
        "import qr_designer.service.qr_service\n"
        "import qr_designer.service.profile_service\n"
        "malos = [m for m in sys.modules if m == 'PIL' or m.startswith('PIL.') "
        "or m == 'tkinter' or m.startswith('tkinter.')]\n"
        "raise SystemExit(0 if not malos else 'Cargó: ' + ','.join(malos))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(ROOT / "src")},
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
