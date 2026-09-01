"""Test de humo de la GUI. Se omite sin DISPLAY o si tkinter no arranca."""

from __future__ import annotations

import os

import pytest


@pytest.mark.gui
@pytest.mark.integration
def test_ventana_arranca_renderiza_y_cierra(tmp_path) -> None:
    if not os.environ.get("DISPLAY"):
        pytest.skip("sin DISPLAY")
    tk = pytest.importorskip("tkinter")
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
    root.update_idletasks()
    assert app.vm.etiqueta_perfil == "Clásico"
    assert app.vm.avanzado_colapsado is True
    app.var_url.set("https://example.com")
    app._on_url()
    root.update()
    assert app.vm.puede_exportar
    assert app.vm.escena is not None
    assert app.canvas.find_all()
    root.destroy()
