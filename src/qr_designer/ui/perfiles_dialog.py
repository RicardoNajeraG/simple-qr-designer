"""Diálogo catálogo de perfiles: ver, aplicar, duplicar, renombrar, eliminar."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from qr_designer.config.models import MarcoTipo, Perfil
from qr_designer.config.presets import NOMBRES_PRESET, PRESETS
from qr_designer.config.profiles import PerfilError, es_preset
from qr_designer.render.canvas import pintar_canvas
from qr_designer.scene.builders import escena_desde_contenido
from qr_designer.ui.theme import BORDE, FONDO
from qr_designer.ui.redondeo import CajaRedonda
from qr_designer.ui.viewmodel import ViewModel

OnCerrar = Callable[[], None]
OnCambio = Callable[[], None]

MUESTRA_LADO = 120
MUESTRA_PAYLOAD = "QR"
NOMBRE_NUEVO = "Nuevo perfil"


def nombre_libre_propuesto(base: str, ocupados: set[str]) -> str:
    if base not in ocupados:
        return base
    n = 2
    while f"{base} {n}" in ocupados:
        n += 1
    return f"{base} {n}"


def nombre_duplicado_propuesto(origen: str, ocupados: set[str]) -> str:
    return nombre_libre_propuesto(f"{origen} copia", ocupados)


class DialogoPerfiles(tk.Toplevel):
    IID_FABRICA = "grp-fabrica"
    IID_USUARIO = "grp-usuario"
    IID_VACIO = "usr-vacio"

    def __init__(
        self,
        master: tk.Misc,
        vm: ViewModel,
        on_cerrar: OnCerrar | None = None,
        on_cambio: OnCambio | None = None,
    ) -> None:
        super().__init__(master)
        self.title("Gestionar perfiles")
        self.configure(bg=FONDO)
        self.vm = vm
        self._on_cerrar = on_cerrar
        self._on_cambio = on_cambio
        self._nombre_sel: str | None = None
        try:
            self.transient(master.winfo_toplevel())
        except tk.TclError:
            pass
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.bind("<Escape>", lambda _e: self._cerrar())
        self.minsize(560, 500)
        self.geometry("640x560")

        cuerpo = ttk.Frame(self, padding=12)
        cuerpo.pack(fill=tk.BOTH, expand=True)
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)

        izq = ttk.Frame(cuerpo)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        izq.rowconfigure(1, weight=1)
        ttk.Label(izq, text="Perfiles", style="Heading.TLabel").pack(anchor=tk.W)
        self.arbol = ttk.Treeview(izq, show="tree", selectmode="browse", height=16)
        self.arbol.column("#0", width=180, stretch=True)
        self.arbol.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.arbol.bind("<<TreeviewSelect>>", self._on_seleccion)

        centro = ttk.Frame(cuerpo)
        centro.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        ttk.Label(centro, text="Detalle", style="Heading.TLabel").pack(anchor=tk.W)
        self.lbl_nombre = ttk.Label(centro, text="", style="Heading.TLabel")
        self.lbl_nombre.pack(anchor=tk.W, pady=(8, 0))
        self.lbl_sello = ttk.Label(centro, text="", style="Muted.TLabel")
        self.lbl_sello.pack(anchor=tk.W)
        self.canvas_muestra = tk.Canvas(
            centro,
            width=MUESTRA_LADO,
            height=MUESTRA_LADO,
            bg=FONDO,
            highlightthickness=1,
            highlightbackground=BORDE,
            bd=0,
        )
        self.canvas_muestra.pack(anchor=tk.W, pady=(8, 8))
        self.lbl_modulo = ttk.Label(centro, text="")
        self.lbl_modulo.pack(anchor=tk.W)
        self.lbl_ojo = ttk.Label(centro, text="")
        self.lbl_ojo.pack(anchor=tk.W)
        self.lbl_marco = ttk.Label(centro, text="")
        self.lbl_marco.pack(anchor=tk.W)
        self.frm_marco_texto = ttk.Frame(centro)
        self.lbl_marco_texto = ttk.Label(self.frm_marco_texto, text="")
        self.lbl_marco_texto.pack(anchor=tk.W)
        self.lbl_ecc = ttk.Label(centro, text="")
        self.lbl_ecc.pack(anchor=tk.W, pady=(4, 0))
        self.lbl_logo = ttk.Label(centro, text="", style="Muted.TLabel")
        self.lbl_logo.pack(anchor=tk.W, pady=(0, 8))
        self.frm_colores = ttk.Frame(centro)
        self.frm_colores.pack(anchor=tk.W, pady=(0, 8))
        self._swatches: dict[str, tk.Frame] = {}
        self._hex: dict[str, ttk.Label] = {}
        for campo, etiqueta in (
            ("fondo", "Fondo"),
            ("modulos", "Módulos"),
            ("ojos", "Ojos"),
            ("marco", "Marco"),
        ):
            fila = ttk.Frame(self.frm_colores)
            fila.pack(anchor=tk.W, pady=1)
            ttk.Label(fila, text=etiqueta, width=9).pack(side=tk.LEFT)
            chip = tk.Frame(
                fila, width=18, height=14, bd=1, relief="solid", highlightthickness=0,
                highlightbackground=BORDE, bg=FONDO,
            )
            chip.pack(side=tk.LEFT, padx=(0, 6))
            chip.pack_propagate(False)
            hex_l = ttk.Label(fila, text="", style="Muted.TLabel")
            hex_l.pack(side=tk.LEFT)
            self._swatches[campo] = chip
            self._hex[campo] = hex_l

        col_btns = ttk.Frame(cuerpo)
        col_btns.grid(row=0, column=2, sticky="ne")

        def _boton(texto: str, comando, **kw) -> ttk.Button:
            caja = CajaRedonda(col_btns, fondo=BORDE, borde=BORDE)
            btn = ttk.Button(caja, text=texto, command=comando, **kw)
            caja.alojar(btn)
            caja.pack(fill=tk.X, pady=(0, 6))
            return btn

        self.btn_nuevo = _boton("Nuevo perfil", self._nuevo)
        self.btn_aplicar = _boton("Aplicar", self._aplicar)
        self.btn_duplicar = _boton("Duplicar", self._duplicar)
        self.btn_renombrar = _boton("Renombrar", self._renombrar)
        self.btn_eliminar = _boton("Eliminar", self._eliminar)
        caja_cerrar = CajaRedonda(col_btns, fondo=BORDE, borde=BORDE)
        self.btn_cerrar = ttk.Button(caja_cerrar, text="Cerrar", command=self._cerrar)
        caja_cerrar.alojar(self.btn_cerrar)
        caja_cerrar.pack(fill=tk.X, pady=(18, 0))

        self._llenar_arbol()
        self._set_botones(None)
        self.update_idletasks()
        try:
            self.grab_set()
        except tk.TclError:
            pass

    def iid_perfil(self, nombre: str) -> str | None:
        prefijo = "fab::" if es_preset(nombre) else "usr::"
        candidato = prefijo + nombre
        if self.arbol.exists(candidato):
            return candidato
        return None

    def seleccionar_nombre(self, nombre: str) -> None:
        iid = self.iid_perfil(nombre)
        if not iid:
            return
        self.arbol.selection_set(iid)
        self.arbol.see(iid)
        self._on_seleccion()

    def _ocupados(self) -> set[str]:
        nombres = set(NOMBRES_PRESET)
        nombres.update(p.nombre for p in self.vm.gestor.listar())
        return nombres

    def _llenar_arbol(self, seleccionar: str | None = None) -> None:
        for iid in self.arbol.get_children():
            self.arbol.delete(iid)
        self.arbol.insert("", "end", iid=self.IID_FABRICA, text="Fábrica", open=True)
        self.arbol.insert("", "end", iid=self.IID_USUARIO, text="Mis perfiles", open=True)
        for p in PRESETS:
            self.arbol.insert(
                self.IID_FABRICA, "end", iid=f"fab::{p.nombre}", text=p.nombre
            )
        usuarios = list(self.vm.gestor.listar())
        if not usuarios:
            self.arbol.insert(
                self.IID_USUARIO, "end", iid=self.IID_VACIO, text="(ninguno aún)"
            )
        else:
            for p in usuarios:
                self.arbol.insert(
                    self.IID_USUARIO, "end", iid=f"usr::{p.nombre}", text=p.nombre
                )
        if seleccionar:
            self.seleccionar_nombre(seleccionar)

    def _on_seleccion(self, _event=None) -> None:
        sel = self.arbol.selection()
        if not sel:
            self._nombre_sel = None
            self._limpiar_muestra()
            self._set_botones(None)
            return
        iid = sel[0]
        if iid in {self.IID_FABRICA, self.IID_USUARIO, self.IID_VACIO}:
            self.arbol.selection_remove(iid)
            self._nombre_sel = None
            self._limpiar_muestra()
            self._set_botones(None)
            return
        nombre = str(self.arbol.item(iid, "text"))
        self._nombre_sel = nombre
        self._mostrar_ficha(nombre)
        self._set_botones("fabrica" if es_preset(nombre) else "usuario")

    def _mostrar_ficha(self, nombre: str) -> None:
        try:
            perfil = self.vm.gestor.obtener(nombre)
        except PerfilError as exc:
            messagebox.showerror("Perfil", str(exc), parent=self)
            return
        self.lbl_nombre.config(text=perfil.nombre)
        self.lbl_sello.config(text="Fábrica" if es_preset(nombre) else "Usuario")
        self.lbl_modulo.config(text=perfil.modulo_estilo.value)
        self.lbl_ojo.config(text=f"Ojos: {perfil.ojo_estilo.value}")
        self.lbl_marco.config(text=f"Marco: {perfil.marco_tipo.value}")
        if perfil.marco_tipo is MarcoTipo.NINGUNO:
            self.frm_marco_texto.pack_forget()
        else:
            self.lbl_marco_texto.config(text=f"Texto: {perfil.marco_texto or ''}")
            if str(self.frm_marco_texto.winfo_manager()) != "pack":
                self.frm_marco_texto.pack(anchor=tk.W, after=self.lbl_marco)
        self.lbl_ecc.config(text=f"Corrección: {perfil.correccion.value}")
        if perfil.logo_id:
            self.lbl_logo.config(text=f"Logo: {perfil.logo_id}")
        elif perfil.logo_path:
            self.lbl_logo.config(text=f"Logo: {Path(perfil.logo_path).name}")
        else:
            self.lbl_logo.config(text="Logo: (ninguno)")
        colores = perfil.colores.to_dict()
        for campo, valor in colores.items():
            self._swatches[campo].config(bg=valor)
            self._hex[campo].config(text=valor)
        self._pintar_muestra(perfil)

    def _pintar_muestra(self, perfil: Perfil) -> None:
        escena = escena_desde_contenido(MUESTRA_PAYLOAD, perfil)
        pintar_canvas(self.canvas_muestra, escena, lienzo=MUESTRA_LADO)

    def _limpiar_muestra(self) -> None:
        self.canvas_muestra.delete("all")
        self.canvas_muestra.config(width=MUESTRA_LADO, height=MUESTRA_LADO)

    def _set_botones(self, clase: str | None) -> None:
        def est(btn: ttk.Button, activo: bool) -> None:
            btn.config(state=tk.NORMAL if activo else tk.DISABLED)

        if clase == "fabrica":
            est(self.btn_aplicar, True)
            est(self.btn_duplicar, True)
            est(self.btn_renombrar, False)
            est(self.btn_eliminar, False)
        elif clase == "usuario":
            est(self.btn_aplicar, True)
            est(self.btn_duplicar, True)
            est(self.btn_renombrar, True)
            est(self.btn_eliminar, True)
        else:
            est(self.btn_aplicar, False)
            est(self.btn_duplicar, False)
            est(self.btn_renombrar, False)
            est(self.btn_eliminar, False)

    def _confirmar_descarte(self, nombre: str) -> bool:
        if not self.vm.modificado:
            return True
        return bool(
            messagebox.askyesno(
                "Cambios sin guardar",
                f"Hay cambios sin guardar. ¿Descartar y aplicar «{nombre}»?",
                parent=self,
            )
        )

    def _aplicar(self) -> None:
        nombre = self._nombre_sel
        if not nombre:
            return
        if not self._confirmar_descarte(nombre):
            return
        try:
            self.vm.aplicar_perfil(nombre)
        except PerfilError as exc:
            messagebox.showerror("Perfil", str(exc), parent=self)
            return
        self._cerrar()

    def _nuevo(self) -> None:
        propuesto = nombre_libre_propuesto(NOMBRE_NUEVO, self._ocupados())
        nuevo = simpledialog.askstring(
            "Nuevo perfil",
            "Nombre del perfil:",
            initialvalue=propuesto,
            parent=self,
        )
        if not nuevo:
            return
        destino = nuevo.strip()
        if not destino:
            return
        if not self._confirmar_descarte(destino):
            return
        try:
            copia = self.vm.duplicar_perfil("Clásico", destino)
        except (PerfilError, ValueError) as exc:
            messagebox.showerror("Perfil", str(exc), parent=self)
            return
        try:
            self.vm.aplicar_perfil(copia.nombre)
        except PerfilError as exc:
            messagebox.showerror("Perfil", str(exc), parent=self)
            if self._on_cambio:
                self._on_cambio()
            self._llenar_arbol(seleccionar=copia.nombre)
            return
        self._cerrar()

    def _duplicar(self) -> None:
        origen = self._nombre_sel
        if not origen:
            return
        propuesto = nombre_duplicado_propuesto(origen, self._ocupados())
        nuevo = simpledialog.askstring(
            "Duplicar perfil",
            "Nombre de la copia:",
            initialvalue=propuesto,
            parent=self,
        )
        if not nuevo:
            return
        try:
            copia = self.vm.duplicar_perfil(origen, nuevo)
        except (PerfilError, ValueError) as exc:
            messagebox.showerror("Perfil", str(exc), parent=self)
            return
        if self._on_cambio:
            self._on_cambio()
        self._llenar_arbol(seleccionar=copia.nombre)

    def _renombrar(self) -> None:
        viejo = self._nombre_sel
        if not viejo or es_preset(viejo):
            return
        nuevo = simpledialog.askstring(
            "Renombrar perfil",
            "Nuevo nombre:",
            initialvalue=viejo,
            parent=self,
        )
        if not nuevo or nuevo.strip() == viejo:
            return
        try:
            self.vm.renombrar_perfil(viejo, nuevo)
        except (PerfilError, ValueError) as exc:
            messagebox.showerror("Perfil", str(exc), parent=self)
            return
        if self._on_cambio:
            self._on_cambio()
        self._llenar_arbol(seleccionar=nuevo.strip())

    def _eliminar(self) -> None:
        nombre = self._nombre_sel
        if not nombre or es_preset(nombre):
            return
        activo = self.vm.perfil_origen == nombre
        extra = ""
        if activo:
            extra = " Se aplicará Clásico y se descartarán los cambios de la ventana principal."
        if not messagebox.askyesno(
            "Eliminar perfil",
            f"¿Eliminar «{nombre}»?{extra}",
            parent=self,
        ):
            return
        try:
            self.vm.eliminar_perfil(nombre)
        except PerfilError as exc:
            messagebox.showerror("Perfil", str(exc), parent=self)
            return
        if self._on_cambio:
            self._on_cambio()
        self._llenar_arbol()
        self._nombre_sel = None
        self._limpiar_muestra()
        self._set_botones(None)

    def _cerrar(self) -> None:
        try:
            self.grab_release()
        except tk.TclError:
            pass
        cb = self._on_cerrar
        self._on_cerrar = None
        if cb is not None:
            cb()
        try:
            self.destroy()
        except tk.TclError:
            return
