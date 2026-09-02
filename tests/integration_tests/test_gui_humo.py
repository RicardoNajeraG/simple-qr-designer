"""Test de humo de la GUI. Se omite sin DISPLAY o si tkinter no arranca."""

from __future__ import annotations

import os
import time

import pytest


def _textos(widget) -> list[str]:
    textos: list[str] = []
    try:
        valor = str(widget.cget("text"))
        if valor:
            textos.append(valor)
    except Exception:
        pass
    for hijo in widget.winfo_children():
        textos.extend(_textos(hijo))
    return textos


def _assert_canvas_centrado(app) -> None:
    marco = app.marco_preview
    canvas = app.canvas
    mw, mh = marco.winfo_width(), marco.winfo_height()
    cw, ch = canvas.winfo_width(), canvas.winfo_height()
    cx = canvas.winfo_rootx() - marco.winfo_rootx()
    cy = canvas.winfo_rooty() - marco.winfo_rooty()
    if mw <= 1 or mh <= 1:
        return
    assert abs((cx + cw / 2) - mw / 2) < 8
    assert abs((cy + ch / 2) - mh / 2) < 8


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
def test_ventana_arranca_renderiza_y_cierra(tmp_path) -> None:
    if not os.environ.get("DISPLAY"):
        pytest.skip("sin DISPLAY")
    from qr_designer.config.models import MarcoTipo
    from qr_designer.render.preview import px_para_preview
    from qr_designer.ui.gui import COMBO_ANCHO, HINT_CONTENIDO, PREVIEW_LADO
    from qr_designer.ui.theme import FONDO, ruta_icono
    from tkinter import ttk

    _tk, root, app = _arrancar(tmp_path)
    try:
        min_w, min_h = root.minsize()
        assert PREVIEW_LADO >= 400
        assert min_w >= PREVIEW_LADO
        assert min_h >= PREVIEW_LADO
        assert app.var_estado.get() == HINT_CONTENIDO
        assert str(app.btn_exportar.cget("style")) == "Primary.TButton"
        assert app.vm.etiqueta_perfil == "Clásico"
        assert app.vm.avanzado_colapsado is True
        assert app._icono is not None
        assert app._icono.width() <= 64
        assert app._icono.height() <= 64
        assert ruta_icono(64).is_file()
        assert FONDO.lower() == "#ffffff"
        assert isinstance(app.paned, ttk.Panedwindow)
        assert app.img_pet is not None
        assert app.img_banner is not None
        assert app.img_scraping is not None
        assert app.img_ayuda is not None
        assert app.btn_ayuda.winfo_ismapped()
        assert app.btn_ayuda.winfo_height() <= 28
        assert app.pie.winfo_height() <= 48
        assert app.lbl_estado.winfo_rootx() < app.btn_ayuda.winfo_rootx()
        assert app.btn_ayuda.winfo_rootx() > app.pie.winfo_rootx() + app.pie.winfo_width() // 2
        assert app.marco_preview is not None
        assert getattr(app.marco_opciones, "radio", 0) >= 8
        assert getattr(app.marco_preview, "radio", 0) >= 8
        assert app.marco_opciones.find_withtag("rr")
        assert app.marco_preview.find_withtag("rr")
        assert app.zona_export is not None
        textos_cabecera = _textos(app.cabecera)
        assert "QR Designer" not in textos_cabecera
        assert "Simple QR designer" not in textos_cabecera
        root.update()
        if app.lbl_banner is not None and app.lbl_pet is not None:
            assert app.lbl_banner.winfo_x() < app.lbl_pet.winfo_x()
        assert str(app.panel.vsb.winfo_manager()) == "grid"
        assert app.panel.vsb.winfo_ismapped()
        assert int(app.panel.vsb.cget("width")) >= 12
        if app.lbl_scraping is not None:
            img_base = app.lbl_scraping.winfo_rooty() + app.lbl_scraping.winfo_height()
            btn_top = app.btn_exportar.winfo_rooty()
            assert img_base <= btn_top + 2
            assert app.lbl_exportar.winfo_rootx() < app.lbl_scraping.winfo_rootx()
            ly1 = app.lbl_exportar.winfo_rooty()
            ly2 = ly1 + app.lbl_exportar.winfo_height()
            iy1 = app.lbl_scraping.winfo_rooty()
            iy2 = iy1 + app.lbl_scraping.winfo_height()
            assert ly1 < iy2 and iy1 < ly2
        assert int(str(app.combo_modulo.cget("width"))) == COMBO_ANCHO
        root.update()
        fila_url = app.entry_url.master.master
        fila_url.update_idletasks()
        caja_url = app.entry_url.master
        if fila_url.winfo_width() > 20:
            ratio = caja_url.winfo_width() / fila_url.winfo_width()
            assert 0.82 <= ratio <= 0.98
        assert not app.frm_marco_texto.winfo_ismapped()
        app.var_marco.set(MarcoTipo.PERIMETRO.value)
        app._on_marco()
        root.update()
        assert app.frm_marco_texto.winfo_ismapped()
        app.var_marco.set(MarcoTipo.NINGUNO.value)
        app._on_marco()
        root.update()
        assert not app.frm_marco_texto.winfo_ismapped()

        root.update()
        ancho_sw = max(app.pal_swatches.winfo_reqwidth(), 80)
        sash = app.paned.sashpos(0)
        assert ancho_sw > 0
        assert sash >= 180
        assert sash >= min(ancho_sw, app.ancho_opciones_inicial()) - 8

        app.var_url.set("https://example.com")
        root.update()
        assert app.vm.contenido == "https://example.com"
        assert app.vm.puede_exportar
        assert app.vm.escena is not None
        assert app.canvas.find_all()
        assert app.var_estado.get() != HINT_CONTENIDO
        hints_canvas = [
            i
            for i in app.canvas.find_all()
            if app.canvas.type(i) == "text"
            and app.canvas.itemcget(i, "text") == HINT_CONTENIDO
        ]
        assert hints_canvas == []
        px = px_para_preview(app.vm.escena, PREVIEW_LADO)
        assert int(app.canvas.cget("width")) == round(app.vm.escena.width * px)
        assert int(app.canvas.cget("height")) == round(app.vm.escena.height * px)
        _assert_canvas_centrado(app)
        assert app.canvas.winfo_rootx() >= app.marco_preview.winfo_rootx()
        assert app.canvas.winfo_rooty() >= app.marco_preview.winfo_rooty()
        assert (
            app.canvas.winfo_rootx() + app.canvas.winfo_width()
            <= app.marco_preview.winfo_rootx() + app.marco_preview.winfo_width() + 1
        )
        assert (
            app.canvas.winfo_rooty() + app.canvas.winfo_height()
            <= app.marco_preview.winfo_rooty() + app.marco_preview.winfo_height() + 1
        )

        app.var_avanzado.set(True)
        app._toggle_avanzado()
        root.update()
        assert app.frm_adv.winfo_ismapped()
        assert app.chk_avanzado.winfo_rooty() <= app.frm_adv.winfo_rooty()
        assert (
            app.frm_adv.winfo_rooty() + app.frm_adv.winfo_height()
            <= app.zona_export.winfo_rooty() + 2
        )

        app.var_url.set("")
        root.update()
        assert app.var_estado.get() == HINT_CONTENIDO
        app.var_url.set("https://example.com")
        root.update()

        pos = app.paned.sashpos(0)
        app.paned.sashpos(0, pos + 40)
        root.update_idletasks()
        assert app.paned.sashpos(0) != pos

        app.var_url.set("Hola mundo, esto no es una URL")
        root.update()
        assert app.vm.contenido == "Hola mundo, esto no es una URL"
        assert app.vm.puede_exportar
        assert app.var_formato.get() == "svg"

        from qr_designer.meta import REPO_URL, version_app

        app.btn_ayuda.event_generate("<Button-1>")
        root.update()
        assert app.ventana_acerca is not None
        assert app.ventana_acerca.winfo_ismapped()
        assert int(app.ventana_acerca.wm_overrideredirect() or 0) == 0
        assert "Acerca" in app.ventana_acerca.title()
        assert version_app() in app.ventana_acerca.texto
        assert REPO_URL in app.ventana_acerca.texto
        app._cerrar_acerca()
        root.update()
        assert app.ventana_acerca is None
    finally:
        root.destroy()


@pytest.mark.gui
@pytest.mark.raster
@pytest.mark.integration
def test_export_png_no_se_queda_exportando(tmp_path, monkeypatch) -> None:
    if not os.environ.get("DISPLAY"):
        pytest.skip("sin DISPLAY")
    pytest.importorskip("PIL")

    _tk, root, app = _arrancar(tmp_path)
    try:
        destino = tmp_path / "qr.png"
        monkeypatch.setattr(
            "qr_designer.ui.gui.filedialog.asksaveasfilename",
            lambda **_kw: str(destino),
        )
        app.var_url.set("https://example.com")
        app.var_formato.set("png")
        root.update()
        app._exportar()
        limite = time.time() + 15
        while time.time() < limite:
            root.update()
            if destino.is_file() and app.var_estado.get() != "Exportando...":
                break
            time.sleep(0.05)
        assert destino.is_file()
        assert destino.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        assert app.var_estado.get() != "Exportando..."
        assert str(app.btn_exportar.cget("state")) == "normal"
    finally:
        root.destroy()
