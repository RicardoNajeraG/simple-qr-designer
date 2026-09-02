"""Marcos y cromo de controles con esquinas redondeadas."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from qr_designer.ui.theme import ACENTO, BORDE, FONDO, MARCO_PREVIEW, SUPERFICIE

RADIO_MARCO = 14
RADIO_CONTROL = 8
GROSOR_MARCO = 1


def dibujar_rect_redondeado(
    canvas: tk.Canvas,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    radio: float,
    fill: str,
    outline: str | None = None,
    grosor: int = 1,
    tags: tuple[str, ...] = (),
) -> None:
    """Rellena un rectángulo redondeado; el borde es un anillo del mismo radio."""
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return
    r = min(float(radio), w / 2, h / 2)
    if outline and grosor > 0:
        _capsula_llena(canvas, x0, y0, x1, y1, r, outline, tags)
        inner = grosor
        _capsula_llena(
            canvas,
            x0 + inner,
            y0 + inner,
            x1 - inner,
            y1 - inner,
            max(1.0, r - inner),
            fill,
            tags,
        )
    else:
        _capsula_llena(canvas, x0, y0, x1, y1, r, fill, tags)


def _capsula_llena(
    canvas: tk.Canvas,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    r: float,
    fill: str,
    tags: tuple[str, ...],
) -> None:
    r = max(1.0, r)
    kw = {"fill": fill, "outline": fill, "tags": tags}
    canvas.create_arc(x0, y0, x0 + 2 * r, y0 + 2 * r, start=90, extent=90, **kw)
    canvas.create_arc(x1 - 2 * r, y0, x1, y0 + 2 * r, start=0, extent=90, **kw)
    canvas.create_arc(x1 - 2 * r, y1 - 2 * r, x1, y1, start=270, extent=90, **kw)
    canvas.create_arc(x0, y1 - 2 * r, x0 + 2 * r, y1, start=180, extent=90, **kw)
    canvas.create_rectangle(x0 + r, y0, x1 - r, y1, fill=fill, outline="", tags=tags)
    canvas.create_rectangle(x0, y0 + r, x1, y1 - r, fill=fill, outline="", tags=tags)


class MarcoRedondeado(tk.Canvas):
    """Lienzo con borde redondeado e `inner` para el contenido."""

    def __init__(
        self,
        parent: tk.Misc,
        radio: int = RADIO_MARCO,
        borde: str = MARCO_PREVIEW,
        fondo: str = FONDO,
        grosor: int = GROSOR_MARCO,
        **kwargs,
    ) -> None:
        super().__init__(
            parent,
            highlightthickness=0,
            bd=0,
            bg=FONDO,
            **kwargs,
        )
        self.radio = radio
        self.borde = borde
        self.fondo_interior = fondo
        self.grosor = grosor
        self.inner = ttk.Frame(self)
        pad = grosor + 3
        self._win = self.create_window(pad, pad, window=self.inner, anchor="nw")
        self.bind("<Configure>", self._redibujar)
        self.bind("<Map>", lambda _e: self.after_idle(self._redibujar))
        self.after_idle(self._redibujar)

    def _redibujar(self, event=None) -> None:
        if event is not None and str(event.widget) != str(self):
            return
        w = self.winfo_width()
        h = self.winfo_height()
        if event is not None:
            w, h = max(w, int(event.width)), max(h, int(event.height))
        if w < 8 or h < 8:
            return
        self.delete("rr")
        dibujar_rect_redondeado(
            self, 1, 1, w - 1, h - 1, self.radio, self.fondo_interior, self.borde, self.grosor, ("rr",)
        )
        pad = self.grosor + 3
        self.coords(self._win, pad, pad)
        self.itemconfigure(self._win, width=max(1, w - 2 * pad), height=max(1, h - 2 * pad))
        self.tag_lower("rr")


class CajaRedonda(tk.Canvas):
    """Cromo redondeado alrededor de un Entry, Combobox, Spinbox o Button."""

    PAD = 3

    def __init__(
        self,
        parent: tk.Misc,
        radio: int = RADIO_CONTROL,
        borde: str = BORDE,
        fondo: str = SUPERFICIE,
        **kwargs,
    ) -> None:
        super().__init__(
            parent,
            highlightthickness=0,
            bd=0,
            bg=FONDO,
            **kwargs,
        )
        self.radio = radio
        self.borde = borde
        self.fondo_interior = fondo
        self._hijo: tk.Misc | None = None
        self._win: int | None = None
        self._expandir = False
        self.bind("<Configure>", self._redibujar)
        self.bind("<Map>", lambda _e: self.after_idle(self._redibujar))

    def alojar(self, widget: tk.Misc, expandir: bool = False) -> None:
        self._hijo = widget
        self._expandir = expandir
        pad = self.PAD
        self._win = self.create_window(pad, pad, window=widget, anchor="nw")
        widget.bind("<Configure>", lambda _e: self._ajustar_si_hace_falta(), add="+")
        self._ajustar_si_hace_falta()
        self._redibujar()

    def _ajustar_si_hace_falta(self) -> None:
        if self._hijo is None:
            return
        try:
            rw = int(self._hijo.winfo_reqwidth())
            rh = int(self._hijo.winfo_reqheight())
        except tk.TclError:
            return
        self.configure(height=rh + 2 * self.PAD)
        if self._expandir:
            # Entero pequeño: el geom. manager estira el cromo; "10c" infla el reqwidth.
            self.configure(width=8)
        else:
            self.configure(width=max(rw + 2 * self.PAD + 4, 8))

    def _redibujar(self, event=None) -> None:
        if event is not None and str(event.widget) != str(self):
            return
        if event is not None and event.width >= 4:
            w, h = int(event.width), int(event.height)
        else:
            w, h = self.winfo_width(), self.winfo_height()
            if w < 4:
                w = max(int(self.winfo_reqwidth() or 4), 4)
            if h < 4:
                h = max(int(self.winfo_reqheight() or 4), 4)
        self.delete("rr")
        dibujar_rect_redondeado(
            self, 0.5, 0.5, w - 0.5, h - 0.5, self.radio, self.fondo_interior, self.borde, 1, ("rr",)
        )
        if self._win is not None:
            pad = self.PAD
            self.coords(self._win, pad, pad)
            self.itemconfigure(
                self._win,
                width=max(1, w - 2 * pad),
                height=max(1, h - 2 * pad),
            )
        self.tag_lower("rr")

    def set_borde(self, borde: str) -> None:
        self.borde = borde
        self._redibujar()

    @property
    def presionado(self) -> bool:
        return self.borde == ACENTO


def envolver(
    parent: tk.Misc,
    widget: tk.Misc,
    *,
    expandir: bool = False,
    radio: int = RADIO_CONTROL,
    borde: str = BORDE,
    fondo: str = SUPERFICIE,
) -> CajaRedonda:
    caja = CajaRedonda(parent, radio=radio, borde=borde, fondo=fondo)
    caja.alojar(widget, expandir=expandir)
    return caja
