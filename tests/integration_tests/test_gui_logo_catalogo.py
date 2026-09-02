"""GUI: botones de catálogo con exclusión mutua."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def _parche_catalogo(monkeypatch, tmp_path: Path):
    from qr_designer.logos import EntradaLogo, LogoDesconocido
    from tests.png_bytes import escribir_png

    alfa = escribir_png(tmp_path / "alfa.png", 32, 32)
    beta = escribir_png(tmp_path / "beta.png", 32, 32)
    entradas = (
        EntradaLogo(id="alfa", nombre="alfa", filename="alfa.png", path=alfa),
        EntradaLogo(id="beta", nombre="beta", filename="beta.png", path=beta),
    )

    def listar(raiz=None):
        return entradas

    def resolver(ident: str, raiz=None):
        for e in entradas:
            if e.id == ident:
                return e.path
        raise LogoDesconocido(ident)

    monkeypatch.setattr("qr_designer.logos.listar_logos", listar)
    monkeypatch.setattr("qr_designer.logos.resolver_logo", resolver)
    import qr_designer.ui.gui as gui_mod

    monkeypatch.setattr(gui_mod, "listar_logos", listar)
    return alfa, beta


def _arrancar(tmp_path):
    tk = pytest.importorskip("tkinter")
    from qr_designer.ui.fonts import registrar_fuentes

    registrar_fuentes()
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError as exc:
        pytest.skip(f"tkinter no disponible: {exc}")
    from qr_designer.config.profiles import GestorPerfiles
    from qr_designer.ui.gui import QRDesignerApp, ProgramadorTk
    from qr_designer.ui.viewmodel import ViewModel

    vm = ViewModel(
        gestor=GestorPerfiles(tmp_path / "profiles.json"),
        programador=ProgramadorTk(root),
    )
    root.deiconify()
    app = QRDesignerApp(root, vm=vm)
    root.geometry("980x720")
    root.update()
    app._inicializar_sash()
    root.update()
    return tk, root, app


@pytest.mark.gui
@pytest.mark.integration
def test_botones_catalogo_exclusion_quitar_y_elegir(tmp_path, monkeypatch) -> None:
    if not os.environ.get("DISPLAY"):
        pytest.skip("sin DISPLAY")
    from qr_designer.ui.theme import ACENTO, BORDE
    from tests.png_bytes import escribir_png

    _parche_catalogo(monkeypatch, tmp_path)
    propio = escribir_png(tmp_path / "mio.png", 16, 16)
    _tk, root, app = _arrancar(tmp_path)
    try:
        assert set(app.btns_logo_catalogo) == {"alfa", "beta"}
        assert app.btns_logo_catalogo["alfa"].winfo_ismapped()
        assert app.btns_logo_catalogo["beta"].winfo_ismapped()
        for caja in app.cajas_logo_catalogo.values():
            assert caja.borde == BORDE
            assert not caja.presionado

        app.var_url.set("https://example.com")
        root.update()
        app.btns_logo_catalogo["alfa"].invoke()
        root.update()
        assert app.vm.perfil.logo_id == "alfa"
        assert app.vm.perfil.logo_path is None
        assert app.cajas_logo_catalogo["alfa"].borde == ACENTO
        assert app.cajas_logo_catalogo["alfa"].presionado
        assert app.cajas_logo_catalogo["beta"].borde == BORDE
        assert not app.cajas_logo_catalogo["beta"].presionado
        assert app.vm.escena is not None
        logos = app.vm.escena.por_rol("logo")
        assert logos
        assert Path(logos[0].ruta).name == "alfa.png"

        app.btns_logo_catalogo["beta"].invoke()
        root.update()
        assert app.vm.perfil.logo_id == "beta"
        assert app.cajas_logo_catalogo["beta"].presionado
        assert not app.cajas_logo_catalogo["alfa"].presionado
        assert Path(app.vm.escena.por_rol("logo")[0].ruta).name == "beta.png"

        app.btns_logo_catalogo["beta"].invoke()
        root.update()
        assert app.vm.perfil.logo_id == "beta"
        assert app.cajas_logo_catalogo["beta"].presionado

        app.btn_quitar_logo.invoke()
        root.update()
        assert app.vm.perfil.logo_id is None
        assert app.vm.perfil.logo_path is None
        assert not app.cajas_logo_catalogo["alfa"].presionado
        assert not app.cajas_logo_catalogo["beta"].presionado
        assert app.vm.escena.por_rol("logo") == ()

        app.btns_logo_catalogo["alfa"].invoke()
        root.update()
        monkeypatch.setattr(
            "qr_designer.ui.gui.filedialog.askopenfilename",
            lambda *_a, **_k: str(propio),
        )
        app.btn_elegir_logo.invoke()
        root.update()
        assert app.vm.perfil.logo_id is None
        assert app.vm.perfil.logo_path == str(propio)
        assert not app.cajas_logo_catalogo["alfa"].presionado
        assert not app.cajas_logo_catalogo["beta"].presionado
    finally:
        root.destroy()
