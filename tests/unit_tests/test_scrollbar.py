"""Comportamiento de la barra de desplazamiento custom."""

from __future__ import annotations

import os

import pytest


def _barra_con_lienzo():
    tk = pytest.importorskip("tkinter")
    if not os.environ.get("DISPLAY"):
        pytest.skip("sin DISPLAY")
    try:
        root = tk.Tk()
        root.withdraw()
    except tk.TclError as exc:
        pytest.skip(f"tkinter no disponible: {exc}")

    from qr_designer.ui.gui import _BarraDesplazamiento

    root.geometry("240x220")
    root.deiconify()
    canvas = tk.Canvas(root, width=200, height=200, highlightthickness=0)
    inner = tk.Frame(canvas, width=200, height=800)
    inner.pack_propagate(False)
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(scrollregion=(0, 0, 200, 800), yscrollincrement=20)
    bar = _BarraDesplazamiento(root, command=canvas.yview, ancho=14)
    canvas.configure(yscrollcommand=bar.set)
    canvas.pack(side="left", fill="y")
    bar.pack(side="right", fill="y")
    root.update()
    canvas.yview_moveto(0.0)
    root.update()
    return tk, root, canvas, bar


@pytest.mark.gui
@pytest.mark.unit
def test_click_en_thumb_no_salta_el_contenido() -> None:
    _tk, root, canvas, bar = _barra_con_lienzo()
    try:
        first0, last0 = (float(x) for x in canvas.yview())
        assert last0 < 1.0

        y0, y1, _thumb_h, _rec = bar._geometria()
        assert y1 - y0 > 20
        click_y = int(y1 - 8)
        bar.event_generate("<ButtonPress-1>", x=7, y=click_y)
        root.update()

        first1, _last1 = (float(x) for x in canvas.yview())
        assert first1 == pytest.approx(first0, abs=0.04)
    finally:
        root.destroy()


@pytest.mark.gui
@pytest.mark.unit
def test_arrastrar_thumb_desplaza_proporcionalmente() -> None:
    _tk, root, canvas, bar = _barra_con_lienzo()
    try:
        y0, y1, _thumb_h, recorrido = bar._geometria()
        mid = int((y0 + y1) / 2)
        bar.event_generate("<ButtonPress-1>", x=7, y=mid)
        root.update()
        destino = int(mid + min(40, max(recorrido * 0.25, 20)))
        bar.event_generate("<B1-Motion>", x=7, y=destino)
        root.update()

        first, last = (float(x) for x in canvas.yview())
        assert first > 0.04
        assert first < 0.55
        assert last < 1.0 or first < 0.8
    finally:
        root.destroy()
