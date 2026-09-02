"""Diálogo con rueda HSV, brillo, opacidad y campos RGBA. Persiste solo RGB."""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from qr_designer.ui.color_math import (
    clamp_byte,
    hex_a_rgba,
    hsv_a_rgb,
    hsv_en_rueda,
    rgb_a_hsv,
    rgba_a_hex,
)
from qr_designer.ui.theme import BORDE, FONDO
from qr_designer.ui.redondeo import CajaRedonda

OnRgb = Callable[[str], None]
OnCerrar = Callable[[], None]

RUEDA_LADO = 140
_TITULO_CAMPO = {
    "fondo": "fondo",
    "modulos": "módulos",
    "ojos": "ojos",
    "marco": "marco",
}


class SelectorColor(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        campo: str,
        color: str,
        on_rgb: OnRgb | None = None,
        on_cerrar: OnCerrar | None = None,
    ) -> None:
        super().__init__(master)
        self.campo = campo
        self.title(f"Color {_TITULO_CAMPO.get(campo, campo)}")
        self.configure(bg=FONDO)
        self._on_rgb = on_rgb
        self._on_cerrar = on_cerrar
        self._silencio = False
        r, g, b, a = hex_a_rgba(color)
        self._h, self._s, self._v = rgb_a_hsv(r, g, b)
        self._a = a
        self._radio = RUEDA_LADO // 2
        self._img_rueda: tk.PhotoImage | None = None
        self.var_r = tk.StringVar()
        self.var_g = tk.StringVar()
        self.var_b = tk.StringVar()
        self.var_a = tk.StringVar()
        self.var_valor = tk.DoubleVar(value=self._v)
        self.var_alfa_scale = tk.DoubleVar(value=float(self._a))
        try:
            self.transient(master.winfo_toplevel())
        except tk.TclError:
            pass
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.bind("<Escape>", lambda _e: self._cerrar())
        self.minsize(320, 260)
        self.resizable(False, False)

        cuerpo = ttk.Frame(self, padding=12)
        cuerpo.pack(fill=tk.BOTH, expand=True)

        fila = ttk.Frame(cuerpo)
        fila.pack(fill=tk.X)
        self.canvas_rueda = tk.Canvas(
            fila,
            width=RUEDA_LADO,
            height=RUEDA_LADO,
            bg=FONDO,
            highlightthickness=1,
            highlightbackground=BORDE,
            bd=0,
        )
        self.canvas_rueda.pack(side=tk.LEFT)
        self.canvas_rueda.bind("<Button-1>", self._clic_rueda)
        self.canvas_rueda.bind("<B1-Motion>", self._clic_rueda)

        sliders = ttk.Frame(fila)
        sliders.pack(side=tk.LEFT, fill=tk.Y, padx=(12, 0))
        ttk.Label(sliders, text="Brillo").pack(anchor=tk.W)
        self.scale_valor = ttk.Scale(
            sliders,
            from_=0.0,
            to=1.0,
            variable=self.var_valor,
            length=RUEDA_LADO,
        )
        self.scale_valor.pack(anchor=tk.W, pady=(0, 8))
        ttk.Label(sliders, text="Opacidad").pack(anchor=tk.W)
        self.scale_alfa = ttk.Scale(
            sliders,
            from_=0.0,
            to=255.0,
            variable=self.var_alfa_scale,
            length=RUEDA_LADO,
        )
        self.scale_alfa.pack(anchor=tk.W)
        self.canvas_chip = tk.Canvas(
            sliders, width=48, height=24, highlightthickness=1, highlightbackground=BORDE, bd=0
        )
        self.canvas_chip.pack(anchor=tk.W, pady=(8, 0))

        rgba = ttk.Frame(cuerpo)
        rgba.pack(fill=tk.X, pady=(12, 0))
        for etiqueta, var in (("R", self.var_r), ("G", self.var_g), ("B", self.var_b), ("A", self.var_a)):
            caja = ttk.Frame(rgba)
            caja.pack(side=tk.LEFT, padx=(0, 8))
            ttk.Label(caja, text=etiqueta).pack(anchor=tk.W)
            cromo = CajaRedonda(caja)
            ent = ttk.Entry(cromo, textvariable=var, width=4)
            cromo.alojar(ent)
            cromo.pack(anchor=tk.W)

        caja_cerrar = CajaRedonda(cuerpo, fondo=BORDE, borde=BORDE)
        self.btn_cerrar = ttk.Button(caja_cerrar, text="Cerrar", command=self._cerrar)
        caja_cerrar.alojar(self.btn_cerrar)
        caja_cerrar.pack(anchor=tk.E, pady=(12, 0))

        self.var_r.trace_add("write", self._on_rgba_var)
        self.var_g.trace_add("write", self._on_rgba_var)
        self.var_b.trace_add("write", self._on_rgba_var)
        self.var_a.trace_add("write", self._on_rgba_var)
        self.scale_valor.configure(command=self._on_valor)
        self.scale_alfa.configure(command=self._on_alfa_scale)

        self._refrescar_desde_hsv(emitir=False)
        self.update_idletasks()

    def aplicar_rgba(self, r: int, g: int, b: int, a: int | None = None) -> None:
        if a is not None:
            self._a = clamp_byte(a)
        self._h, self._s, self._v = rgb_a_hsv(r, g, b)
        self._refrescar_desde_hsv(emitir=True)

    def _byte_de(self, var: tk.StringVar) -> int:
        crudo = var.get().strip()
        if not crudo:
            return 0
        try:
            return clamp_byte(int(float(crudo)))
        except ValueError:
            return 0

    def _on_rgba_var(self, *_args) -> None:
        if self._silencio:
            return
        r, g, b = self._byte_de(self.var_r), self._byte_de(self.var_g), self._byte_de(self.var_b)
        self._a = self._byte_de(self.var_a)
        self._h, self._s, self._v = rgb_a_hsv(r, g, b)
        self._silencio = True
        try:
            self.var_valor.set(self._v)
            self.var_alfa_scale.set(float(self._a))
        finally:
            self._silencio = False
        self._pintar_rueda()
        self._pintar_marcador()
        self._pintar_chip()
        self._emitir(r, g, b)

    def _on_valor(self, _val: str | None = None) -> None:
        if self._silencio:
            return
        self._v = max(0.0, min(1.0, float(self.var_valor.get())))
        r, g, b = hsv_a_rgb(self._h, self._s, self._v)
        self._silencio = True
        try:
            self.var_r.set(str(r))
            self.var_g.set(str(g))
            self.var_b.set(str(b))
        finally:
            self._silencio = False
        self._pintar_rueda()
        self._pintar_marcador()
        self._pintar_chip()
        self._emitir(r, g, b)

    def _on_alfa_scale(self, _val: str | None = None) -> None:
        if self._silencio:
            return
        self._a = clamp_byte(float(self.var_alfa_scale.get()))
        self._silencio = True
        try:
            self.var_a.set(str(self._a))
        finally:
            self._silencio = False
        self._pintar_chip()

    def _clic_rueda(self, event) -> None:
        hs = hsv_en_rueda(event.x - self._radio, event.y - self._radio, self._radio)
        if hs is None:
            return
        self._h, self._s = hs
        r, g, b = hsv_a_rgb(self._h, self._s, self._v)
        self._silencio = True
        try:
            self.var_r.set(str(r))
            self.var_g.set(str(g))
            self.var_b.set(str(b))
        finally:
            self._silencio = False
        self._pintar_marcador()
        self._pintar_chip()
        self._emitir(r, g, b)

    def _refrescar_desde_hsv(self, emitir: bool) -> None:
        r, g, b = hsv_a_rgb(self._h, self._s, self._v)
        self._silencio = True
        try:
            self.var_r.set(str(r))
            self.var_g.set(str(g))
            self.var_b.set(str(b))
            self.var_a.set(str(self._a))
            self.var_valor.set(self._v)
            self.var_alfa_scale.set(float(self._a))
        finally:
            self._silencio = False
        self._pintar_rueda()
        self._pintar_marcador()
        self._pintar_chip()
        if emitir:
            self._emitir(r, g, b)

    def _pintar_rueda(self) -> None:
        lado = self._radio * 2
        img = tk.PhotoImage(width=lado, height=lado, master=self)
        fondo = FONDO
        for y in range(lado):
            cy = y - self._radio
            partes: list[str] = []
            for x in range(lado):
                hs = hsv_en_rueda(x - self._radio, cy, self._radio)
                if hs is None:
                    partes.append(fondo)
                    continue
                h, s = hs
                r, g, b = hsv_a_rgb(h, s, self._v)
                partes.append(f"#{r:02x}{g:02x}{b:02x}")
            img.put("{" + " ".join(partes) + "}", to=(0, y))
        self._img_rueda = img
        self.canvas_rueda.delete("rueda")
        self.canvas_rueda.create_image(0, 0, image=img, anchor="nw", tags=("rueda",))

    def _pintar_marcador(self) -> None:
        ang = self._h * 2 * math.pi
        dist = self._s * self._radio
        cx = self._radio + dist * math.cos(ang)
        cy = self._radio - dist * math.sin(ang)
        self.canvas_rueda.delete("marcador")
        r = 5
        self.canvas_rueda.create_oval(
            cx - r, cy - r, cx + r, cy + r, outline="#ffffff", width=2, tags=("marcador",)
        )
        self.canvas_rueda.create_oval(
            cx - r, cy - r, cx + r, cy + r, outline="#000000", width=1, tags=("marcador",)
        )

    def _pintar_chip(self) -> None:
        c = self.canvas_chip
        c.delete("all")
        w, h = 48, 24
        celda = 6
        claro, oscuro = "#d0d0d0", "#888888"
        for iy in range(0, h, celda):
            for ix in range(0, w, celda):
                fill = claro if (ix // celda + iy // celda) % 2 == 0 else oscuro
                c.create_rectangle(ix, iy, ix + celda, iy + celda, fill=fill, outline="")
        r, g, b = hsv_a_rgb(self._h, self._s, self._v)
        t = self._a / 255.0
        br = clamp_byte(r * t + 208 * (1 - t))
        bg = clamp_byte(g * t + 208 * (1 - t))
        bb = clamp_byte(b * t + 208 * (1 - t))
        c.create_rectangle(0, 0, w, h, fill=f"#{br:02x}{bg:02x}{bb:02x}", outline=BORDE, stipple="")
        # Capa opaca a la izquierda, mezcla a la derecha según A
        c.create_rectangle(0, 0, w // 2, h, fill=f"#{r:02x}{g:02x}{b:02x}", outline="")

    def _emitir(self, r: int, g: int, b: int) -> None:
        if self._on_rgb is None:
            return
        self._on_rgb(rgba_a_hex(r, g, b, self._a))

    def _cerrar(self) -> None:
        cb = self._on_cerrar
        self._on_cerrar = None
        if cb is not None:
            cb()
        try:
            self.destroy()
        except tk.TclError:
            return
