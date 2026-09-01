"""Ventana emergente de «acerca de»: versión y enlace al repositorio."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import font as tkfont
from tkinter import ttk

from qr_designer.meta import REPO_URL, version_app
from qr_designer.ui.theme import ACENTO, FONDO


class VentanaAcerca(tk.Toplevel):
    """Diálogo estándar con la versión del paquete y el enlace al repo."""

    def __init__(self, master: tk.Misc, on_cerrar=None) -> None:
        super().__init__(master)
        self.title("Acerca de")
        self.resizable(False, False)
        self.configure(bg=FONDO)
        self.texto = f"Versión {version_app()}\n{REPO_URL}"
        self._on_cerrar = on_cerrar
        try:
            self.transient(master.winfo_toplevel())
        except tk.TclError:
            pass
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

        cuerpo = ttk.Frame(self, padding=20)
        cuerpo.pack(fill=tk.BOTH, expand=True)
        ttk.Label(cuerpo, text="Simple QR Designer", style="Heading.TLabel").pack(
            anchor=tk.W
        )
        ttk.Label(
            cuerpo, text=f"Versión {version_app()}", style="Muted.TLabel"
        ).pack(anchor=tk.W, pady=(8, 12))
        try:
            fuente = tkfont.nametofont("TkDefaultFont").copy()
            fuente.configure(underline=True)
        except tk.TclError:
            fuente = ("TkDefaultFont", 10, "underline")
        enlace = tk.Label(
            cuerpo,
            text="Ver repositorio en GitHub",
            fg=ACENTO,
            bg=FONDO,
            cursor="hand2",
            font=fuente,
            bd=0,
        )
        enlace.pack(anchor=tk.W)
        enlace.bind("<Button-1>", self._abrir_repo)
        self._fuente_enlace = fuente
        ttk.Button(cuerpo, text="Cerrar", command=self._cerrar).pack(
            anchor=tk.E, pady=(16, 0)
        )
        self._centrar(master)

    def _centrar(self, master: tk.Misc) -> None:
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        try:
            mx, my = master.winfo_rootx(), master.winfo_rooty()
            mw, mh = master.winfo_width(), master.winfo_height()
        except tk.TclError:
            mx = my = 0
            mw, mh = w, h
        x = mx + max((mw - w) // 2, 0)
        y = my + max((mh - h) // 2, 0)
        self.geometry(f"+{x}+{y}")

    def _cerrar(self) -> None:
        cb = self._on_cerrar
        self._on_cerrar = None
        if cb is not None:
            cb()
        try:
            self.destroy()
        except tk.TclError:
            return

    def _abrir_repo(self, _event=None) -> None:
        webbrowser.open(REPO_URL)
