"""Selector cromático: apertura, RGB en vivo, alfa no persistido."""

from __future__ import annotations

import os

import pytest


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
def test_selector_cromatico_swatch_hex_rgb_alfa(tmp_path) -> None:
    if not os.environ.get("DISPLAY"):
        pytest.skip("sin DISPLAY")

    _tk, root, app = _arrancar(tmp_path)
    try:
        assert app.ventana_color is None
        app._hex("modulos")
        app._colores["modulos"].set("#ff0000")
        app._hex("modulos")
        root.update()
        assert app.vm.perfil.colores.modulos == "#ff0000"

        app._colores["modulos"].set("#000000")
        app._hex("modulos")
        root.update()

        app._sw_modulos.invoke()
        root.update()
        dlg = app.ventana_color
        assert dlg is not None
        assert dlg.winfo_ismapped()
        assert int(dlg.wm_overrideredirect() or 0) == 0
        assert "módulos" in dlg.title().lower()
        assert dlg.canvas_rueda.winfo_exists()
        assert dlg.scale_valor.winfo_exists()
        assert dlg.scale_alfa.winfo_exists()
        for var in (dlg.var_r, dlg.var_g, dlg.var_b, dlg.var_a):
            assert var.get() != ""

        dlg.btn_cerrar.invoke()
        root.update()
        assert app.ventana_color is None

        app._entry_color["fondo"].event_generate("<Button-1>")
        root.update()
        dlg = app.ventana_color
        assert dlg is not None
        assert dlg.campo == "fondo"
        dlg.btn_cerrar.invoke()
        root.update()
        assert app.ventana_color is None

        app._entry_color["modulos"].focus_set()
        app._entry_color["modulos"].event_generate("<FocusIn>")
        root.update()
        assert app.ventana_color is None

        app._sw_modulos.invoke()
        root.update()
        dlg = app.ventana_color
        assert dlg is not None
        dlg.var_r.set("14")
        dlg.var_g.set("112")
        dlg.var_b.set("138")
        root.update()
        assert app.vm.perfil.colores.modulos == "#0e708a"
        previo = app.vm.perfil.colores.modulos
        dlg.var_a.set("40")
        root.update()
        assert app.vm.perfil.colores.modulos == previo

        dlg.btn_cerrar.invoke()
        root.update()
        assert app.ventana_color is None
    finally:
        root.destroy()
