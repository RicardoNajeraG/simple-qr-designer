"""GUI: elegir y quitar logotipo."""

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
def test_elegir_y_quitar_logo(tmp_path, monkeypatch) -> None:
    if not os.environ.get("DISPLAY"):
        pytest.skip("sin DISPLAY")
    from tests.png_bytes import escribir_png

    logo = escribir_png(tmp_path / "marca.png", 16, 16)
    _tk, root, app = _arrancar(tmp_path)
    try:
        app.var_url.set("https://example.com")
        root.update()
        assert app.btn_elegir_logo.winfo_ismapped()
        texto = str(app.btn_elegir_logo.cget("text"))
        assert texto == "Elegir imagen"
        assert "…" not in texto
        assert "..." not in texto
        assert str(app.btn_quitar_logo.cget("state")) == "disabled"
        assert "Ninguno" in app.lbl_logo.cget("text")
        sin_logo = app.canvas.find_all()

        capturado: dict = {}

        def _abrir(*_a, **kwargs):
            capturado.update(kwargs)
            return str(logo)

        monkeypatch.setattr("qr_designer.ui.gui.filedialog.askopenfilename", _abrir)
        app.btn_elegir_logo.invoke()
        root.update()
        tipos = capturado.get("filetypes") or []
        assert any("*.svg" in patron for _etiqueta, patron in tipos)
        assert app.vm.perfil.logo_path == str(logo)
        assert "marca.png" in app.lbl_logo.cget("text")
        assert str(app.btn_quitar_logo.cget("state")) == "normal"
        assert app.vm.escena is not None
        assert app.vm.escena.por_rol("logo")
        con_logo = app.canvas.find_all()
        assert con_logo != sin_logo

        app.btn_quitar_logo.invoke()
        root.update()
        assert app.vm.perfil.logo_path is None
        assert "Ninguno" in app.lbl_logo.cget("text")
        assert str(app.btn_quitar_logo.cget("state")) == "disabled"
        assert app.vm.escena.por_rol("logo") == ()
    finally:
        root.destroy()
