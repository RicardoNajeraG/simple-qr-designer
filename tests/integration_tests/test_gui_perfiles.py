"""Diálogo Gestionar perfiles."""

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


@pytest.mark.unit
def test_nombre_duplicado_propuesto() -> None:
    pytest.importorskip("tkinter")
    from qr_designer.ui.perfiles_dialog import nombre_duplicado_propuesto, nombre_libre_propuesto

    assert nombre_duplicado_propuesto("Clásico", set()) == "Clásico copia"
    ocupados = {"Clásico copia"}
    assert nombre_duplicado_propuesto("Clásico", ocupados) == "Clásico copia 2"
    ocupados.add("Clásico copia 2")
    assert nombre_duplicado_propuesto("Clásico", ocupados) == "Clásico copia 3"
    assert nombre_libre_propuesto("Nuevo perfil", set()) == "Nuevo perfil"
    assert nombre_libre_propuesto("Nuevo perfil", {"Nuevo perfil"}) == "Nuevo perfil 2"


def _botones_catalogo(dlg):
    return (
        dlg.btn_nuevo,
        dlg.btn_aplicar,
        dlg.btn_duplicar,
        dlg.btn_renombrar,
        dlg.btn_eliminar,
        dlg.btn_cerrar,
    )


def _altura_geometry(dlg) -> int:
    # "640x560+10+10" o "640x560-0-0"
    return int(str(dlg.geometry()).split("x")[1].split("+")[0].split("-")[0])


@pytest.mark.gui
@pytest.mark.integration
def test_botones_catalogo_visibles_y_apilados(tmp_path) -> None:
    if not os.environ.get("DISPLAY"):
        pytest.skip("sin DISPLAY")

    _tk, root, app = _arrancar(tmp_path)
    try:
        app.btn_gestionar_perfiles.invoke()
        root.update()
        dlg = app.ventana_perfiles
        assert dlg is not None
        dlg.update_idletasks()

        izq = dlg.winfo_rootx()
        der = izq + dlg.winfo_width()
        top = dlg.winfo_rooty()
        pie = top + dlg.winfo_height()
        arbol_centro = dlg.arbol.winfo_rootx() + dlg.arbol.winfo_width() // 2

        botones = _botones_catalogo(dlg)
        prev_pie = top
        for btn in botones:
            caja = btn.master
            assert btn.winfo_ismapped()
            assert btn.winfo_viewable()
            assert caja.winfo_ismapped()
            assert caja.winfo_width() >= 100
            assert caja.winfo_height() >= 24
            assert btn.winfo_width() >= 90
            assert btn.winfo_height() >= 18
            assert caja.winfo_rootx() > arbol_centro
            assert caja.winfo_rootx() >= izq
            assert caja.winfo_rootx() + caja.winfo_width() <= der
            assert caja.winfo_rooty() >= prev_pie
            assert caja.winfo_rooty() + caja.winfo_height() <= pie
            prev_pie = caja.winfo_rooty() + caja.winfo_height()

        assert dlg.btn_cerrar.winfo_rooty() > dlg.btn_eliminar.winfo_rooty()
        assert 500 <= _altura_geometry(dlg) <= 580
    finally:
        root.destroy()


@pytest.mark.gui
@pytest.mark.integration
def test_gestionar_perfiles_catalogo_duplicar_eliminar(tmp_path, monkeypatch) -> None:
    if not os.environ.get("DISPLAY"):
        pytest.skip("sin DISPLAY")

    _tk, root, app = _arrancar(tmp_path)
    try:
        assert app.btn_gestionar_perfiles is not None
        assert "Guardar perfil" not in _textos(app.zona_export)
        assert app.btn_guardar_perfil.winfo_ismapped()
        assert str(app.btn_guardar_perfil.cget("state")) == "disabled"

        app.btn_gestionar_perfiles.invoke()
        root.update()
        dlg = app.ventana_perfiles
        assert dlg is not None
        assert dlg.winfo_ismapped()
        assert int(dlg.wm_overrideredirect() or 0) == 0
        assert dlg.title() == "Gestionar perfiles"
        assert not hasattr(dlg, "btn_editar")
        assert dlg.btn_nuevo is not None
        assert str(dlg.btn_nuevo.cget("state")) == "normal"
        assert dlg.btn_nuevo.winfo_rootx() > dlg.arbol.winfo_rootx() + dlg.arbol.winfo_width() // 2
        assert dlg.btn_aplicar.winfo_rooty() > dlg.btn_nuevo.winfo_rooty()
        assert dlg.winfo_height() >= 500
        assert _altura_geometry(dlg) <= 580

        dlg.seleccionar_nombre("Escanéame")
        root.update()
        assert dlg.frm_marco_texto.winfo_ismapped()
        pie_marco = dlg.lbl_marco.winfo_rooty() + dlg.lbl_marco.winfo_height()
        pie_dlg = dlg.winfo_rooty() + dlg.winfo_height()
        assert pie_marco <= pie_dlg

        hojas_fabrica = [dlg.arbol.item(i, "text") for i in dlg.arbol.get_children(dlg.IID_FABRICA)]
        assert set(hojas_fabrica) >= {"Clásico", "Redondeado", "Puntos", "Escanéame", "Barras"}

        dlg.seleccionar_nombre("Puntos")
        root.update()
        assert "puntos" in dlg.lbl_modulo.cget("text")
        assert str(dlg.btn_eliminar.cget("state")) == "disabled"
        assert dlg.canvas_muestra.find_all()

        monkeypatch.setattr(
            "qr_designer.ui.perfiles_dialog.simpledialog.askstring",
            lambda *_a, **_k: "Mia",
        )
        dlg.btn_duplicar.invoke()
        root.update()
        hojas_user = [dlg.arbol.item(i, "text") for i in dlg.arbol.get_children(dlg.IID_USUARIO)]
        assert "Mia" in hojas_user
        assert any(p.nombre == "Mia" for p in app.vm.gestor.listar())

        dlg.seleccionar_nombre("Mia")
        root.update()
        assert str(dlg.btn_eliminar.cget("state")) == "normal"

        monkeypatch.setattr(
            "qr_designer.ui.perfiles_dialog.simpledialog.askstring",
            lambda *_a, **_k: "Copia",
        )
        dlg.seleccionar_nombre("Puntos")
        root.update()
        dlg.btn_duplicar.invoke()
        root.update()
        assert any(p.nombre == "Copia" for p in app.vm.gestor.listar())

        dlg.seleccionar_nombre("Copia")
        root.update()
        monkeypatch.setattr(
            "qr_designer.ui.perfiles_dialog.messagebox.askyesno",
            lambda *_a, **_k: True,
        )
        dlg.btn_eliminar.invoke()
        root.update()
        assert all(p.nombre != "Copia" for p in app.vm.gestor.listar())

        dlg.seleccionar_nombre("Mia")
        root.update()
        dlg.btn_eliminar.invoke()
        root.update()
        assert app.vm.gestor.listar() == []

        dlg.seleccionar_nombre("Puntos")
        app.vm.set_modulo(app.vm.perfil.modulo_estilo)
        app.vm.modificado = True
        monkeypatch.setattr(
            "qr_designer.ui.perfiles_dialog.messagebox.askyesno",
            lambda *_a, **_k: False,
        )
        origen = app.vm.perfil_origen
        dlg.btn_aplicar.invoke()
        root.update()
        assert app.vm.perfil_origen == origen

        dlg.btn_cerrar.invoke()
        root.update()
        assert app.ventana_perfiles is None
        assert "Clásico" in app.combo_perfil.cget("values")
    finally:
        root.destroy()


@pytest.mark.gui
@pytest.mark.integration
def test_aplicar_cierra_el_dialogo(tmp_path) -> None:
    if not os.environ.get("DISPLAY"):
        pytest.skip("sin DISPLAY")

    _tk, root, app = _arrancar(tmp_path)
    try:
        app.btn_gestionar_perfiles.invoke()
        root.update()
        dlg = app.ventana_perfiles
        assert dlg is not None
        dlg.seleccionar_nombre("Puntos")
        root.update()
        dlg.btn_aplicar.invoke()
        root.update()
        assert app.ventana_perfiles is None
        assert app.vm.perfil_origen == "Puntos"
        assert app.var_perfil.get() == "Puntos"
    finally:
        root.destroy()


@pytest.mark.gui
@pytest.mark.integration
def test_nuevo_perfil_aplica_y_cierra(tmp_path, monkeypatch) -> None:
    if not os.environ.get("DISPLAY"):
        pytest.skip("sin DISPLAY")

    from qr_designer.config.presets import preset_clasico

    _tk, root, app = _arrancar(tmp_path)
    try:
        origen = app.vm.perfil_origen
        app.btn_gestionar_perfiles.invoke()
        root.update()
        dlg = app.ventana_perfiles
        assert dlg is not None
        monkeypatch.setattr(
            "qr_designer.ui.perfiles_dialog.simpledialog.askstring",
            lambda *_a, **_k: "Mia",
        )
        dlg.btn_nuevo.invoke()
        root.update()
        assert app.ventana_perfiles is None
        assert app.vm.perfil_origen == "Mia"
        assert app.vm.perfil_origen != origen
        mia = app.vm.gestor.obtener("Mia")
        clasico = preset_clasico()
        assert mia.modulo_estilo is clasico.modulo_estilo
        assert mia.ojo_estilo is clasico.ojo_estilo
        assert "Mia" in app.combo_perfil.cget("values")
        assert app.var_perfil.get() == "Mia"
    finally:
        root.destroy()


@pytest.mark.gui
@pytest.mark.integration
def test_guardar_perfil_confirma_overwrite_usuario(tmp_path, monkeypatch) -> None:
    if not os.environ.get("DISPLAY"):
        pytest.skip("sin DISPLAY")

    from qr_designer.config.models import ModuloEstilo

    _tk, root, app = _arrancar(tmp_path)
    try:
        assert str(app.btn_guardar_perfil.cget("state")) == "disabled"
        app.vm.guardar_perfil("Mia")
        app.vm.aplicar_perfil("Mia")
        app._sync()
        root.update()
        assert str(app.btn_guardar_perfil.cget("state")) == "disabled"

        app.vm.set_modulo(ModuloEstilo.PUNTOS)
        app._sync()
        root.update()
        assert str(app.btn_guardar_perfil.cget("state")) == "normal"

        monkeypatch.setattr(
            "qr_designer.ui.gui.messagebox.askyesno",
            lambda *_a, **_k: False,
        )
        app.btn_guardar_perfil.invoke()
        root.update()
        assert app.vm.modificado
        assert app.vm.gestor.obtener("Mia").modulo_estilo is not ModuloEstilo.PUNTOS

        monkeypatch.setattr(
            "qr_designer.ui.gui.messagebox.askyesno",
            lambda *_a, **_k: True,
        )
        app.btn_guardar_perfil.invoke()
        root.update()
        assert not app.vm.modificado
        assert app.vm.gestor.obtener("Mia").modulo_estilo is ModuloEstilo.PUNTOS
        assert str(app.btn_guardar_perfil.cget("state")) == "disabled"
    finally:
        root.destroy()


@pytest.mark.gui
@pytest.mark.integration
def test_guardar_preset_modificado_pide_nombre(tmp_path, monkeypatch) -> None:
    if not os.environ.get("DISPLAY"):
        pytest.skip("sin DISPLAY")

    from qr_designer.config.models import ModuloEstilo
    from qr_designer.config.presets import preset_clasico

    _tk, root, app = _arrancar(tmp_path)
    try:
        assert app.vm.perfil_origen == "Clásico"
        assert str(app.btn_guardar_perfil.cget("state")) == "disabled"

        app.vm.set_modulo(ModuloEstilo.PUNTOS)
        app._sync()
        root.update()
        assert str(app.btn_guardar_perfil.cget("state")) == "normal"

        def no_yesno(*_a, **_k):
            raise AssertionError("askyesno no debe llamarse al guardar un preset")

        monkeypatch.setattr("qr_designer.ui.gui.messagebox.askyesno", no_yesno)
        monkeypatch.setattr(
            "qr_designer.ui.gui.simpledialog.askstring",
            lambda *_a, **_k: "Mia",
        )
        app.btn_guardar_perfil.invoke()
        root.update()
        assert app.vm.perfil_origen == "Mia"
        assert not app.vm.modificado
        mia = app.vm.gestor.obtener("Mia")
        assert mia.modulo_estilo is ModuloEstilo.PUNTOS
        assert mia.modulo_estilo is not preset_clasico().modulo_estilo
        assert "Mia" in app.combo_perfil.cget("values")
        assert str(app.btn_guardar_perfil.cget("state")) == "disabled"
    finally:
        root.destroy()


@pytest.mark.gui
@pytest.mark.integration
def test_guardar_preset_cancelar_no_escribe(tmp_path, monkeypatch) -> None:
    if not os.environ.get("DISPLAY"):
        pytest.skip("sin DISPLAY")

    from qr_designer.config.models import ModuloEstilo

    _tk, root, app = _arrancar(tmp_path)
    try:
        app.vm.set_modulo(ModuloEstilo.PUNTOS)
        app._sync()
        root.update()
        monkeypatch.setattr(
            "qr_designer.ui.gui.simpledialog.askstring",
            lambda *_a, **_k: None,
        )
        app.btn_guardar_perfil.invoke()
        root.update()
        assert app.vm.modificado
        assert app.vm.perfil_origen == "Clásico"
        assert app.vm.gestor.listar() == []
    finally:
        root.destroy()
