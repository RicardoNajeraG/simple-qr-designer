"""GUI tkinter: tema del mapache, paned layout, preview raster."""

from __future__ import annotations

import base64
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk

from qr_designer.config.models import Correccion, MarcoTipo, ModuloEstilo, OjoEstilo
from qr_designer.config.profiles import PerfilError
from qr_designer.export.paths import filetypes_para, resolver_export
from qr_designer.render.canvas import pintar_canvas
from qr_designer.render.preview import px_para_preview
from qr_designer.ui.acerca import VentanaAcerca
from qr_designer.ui.theme import (
    ACENTO,
    AYUDA_ICONO,
    BANNER_HEADER,
    BORDE,
    FONDO,
    GRIS,
    MARCO_PREVIEW,
    PET_HEADER,
    SCRAPING_FONDO,
    SCROLL_THUMB,
    SCROLL_TROUGH,
    SUPERFICIE,
    aplicar_tema,
    cargar_icono,
    cargar_png,
)
from qr_designer.ui.viewmodel import ViewModel

PREVIEW_LADO = 400
PREVIEW_PAD = 12
SIDEBAR_ANCHO = 320
COMBO_ANCHO = 16
PAD = 16
HINT_CONTENIDO = "Pega una URL o escribe un texto"
SWATCHES = (
    "#000000",
    "#ffffff",
    "#2b2724",
    "#8a8580",
    "#e0708a",
    "#b56a2b",
    "#3d2914",
    "#0b3d91",
)


class ProgramadorTk:
    def __init__(self, root: tk.Misc) -> None:
        self.root = root

    def programar(self, ms: int, callback) -> object:
        return self.root.after(ms, callback)

    def cancelar(self, handle: object) -> None:
        try:
            self.root.after_cancel(handle)  # type: ignore[arg-type]
        except Exception:
            return


class _BarraDesplazamiento(tk.Canvas):
    """Barra vertical dibujada: canal claro y thumb violeta, sin flechas."""

    PAD_X = 3
    PAD_Y = 4
    THUMB_MIN = 32

    def __init__(self, parent: tk.Misc, command, ancho: int = 14) -> None:
        super().__init__(
            parent,
            width=ancho,
            highlightthickness=0,
            bd=0,
            bg=SCROLL_TROUGH,
            cursor="sb_v_double_arrow",
        )
        self._command = command
        self._first = 0.0
        self._last = 1.0
        self._dragging = False
        self._drag_offset = 0.0
        self.bind("<Configure>", lambda _e: self._dibujar())
        self.bind("<ButtonPress-1>", self._click)
        self.bind("<B1-Motion>", self._arrastrar)
        self.bind("<ButtonRelease-1>", self._soltar)

    def set(self, first: str, last: str) -> None:
        self._first = float(first)
        self._last = float(last)
        self._dibujar()

    def _visible(self) -> float:
        return max(min(self._last, 1.0) - max(self._first, 0.0), 0.0)

    def _cabe(self) -> bool:
        return self._visible() >= 0.999

    def _geometria(self) -> tuple[float, float, float, float]:
        """Devuelve (y0, y1, thumb_h, recorrido) del thumb en píxeles."""
        h = max(self.winfo_height(), 1)
        usable = max(h - 2 * self.PAD_Y, 1)
        visible = self._visible()
        if visible >= 0.999:
            return float(self.PAD_Y), float(self.PAD_Y + usable), float(usable), 0.0
        thumb_h = min(max(self.THUMB_MIN, usable * visible), usable)
        recorrido = max(usable - thumb_h, 0.0)
        max_first = max(1.0 - visible, 1e-9)
        ratio = min(1.0, max(0.0, self._first / max_first))
        y0 = self.PAD_Y + ratio * recorrido
        return y0, y0 + thumb_h, thumb_h, recorrido

    def _dibujar(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), int(self.cget("width")))
        y0, y1, _, _ = self._geometria()
        self._capsula(self.PAD_X, y0, w - self.PAD_X, y1, SCROLL_THUMB)

    def _capsula(self, x0: float, y0: float, x1: float, y1: float, fill: str) -> None:
        r = max(1, (x1 - x0) / 2)
        if y1 - y0 <= 2 * r:
            self.create_oval(x0, y0, x1, y1, fill=fill, outline="")
            return
        self.create_oval(x0, y0, x1, y0 + 2 * r, fill=fill, outline="")
        self.create_oval(x0, y1 - 2 * r, x1, y1, fill=fill, outline="")
        self.create_rectangle(x0, y0 + r, x1, y1 - r, fill=fill, outline="")

    def _aplicar_thumb_top(self, y_thumb: float) -> None:
        _y0, _y1, _thumb_h, recorrido = self._geometria()
        if recorrido <= 0:
            self._command("moveto", 0.0)
            return
        ratio = (y_thumb - self.PAD_Y) / recorrido
        ratio = min(1.0, max(0.0, ratio))
        self._command("moveto", ratio * max(1.0 - self._visible(), 0.0))

    def _click(self, event) -> None:
        if self._cabe():
            return
        y0, y1, thumb_h, _recorrido = self._geometria()
        if y0 <= event.y <= y1:
            self._drag_offset = event.y - y0
        else:
            self._drag_offset = thumb_h / 2
            self._aplicar_thumb_top(event.y - self._drag_offset)
        self._dragging = True
        self.grab_set()

    def _arrastrar(self, event) -> None:
        if not self._dragging or self._cabe():
            return
        self._aplicar_thumb_top(event.y - self._drag_offset)

    def _soltar(self, _event) -> None:
        self._dragging = False
        try:
            self.grab_release()
        except tk.TclError:
            return


class _PanelDesplazable(ttk.Frame):
    """Sidebar con scrollbar vertical de canvas, siempre visible."""

    def __init__(self, parent: tk.Misc, ancho: int) -> None:
        super().__init__(parent)
        self.canvas = tk.Canvas(
            self,
            highlightthickness=0,
            width=ancho,
            bg=FONDO,
            bd=0,
            yscrollincrement=24,
        )
        self.vsb = _BarraDesplazamiento(self, command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._bind_rueda(self)
        self._bind_rueda(self.canvas)
        self._bind_rueda(self.vsb)
        self._bind_rueda(self.inner)

    def _on_inner(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._asegurar_rueda(self.inner)

    def _on_canvas(self, event) -> None:
        self.canvas.itemconfigure(self._win, width=event.width)

    def _bind_rueda(self, widget: tk.Misc) -> None:
        if getattr(widget, "_qr_rueda", False):
            return
        widget.bind("<MouseWheel>", self._rueda, add="+")
        widget.bind("<Button-4>", self._rueda, add="+")
        widget.bind("<Button-5>", self._rueda, add="+")
        try:
            widget._qr_rueda = True  # type: ignore[attr-defined]
        except (tk.TclError, AttributeError):
            pass

    def _asegurar_rueda(self, widget: tk.Misc) -> None:
        self._bind_rueda(widget)
        for hijo in widget.winfo_children():
            self._asegurar_rueda(hijo)

    def _rueda(self, event) -> str | None:
        if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
            self.canvas.yview_scroll(-1, "units")
        else:
            self.canvas.yview_scroll(1, "units")
        return "break"


class QRDesignerApp:
    def __init__(self, root: tk.Tk, vm: ViewModel | None = None) -> None:
        self.root = root
        self.root.title("Simple QR Designer")
        aplicar_tema(root)
        self._icono = cargar_icono(root, max_px=64, aplicar_ventana=True)
        self.img_pet = cargar_png(PET_HEADER, master=root)
        self.img_banner = cargar_png(BANNER_HEADER, master=root)
        self.img_scraping = cargar_png(SCRAPING_FONDO, master=root)
        self.img_ayuda = cargar_png(AYUDA_ICONO, master=root)
        self.ventana_acerca: VentanaAcerca | None = None
        self._sash_inicializado = False
        self._preview_photo: tk.PhotoImage | None = None
        self._export_cola: queue.Queue = queue.Queue()
        self._exportando = False
        min_w = SIDEBAR_ANCHO + PREVIEW_LADO + PREVIEW_PAD * 2 + PAD * 4
        min_h = 96 + PREVIEW_LADO + PREVIEW_PAD * 2 + 40 + PAD * 2
        self.root.minsize(min_w, min_h)
        self.root.geometry(f"{max(min_w, 1100)}x{max(min_h, 780)}")
        self.vm = vm or ViewModel(programador=ProgramadorTk(root))
        if not isinstance(self.vm.programador, ProgramadorTk):
            self.vm.programador = ProgramadorTk(root)
        self._silencio = False
        self.vm.on_change = self._sync
        self._build()
        self._refrescar_perfiles()
        self._sync()

    def _build(self) -> None:
        root = self.root
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)

        self._cabecera(root)

        self.paned = ttk.Panedwindow(root, orient=tk.HORIZONTAL)
        self.paned.grid(row=1, column=0, sticky="nsew", padx=PAD, pady=8)

        self.marco_opciones = tk.Frame(
            self.paned,
            bg=FONDO,
            highlightthickness=1,
            highlightbackground=MARCO_PREVIEW,
            highlightcolor=MARCO_PREVIEW,
            bd=0,
        )
        self.panel = _PanelDesplazable(self.marco_opciones, SIDEBAR_ANCHO)
        self.panel.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.panel.inner.bind("<Configure>", self._on_sidebar_ancho, add="+")
        self._controles(self.panel.inner)

        der = ttk.Frame(self.paned)
        der.grid_rowconfigure(1, weight=1)
        der.grid_columnconfigure(0, weight=1)
        ttk.Label(der, text="Vista previa", style="Heading.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.marco_preview = tk.Frame(
            der,
            bg=FONDO,
            highlightthickness=1,
            highlightbackground=MARCO_PREVIEW,
            highlightcolor=MARCO_PREVIEW,
            bd=0,
        )
        self.marco_preview.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.marco_preview.grid_rowconfigure(0, weight=1)
        self.marco_preview.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(
            self.marco_preview,
            width=PREVIEW_LADO,
            height=PREVIEW_LADO,
            bg=SUPERFICIE,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.grid(row=0, column=0, padx=PREVIEW_PAD, pady=PREVIEW_PAD)

        self.paned.add(self.marco_opciones, weight=0)
        self.paned.add(der, weight=1)
        try:
            self.paned.pane(
                der, minsize=PREVIEW_LADO + PREVIEW_PAD * 2 + 8
            )
        except tk.TclError:
            pass
        self.paned.bind("<Map>", lambda _e: self._inicializar_sash(), add="+")
        self.root.after_idle(self._inicializar_sash)

        pie = ttk.Frame(root)
        self.pie = pie
        pie.grid(row=2, column=0, sticky="ew", padx=PAD, pady=(0, PAD))
        if self.img_ayuda is not None:
            self.btn_ayuda = tk.Label(
                pie, image=self.img_ayuda, bg=FONDO, bd=0, cursor="hand2"
            )
        else:
            self.btn_ayuda = tk.Label(
                pie, text="?", bg=FONDO, bd=0, cursor="hand2", fg=ACENTO
            )
        self.var_estado = tk.StringVar(value=HINT_CONTENIDO)
        self.lbl_estado = ttk.Label(
            pie, textvariable=self.var_estado, style="Muted.TLabel"
        )
        self.btn_ayuda.pack(side=tk.RIGHT)
        self.lbl_estado.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.btn_ayuda.bind("<Button-1>", self._toggle_acerca)
        self.root.bind("<Destroy>", lambda _e: self._cerrar_acerca(), add="+")

    def ancho_opciones_inicial(self) -> int:
        """Ancho del panel: fila de swatches + scrollbar, con un mínimo para no colapsar."""
        try:
            self.pal_swatches.update_idletasks()
            self.panel.inner.update_idletasks()
        except tk.TclError:
            pass
        anchos = [
            int(self.pal_swatches.winfo_reqwidth()),
            int(self.pal_swatches.winfo_width()),
        ]
        fila = getattr(self, "fila_color", None)
        if fila is not None:
            anchos.append(int(fila.winfo_reqwidth()))
        sw = max(anchos)
        if sw < 80:
            sw = len(SWATCHES) * 24 + 8
        try:
            barra = max(14, int(self.panel.vsb.winfo_reqwidth() or 14))
        except tk.TclError:
            barra = 14
        return max(sw, 200) + barra + PAD + 10

    def _inicializar_sash(self) -> None:
        if self._sash_inicializado:
            return
        try:
            self.root.update_idletasks()
            ancho = self.ancho_opciones_inicial()
            if ancho < 180:
                self.root.after(50, self._inicializar_sash)
                return
            self.panel.canvas.config(width=max(ancho - 12, 120))
            self.paned.sashpos(0, ancho)
            self._sash_inicializado = True
        except tk.TclError:
            return

    def _on_sidebar_ancho(self, event) -> None:
        if hasattr(self, "lbl_aviso"):
            self.lbl_aviso.config(wraplength=max(120, event.width - 16))

    def _cabecera(self, root: tk.Tk) -> None:
        bar = ttk.Frame(root)
        bar.grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 0))
        self.cabecera = bar
        self.lbl_banner = None
        self.lbl_pet = None
        if self.img_banner is not None:
            self.lbl_banner = tk.Label(bar, image=self.img_banner, bg=FONDO, bd=0)
            self.lbl_banner.pack(side=tk.LEFT)
        if self.img_pet is not None:
            self.lbl_pet = tk.Label(bar, image=self.img_pet, bg=FONDO, bd=0)
            self.lbl_pet.pack(side=tk.RIGHT)

    def _controles(self, izq: ttk.Frame) -> None:
        ttk.Label(izq, text="Contenido", style="Heading.TLabel").pack(anchor=tk.W, pady=(0, 4))
        ttk.Label(izq, text="URL o texto").pack(anchor=tk.W)
        self.var_url = tk.StringVar()
        self.entry_url = self._entrada_90(izq, self.var_url, pady=(0, 10))
        self.var_url.trace_add("write", self._on_url)

        ttk.Label(izq, text="Perfil", style="Heading.TLabel").pack(anchor=tk.W, pady=(8, 4))
        self.var_perfil = tk.StringVar()
        self.combo_perfil = ttk.Combobox(
            izq, textvariable=self.var_perfil, state="readonly", width=COMBO_ANCHO
        )
        self.combo_perfil.pack(anchor=tk.W)
        self.combo_perfil.bind("<<ComboboxSelected>>", self._on_perfil)
        self.lbl_activo = ttk.Label(izq, text="", style="Muted.TLabel")
        self.lbl_activo.pack(anchor=tk.W, pady=(2, 8))

        ttk.Label(izq, text="Estilo", style="Heading.TLabel").pack(anchor=tk.W, pady=(4, 4))
        self.var_modulo = tk.StringVar()
        self.var_ojo = tk.StringVar()
        self.var_marco = tk.StringVar()
        self.combo_modulo = self._combo(
            izq, "Módulos", self.var_modulo, [e.value for e in ModuloEstilo], self._on_modulo
        )
        self._combo(izq, "Ojos", self.var_ojo, [e.value for e in OjoEstilo], self._on_ojo)
        self._combo(izq, "Marco", self.var_marco, [e.value for e in MarcoTipo], self._on_marco)

        self.frm_marco_texto = ttk.Frame(izq)
        ttk.Label(self.frm_marco_texto, text="Texto del marco").pack(anchor=tk.W, pady=(6, 0))
        self.var_marco_texto = tk.StringVar()
        self.entry_marco_texto = self._entrada_90(self.frm_marco_texto, self.var_marco_texto)
        self.var_marco_texto.trace_add("write", self._on_marco_texto)

        self.lbl_colores = ttk.Label(izq, text="Colores", style="Heading.TLabel")
        self.lbl_colores.pack(anchor=tk.W, pady=(12, 4))
        self._colores: dict[str, tk.StringVar] = {}
        for campo, etiqueta in (
            ("fondo", "Fondo"),
            ("modulos", "Módulos"),
            ("ojos", "Ojos"),
            ("marco", "Marco"),
        ):
            self._fila_color(izq, campo, etiqueta)

        self.lbl_aviso = ttk.Label(izq, text="", wraplength=280, style="Aviso.TLabel")
        self.lbl_aviso.pack(anchor=tk.W, pady=8)

        self.var_avanzado = tk.BooleanVar(value=False)
        self.chk_avanzado = ttk.Checkbutton(
            izq,
            text="Avanzado",
            variable=self.var_avanzado,
            command=self._toggle_avanzado,
        )
        self.chk_avanzado.pack(anchor=tk.W)
        self.frm_adv = ttk.Frame(izq)
        ttk.Label(self.frm_adv, text="Corrección de errores").pack(anchor=tk.W)
        self.var_ecc = tk.StringVar()
        self._combo(self.frm_adv, None, self.var_ecc, [e.value for e in Correccion], self._on_ecc)
        ttk.Label(self.frm_adv, text="Píxeles por módulo (PNG/WEBP)").pack(anchor=tk.W)
        self.var_px = tk.IntVar(value=8)
        ttk.Spinbox(self.frm_adv, from_=1, to=32, textvariable=self.var_px, width=6).pack(anchor=tk.W)
        self.lbl_ecc_sug = ttk.Label(self.frm_adv, text="", style="Muted.TLabel")
        self.lbl_ecc_sug.pack(anchor=tk.W)

        self.zona_export = ttk.Frame(izq)
        self.zona_export.pack(fill=tk.X, pady=(14, 4))
        fila_cab_export = ttk.Frame(self.zona_export)
        fila_cab_export.pack(fill=tk.X)
        self.lbl_exportar = ttk.Label(
            fila_cab_export, text="Exportar", style="Heading.TLabel"
        )
        self.lbl_exportar.pack(side=tk.LEFT, anchor=tk.N, pady=(12, 0), padx=(0, 8))
        if self.img_scraping is not None:
            self.lbl_scraping = tk.Label(
                fila_cab_export, image=self.img_scraping, bg=FONDO, bd=0
            )
            self.lbl_scraping.pack(side=tk.RIGHT)
        else:
            self.lbl_scraping = None

        fila_fmt = ttk.Frame(self.zona_export)
        fila_fmt.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(fila_fmt, text="Formato").pack(side=tk.LEFT)
        self.var_formato = tk.StringVar(value="svg")
        ttk.Combobox(
            fila_fmt,
            textvariable=self.var_formato,
            values=("svg", "png", "webp"),
            state="readonly",
            width=8,
        ).pack(side=tk.LEFT, padx=(8, 0))

        btns = ttk.Frame(self.zona_export)
        btns.pack(fill=tk.X, pady=(8, 12))
        ttk.Button(btns, text="Guardar perfil", command=self._guardar).pack(side=tk.LEFT)
        self.btn_exportar = ttk.Button(
            btns,
            text="Exportar imagen",
            command=self._exportar,
            style="Primary.TButton",
        )
        self.btn_exportar.pack(side=tk.LEFT, padx=(8, 0))

    def _combo(self, parent, etiqueta, var, values, handler):
        if etiqueta:
            ttk.Label(parent, text=etiqueta).pack(anchor=tk.W, pady=(4, 0))
        box = ttk.Combobox(
            parent, textvariable=var, values=values, state="readonly", width=COMBO_ANCHO
        )
        box.pack(anchor=tk.W)
        box.bind("<<ComboboxSelected>>", lambda _e: handler())
        return box

    def _entrada_90(self, parent, var, pady: tuple[int, int] | int = 0) -> ttk.Entry:
        fila = ttk.Frame(parent)
        fila.pack(fill=tk.X, pady=pady)
        fila.columnconfigure(0, weight=9)
        fila.columnconfigure(1, weight=1)
        ent = ttk.Entry(fila, textvariable=var)
        ent.grid(row=0, column=0, sticky="ew")
        return ent

    def _actualizar_marco_texto_ui(self) -> None:
        visible = self.var_marco.get() != MarcoTipo.NINGUNO.value
        if visible:
            if str(self.frm_marco_texto.winfo_manager()) != "pack":
                self.frm_marco_texto.pack(fill=tk.X, before=self.lbl_colores)
        else:
            self.frm_marco_texto.pack_forget()

    def _fila_color(self, parent, campo: str, etiqueta: str) -> None:
        fila = ttk.Frame(parent)
        fila.pack(fill=tk.X, pady=2)
        if not hasattr(self, "fila_color"):
            self.fila_color = fila
        ttk.Label(fila, text=etiqueta, width=9).pack(side=tk.LEFT)
        var = tk.StringVar()
        self._colores[campo] = var
        sw = tk.Button(
            fila,
            width=3,
            relief="solid",
            bd=1,
            highlightthickness=0,
            command=lambda c=campo: self._picker(c),
        )
        sw.pack(side=tk.LEFT, padx=4)
        setattr(self, f"_sw_{campo}", sw)
        ent = ttk.Entry(fila, textvariable=var, width=10)
        ent.pack(side=tk.LEFT)
        ent.bind("<Return>", lambda _e, c=campo: self._hex(c))
        ent.bind("<FocusOut>", lambda _e, c=campo: self._hex(c))
        pal = ttk.Frame(parent)
        pal.pack(anchor=tk.W, pady=(0, 4))
        if not hasattr(self, "pal_swatches"):
            self.pal_swatches = pal
        for color in SWATCHES:
            tk.Button(
                pal,
                width=2,
                bg=color,
                activebackground=color,
                relief="solid",
                bd=1,
                highlightbackground=BORDE,
                command=lambda col=color, c=campo: self._swatch(c, col),
            ).pack(side=tk.LEFT, padx=1)

    def _on_url(self, *_args) -> None:
        if self._silencio:
            return
        self.vm.set_url(self.var_url.get())

    def _on_perfil(self, _e=None) -> None:
        if self._silencio:
            return
        nombre = self.var_perfil.get()
        if nombre:
            self.vm.aplicar_perfil(nombre)

    def _on_modulo(self) -> None:
        if self._silencio:
            return
        self.vm.set_modulo(ModuloEstilo(self.var_modulo.get()))

    def _on_ojo(self) -> None:
        if self._silencio:
            return
        self.vm.set_ojo(OjoEstilo(self.var_ojo.get()))

    def _on_marco(self) -> None:
        if not self._silencio:
            self.vm.set_marco(MarcoTipo(self.var_marco.get()))
        self._actualizar_marco_texto_ui()

    def _on_marco_texto(self, *_args) -> None:
        if self._silencio:
            return
        self.vm.set_marco_texto(self.var_marco_texto.get())

    def _on_ecc(self) -> None:
        if self._silencio:
            return
        self.vm.set_correccion(Correccion(self.var_ecc.get()))

    def _swatch(self, campo: str, color: str) -> None:
        self.vm.set_color(campo, color)

    def _hex(self, campo: str) -> None:
        if self._silencio:
            return
        try:
            self.vm.set_color(campo, self._colores[campo].get())
        except Exception as exc:
            self.var_estado.set(str(exc))

    def _picker(self, campo: str) -> None:
        actual = self.vm.perfil.colores.to_dict()[campo]
        elegido = colorchooser.askcolor(color=actual, title=f"Color {campo}")
        if elegido and elegido[1]:
            self.vm.set_color(campo, elegido[1])

    def _toggle_acerca(self, _event=None) -> None:
        if self.ventana_acerca is not None:
            self._cerrar_acerca()
            return
        self.ventana_acerca = VentanaAcerca(self.root, on_cerrar=self._acerca_cerrada)

    def _acerca_cerrada(self) -> None:
        self.ventana_acerca = None

    def _cerrar_acerca(self) -> None:
        if self.ventana_acerca is None:
            return
        win = self.ventana_acerca
        self.ventana_acerca = None
        try:
            win._on_cerrar = None
            win.destroy()
        except tk.TclError:
            return

    def _toggle_avanzado(self) -> None:
        self.vm.avanzado_colapsado = not self.var_avanzado.get()
        if self.var_avanzado.get():
            self.frm_adv.pack(fill=tk.X, pady=4, before=self.zona_export)
        else:
            self.frm_adv.pack_forget()

    def _refrescar_perfiles(self) -> None:
        nombres = [p.nombre for p in self.vm.gestor.listar_todos()]
        self.combo_perfil["values"] = nombres
        self.var_perfil.set(self.vm.perfil_origen)

    def _guardar(self) -> None:
        nombre = simpledialog.askstring("Guardar perfil", "Nombre del perfil:", parent=self.root)
        if not nombre:
            return
        try:
            existe = any(p.nombre == nombre for p in self.vm.gestor.listar())
            self.vm.guardar_perfil(nombre, overwrite=existe)
            self._refrescar_perfiles()
            self._sync()
            self.var_estado.set(f"Perfil «{nombre}» guardado")
        except PerfilError as exc:
            messagebox.showerror("Perfil", str(exc), parent=self.root)

    def _exportar(self) -> None:
        if not self.vm.puede_exportar:
            messagebox.showinfo("Exportar", "Pega primero una URL o un texto.", parent=self.root)
            return
        fmt_ui = self.var_formato.get().lower()
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Exportar imagen",
            defaultextension=f".{fmt_ui}",
            initialfile=f"qr.{fmt_ui}",
            filetypes=filetypes_para(fmt_ui),
        )
        if not path:
            return
        destino, fmt = resolver_export(path, fmt_ui)
        px = int(self.var_px.get())
        while True:
            try:
                self._export_cola.get_nowait()
            except queue.Empty:
                break

        def trabajo() -> None:
            try:
                resultado = self.vm.exportar(fmt, px_modulo=px)
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(resultado.datos)
            except Exception as exc:  # noqa: BLE001
                self._export_cola.put(("error", exc, None))
                return
            self._export_cola.put(("ok", resultado, destino))

        self._exportando = True
        self.var_estado.set("Exportando...")
        self.btn_exportar.config(state=tk.DISABLED)
        if fmt in {"png", "webp"}:
            threading.Thread(target=trabajo, daemon=True).start()
            self.root.after(50, self._revisar_export)
        else:
            trabajo()
            self._revisar_export()

    def _revisar_export(self) -> None:
        try:
            kind, payload, extra = self._export_cola.get_nowait()
        except queue.Empty:
            if self._exportando:
                self.root.after(50, self._revisar_export)
            return
        if kind == "ok":
            self._export_ok(payload, extra)
        else:
            self._export_error(payload)

    def _export_ok(self, resultado, destino: Path) -> None:
        self._exportando = False
        self.btn_exportar.config(state=tk.NORMAL)
        extra = ""
        if resultado.advertencias:
            extra = " - " + "; ".join(resultado.advertencias)
        self.var_estado.set(
            f"{destino.name}: {resultado.peso} bytes, {resultado.ancho}x{resultado.alto}{extra}"
        )

    def _export_error(self, exc: BaseException) -> None:
        self._exportando = False
        self.btn_exportar.config(state=tk.NORMAL)
        self.var_estado.set("Error al exportar")
        messagebox.showerror("Exportar", str(exc), parent=self.root)

    def _photo_png(self, datos: bytes) -> tk.PhotoImage:
        try:
            return tk.PhotoImage(data=datos)
        except tk.TclError:
            return tk.PhotoImage(data=base64.b64encode(datos))

    def _actualizar_minsize(self, pw: int, ph: int) -> None:
        min_w = SIDEBAR_ANCHO + int(pw) + PREVIEW_PAD * 2 + PAD * 4
        min_h = 96 + int(ph) + PREVIEW_PAD * 2 + 40 + PAD * 2
        self.root.minsize(min_w, min_h)

    def _pintar_preview(self) -> None:
        escena = self.vm.escena
        if escena is None:
            self._preview_photo = None
            self.canvas.delete("all")
            self.canvas.config(width=PREVIEW_LADO, height=PREVIEW_LADO)
            self.canvas.create_text(
                PREVIEW_LADO / 2,
                PREVIEW_LADO / 2,
                text=HINT_CONTENIDO,
                fill=GRIS,
                font=("TkDefaultFont", 11),
                width=PREVIEW_LADO - 24,
            )
            self._actualizar_minsize(PREVIEW_LADO, PREVIEW_LADO)
            return
        try:
            from qr_designer.render.preview import preview_png

            png = preview_png(self.vm.contenido, self.vm.perfil, PREVIEW_LADO)
            photo = self._photo_png(png)
            self._preview_photo = photo
            self.canvas.delete("all")
            self.canvas.config(width=photo.width(), height=photo.height())
            self.canvas.create_image(0, 0, image=photo, anchor="nw")
            self._actualizar_minsize(photo.width(), photo.height())
        except Exception:
            px = px_para_preview(escena, PREVIEW_LADO)
            pintar_canvas(self.canvas, escena, scale=float(px))
            self._actualizar_minsize(
                int(self.canvas.cget("width")),
                int(self.canvas.cget("height")),
            )

    def _sync(self) -> None:
        self._silencio = True
        try:
            p = self.vm.perfil
            self.var_modulo.set(p.modulo_estilo.value)
            self.var_ojo.set(p.ojo_estilo.value)
            self.var_marco.set(p.marco_tipo.value)
            self.var_marco_texto.set(p.marco_texto or "")
            self._actualizar_marco_texto_ui()
            self.var_ecc.set(p.correccion.value)
            for campo, var in self._colores.items():
                valor = p.colores.to_dict()[campo]
                var.set(valor)
                getattr(self, f"_sw_{campo}").config(bg=valor, activebackground=valor)
            self.lbl_activo.config(text=f"Activo: {self.vm.etiqueta_perfil}")
            self.lbl_aviso.config(text=self.vm.advertencia_contraste or "")
            sug = self.vm.ecc_recomendada
            if sug != p.correccion.value and p.correccion.value != "auto":
                self.lbl_ecc_sug.config(
                    text=f"Sugerida para lectura: {sug} (el preview no cambia)"
                )
            else:
                self.lbl_ecc_sug.config(text="")
            if self._exportando:
                self.btn_exportar.config(state=tk.DISABLED)
            else:
                estado = tk.NORMAL if self.vm.puede_exportar else tk.DISABLED
                self.btn_exportar.config(state=estado)
            self._pintar_preview()
            self._actualizar_hint_estado()
        finally:
            self._silencio = False

    def _actualizar_hint_estado(self) -> None:
        if self._exportando:
            return
        if self.vm.contenido.strip():
            if self.var_estado.get() == HINT_CONTENIDO:
                self.var_estado.set("")
        else:
            self.var_estado.set(HINT_CONTENIDO)


def run_gui() -> None:
    from qr_designer.ui.fonts import registrar_fuentes

    registrar_fuentes()
    root = tk.Tk()
    QRDesignerApp(root)
    root.mainloop()
