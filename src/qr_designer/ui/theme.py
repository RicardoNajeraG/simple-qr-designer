"""Paleta blanca del mapache, ttk.Style y assets de cabecera."""

from __future__ import annotations

from pathlib import Path
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from qr_designer.ui.fonts import familia_activa, registrar_fuentes

FONDO = "#ffffff"
SUPERFICIE = "#ffffff"
TEXTO = "#2b2724"
GRIS = "#6e6a66"
BORDE = "#d9d4e0"
ACENTO = "#7a5aa6"
ACENTO_HOVER = "#654a8c"
AVISO = "#c45c4a"
MARCO_PREVIEW = "#7a5aa6"
SCROLL_THUMB = "#7a5aa6"
SCROLL_TROUGH = "#e4dfee"

TAMANOS_ICONO = (32, 64, 256)
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ICONO_PATH = ASSETS_DIR / "qr-designer-icon.png"
PET_HEADER = ASSETS_DIR / "qr-designer-pet-h80.png"
BANNER_HEADER = ASSETS_DIR / "simple-qr-designer-banner-h80.png"
SCRAPING_FONDO = ASSETS_DIR / "cuere-scraping-h160.png"
AYUDA_ICONO = ASSETS_DIR / "question_mark-h20.png"

_FUENTES: dict[str, tuple[str, ...]] = {
    "win32": ("Segoe UI", "Calibri", "Arial", "Tahoma"),
    "darwin": ("SF Pro Text", "Helvetica Neue", "Helvetica", "Lucida Grande"),
    "linux": ("Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans", "Liberation Sans"),
}


def preferencias_fuente(plataforma: str | None = None) -> tuple[str, ...]:
    plat = sys.platform if plataforma is None else plataforma
    if plat == "win32":
        return _FUENTES["win32"]
    if plat == "darwin":
        return _FUENTES["darwin"]
    return _FUENTES["linux"]


def escala_para_dpi(dpi: float) -> float:
    return max(1.0, min(3.0, float(dpi) / 72.0))


def ruta_icono(max_px: int) -> Path:
    candidatos = sorted(TAMANOS_ICONO)
    elegido = candidatos[-1]
    for tam in candidatos:
        if tam >= int(max_px):
            elegido = tam
            break
    return ASSETS_DIR / f"qr-designer-icon-{elegido}.png"


def fuente_preferida(root: tk.Misc) -> str:
    return familia_activa(root, preferencias_fuente())


def aplicar_escala(root: tk.Tk) -> float:
    try:
        dpi = float(root.winfo_fpixels("1i"))
    except tk.TclError:
        dpi = 96.0
    escala = escala_para_dpi(dpi)
    try:
        root.tk.call("tk", "scaling", escala)
    except tk.TclError:
        pass
    return escala


def aplicar_fuentes(root: tk.Misc) -> str:
    registrar_fuentes()
    familia = fuente_preferida(root)
    for nombre, size, weight in (
        ("TkDefaultFont", 11, "normal"),
        ("TkTextFont", 11, "normal"),
        ("TkMenuFont", 11, "normal"),
        ("TkHeadingFont", 14, "bold"),
    ):
        try:
            fuente = tkfont.nametofont(nombre)
            if familia != "TkDefaultFont":
                fuente.configure(family=familia, size=size, weight=weight)
            else:
                fuente.configure(size=size, weight=weight)
        except tk.TclError:
            continue
    return familia


def aplicar_tema(root: tk.Tk) -> ttk.Style:
    aplicar_escala(root)
    root.configure(bg=FONDO)
    aplicar_fuentes(root)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("TFrame", background=FONDO)
    style.configure("Surface.TFrame", background=SUPERFICIE)
    style.configure("TLabel", background=FONDO, foreground=TEXTO)
    style.configure("Muted.TLabel", background=FONDO, foreground=GRIS)
    style.configure("Heading.TLabel", background=FONDO, foreground=TEXTO, font="TkHeadingFont")
    style.configure("Aviso.TLabel", background=FONDO, foreground=AVISO)
    style.configure("TEntry", fieldbackground=SUPERFICIE, foreground=TEXTO, bordercolor=BORDE)
    style.configure("TCombobox", fieldbackground=SUPERFICIE, foreground=TEXTO, bordercolor=BORDE)
    style.configure("TCheckbutton", background=FONDO, foreground=TEXTO)
    style.configure("TSpinbox", fieldbackground=SUPERFICIE, foreground=TEXTO)
    style.configure("TPanedwindow", background=FONDO)
    _estilo_scrollbar_minimal(style)
    style.configure(
        "TButton",
        background=BORDE,
        foreground=TEXTO,
        padding=(10, 6),
        borderwidth=0,
        focusthickness=1,
        focuscolor=ACENTO,
    )
    style.map("TButton", background=[("active", "#e6e0ee"), ("pressed", "#d9d1e4")])
    style.configure(
        "Primary.TButton",
        background=ACENTO,
        foreground="#ffffff",
        padding=(14, 7),
        borderwidth=0,
    )
    style.map(
        "Primary.TButton",
        background=[("disabled", BORDE), ("pressed", ACENTO_HOVER), ("active", ACENTO_HOVER)],
        foreground=[("disabled", GRIS), ("!disabled", "#ffffff")],
    )
    return style


def _estilo_scrollbar_minimal(style: ttk.Style) -> None:
    try:
        style.layout(
            "Minimal.Vertical.TScrollbar",
            [
                (
                    "Vertical.Scrollbar.trough",
                    {
                        "sticky": "ns",
                        "children": [
                            ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"}),
                        ],
                    },
                )
            ],
        )
    except tk.TclError:
        pass
    style.configure(
        "Minimal.Vertical.TScrollbar",
        background=SCROLL_THUMB,
        troughcolor=SCROLL_TROUGH,
        bordercolor=SCROLL_TROUGH,
        lightcolor=SCROLL_TROUGH,
        darkcolor=SCROLL_TROUGH,
        arrowcolor=SCROLL_TROUGH,
        relief="flat",
        borderwidth=0,
        gripcount=0,
        width=12,
        arrowsize=0,
    )
    style.map(
        "Minimal.Vertical.TScrollbar",
        background=[("active", GRIS), ("pressed", TEXTO)],
    )


def cargar_png(path: Path, master: tk.Misc | None = None) -> tk.PhotoImage | None:
    if not path.is_file():
        return None
    try:
        kwargs: dict = {"file": str(path)}
        if master is not None:
            kwargs["master"] = master
        return tk.PhotoImage(**kwargs)
    except tk.TclError:
        return None


def cargar_icono(root: tk.Tk, max_px: int = 64, aplicar_ventana: bool = True) -> tk.PhotoImage | None:
    path = ruta_icono(max_px)
    img = cargar_png(path, master=root)
    if img is None:
        return None
    if aplicar_ventana:
        imagenes: list[tk.PhotoImage] = []
        for tam in (256, 64, 32):
            loaded = cargar_png(ruta_icono(tam), master=root)
            if loaded is not None:
                imagenes.append(loaded)
        if imagenes:
            try:
                root.iconphoto(True, *imagenes)
            except tk.TclError:
                pass
            root._qr_iconos_wm = imagenes  # type: ignore[attr-defined]
        else:
            try:
                root.iconphoto(True, img)
            except tk.TclError:
                pass
    return img
