"""Esquinas redondeadas: geometría de dibujo."""

from __future__ import annotations

import pytest

from qr_designer.ui.redondeo import (
    RADIO_CONTROL,
    RADIO_MARCO,
    CajaRedonda,
    MarcoRedondeado,
    dibujar_rect_redondeado,
)


@pytest.mark.unit
def test_radios_de_redondeo() -> None:
    assert RADIO_MARCO >= 8
    assert RADIO_CONTROL >= 6


@pytest.mark.unit
def test_dibujar_rect_redondeado_crea_items() -> None:
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError as exc:
        pytest.skip(f"tkinter no disponible: {exc}")
    try:
        c = tk.Canvas(root, width=80, height=40)
        dibujar_rect_redondeado(c, 1, 1, 79, 39, 10, "#ffffff", "#7a5aa6", 1, ("rr",))
        assert c.find_withtag("rr")

        root.deiconify()
        m = MarcoRedondeado(root)
        m.pack()
        m.configure(width=120, height=80)
        root.update()
        m._redibujar()
        assert m.find_withtag("rr")
    finally:
        root.destroy()


@pytest.mark.unit
def test_caja_no_colapsa_ancho_del_hijo() -> None:
    tk = pytest.importorskip("tkinter")
    from tkinter import ttk

    try:
        root = tk.Tk()
        root.geometry("320x200")
    except tk.TclError as exc:
        pytest.skip(f"tkinter no disponible: {exc}")
    try:
        col = ttk.Frame(root)
        col.pack(anchor="ne")
        caja = CajaRedonda(col)
        btn = ttk.Button(caja, text="Nuevo perfil")
        caja.alojar(btn)
        caja.pack(fill=tk.X, pady=4)
        root.update()
        assert caja.winfo_reqwidth() >= btn.winfo_reqwidth()
        assert caja.winfo_width() >= 80
        assert btn.winfo_width() >= 70
        assert btn.winfo_ismapped()
    finally:
        root.destroy()
