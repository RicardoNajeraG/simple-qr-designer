"""GUI tkinter delgada sobre el ViewModel. Pillow no se importa aquí."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk

from qr_designer.config.models import Correccion, MarcoTipo, ModuloEstilo, OjoEstilo
from qr_designer.config.profiles import PerfilError
from qr_designer.render.canvas import pintar_canvas
from qr_designer.ui.viewmodel import ViewModel

SWATCHES = (
    "#000000",
    "#ffffff",
    "#111111",
    "#0b3d91",
    "#8b1e1e",
    "#0f6b3c",
    "#3d2914",
    "#cc8800",
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


class QRDesignerApp:
    def __init__(self, root: tk.Tk, vm: ViewModel | None = None) -> None:
        self.root = root
        self.root.title("QR Designer")
        self.root.minsize(720, 480)
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
        izq = ttk.Frame(root, padding=12)
        izq.pack(side=tk.LEFT, fill=tk.Y)
        der = ttk.Frame(root, padding=12)
        der.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ttk.Label(izq, text="URL o texto").pack(anchor=tk.W)
        self.var_url = tk.StringVar()
        url = ttk.Entry(izq, textvariable=self.var_url, width=36)
        url.pack(fill=tk.X, pady=(0, 8))
        url.bind("<KeyRelease>", self._on_url)

        ttk.Label(izq, text="Perfil").pack(anchor=tk.W)
        fila_p = ttk.Frame(izq)
        fila_p.pack(fill=tk.X)
        self.var_perfil = tk.StringVar()
        self.combo_perfil = ttk.Combobox(
            fila_p, textvariable=self.var_perfil, state="readonly", width=22
        )
        self.combo_perfil.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.combo_perfil.bind("<<ComboboxSelected>>", self._on_perfil)
        self.lbl_activo = ttk.Label(izq, text="")
        self.lbl_activo.pack(anchor=tk.W, pady=(2, 8))

        ttk.Label(izq, text="Personalizar").pack(anchor=tk.W)
        self.var_modulo = tk.StringVar()
        self.var_ojo = tk.StringVar()
        self.var_marco = tk.StringVar()
        self._combo(izq, "Módulos", self.var_modulo, [e.value for e in ModuloEstilo], self._on_modulo)
        self._combo(izq, "Ojos", self.var_ojo, [e.value for e in OjoEstilo], self._on_ojo)
        self._combo(izq, "Marco", self.var_marco, [e.value for e in MarcoTipo], self._on_marco)

        ttk.Label(izq, text="Texto del marco").pack(anchor=tk.W, pady=(6, 0))
        self.var_marco_texto = tk.StringVar()
        e_txt = ttk.Entry(izq, textvariable=self.var_marco_texto)
        e_txt.pack(fill=tk.X)
        e_txt.bind("<KeyRelease>", lambda _e: self._on_marco_texto())

        ttk.Label(izq, text="Colores").pack(anchor=tk.W, pady=(8, 0))
        self._colores = {}
        for campo, etiqueta in (
            ("fondo", "Fondo"),
            ("modulos", "Módulos"),
            ("ojos", "Ojos"),
            ("marco", "Marco"),
        ):
            self._fila_color(izq, campo, etiqueta)

        self.lbl_aviso = ttk.Label(izq, text="", wraplength=260, foreground="#8b1e1e")
        self.lbl_aviso.pack(anchor=tk.W, pady=6)

        self.var_avanzado = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            izq,
            text="Avanzado",
            variable=self.var_avanzado,
            command=self._toggle_avanzado,
        ).pack(anchor=tk.W)
        self.frm_adv = ttk.Frame(izq)
        ttk.Label(self.frm_adv, text="Corrección de errores").pack(anchor=tk.W)
        self.var_ecc = tk.StringVar()
        self._combo(self.frm_adv, None, self.var_ecc, [e.value for e in Correccion], self._on_ecc)
        ttk.Label(self.frm_adv, text="Píxeles por módulo (PNG/WEBP)").pack(anchor=tk.W)
        self.var_px = tk.IntVar(value=8)
        ttk.Spinbox(self.frm_adv, from_=1, to=32, textvariable=self.var_px, width=6).pack(anchor=tk.W)
        self.lbl_ecc_sug = ttk.Label(self.frm_adv, text="")
        self.lbl_ecc_sug.pack(anchor=tk.W)

        btns = ttk.Frame(izq)
        btns.pack(fill=tk.X, pady=12)
        ttk.Button(btns, text="Guardar perfil", command=self._guardar).pack(side=tk.LEFT)
        self.btn_exportar = tk.Button(
            btns,
            text="Exportar imagen",
            command=self._exportar,
            bg="#1a6b3c",
            fg="white",
            activebackground="#145830",
            activeforeground="white",
            padx=10,
        )
        self.btn_exportar.pack(side=tk.RIGHT)

        ttk.Label(der, text="Vista previa").pack(anchor=tk.W)
        self.canvas = tk.Canvas(der, width=280, height=280, bg="#f4f4f4", highlightthickness=0)
        self.canvas.pack(pady=8)
        self.var_estado = tk.StringVar(value="Pega una URL para generar el QR")
        ttk.Label(der, textvariable=self.var_estado).pack(anchor=tk.W)

    def _combo(self, parent, etiqueta, var, values, handler) -> None:
        if etiqueta:
            ttk.Label(parent, text=etiqueta).pack(anchor=tk.W, pady=(4, 0))
        box = ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=20)
        box.pack(fill=tk.X)
        box.bind("<<ComboboxSelected>>", lambda _e: handler())

    def _fila_color(self, parent, campo: str, etiqueta: str) -> None:
        fila = ttk.Frame(parent)
        fila.pack(fill=tk.X, pady=2)
        ttk.Label(fila, text=etiqueta, width=9).pack(side=tk.LEFT)
        var = tk.StringVar()
        self._colores[campo] = var
        sw = tk.Button(fila, width=3, command=lambda c=campo: self._picker(c))
        sw.pack(side=tk.LEFT, padx=4)
        setattr(self, f"_sw_{campo}", sw)
        ent = ttk.Entry(fila, textvariable=var, width=10)
        ent.pack(side=tk.LEFT)
        ent.bind("<Return>", lambda _e, c=campo: self._hex(c))
        ent.bind("<FocusOut>", lambda _e, c=campo: self._hex(c))
        pal = ttk.Frame(parent)
        pal.pack(anchor=tk.W)
        for color in SWATCHES:
            tk.Button(
                pal,
                width=1,
                bg=color,
                command=lambda col=color, c=campo: self._swatch(c, col),
            ).pack(side=tk.LEFT, padx=1)

    def _on_url(self, _e=None) -> None:
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
        if self._silencio:
            return
        self.vm.set_marco(MarcoTipo(self.var_marco.get()))

    def _on_marco_texto(self) -> None:
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

    def _toggle_avanzado(self) -> None:
        self.vm.avanzado_colapsado = not self.var_avanzado.get()
        if self.var_avanzado.get():
            self.frm_adv.pack(fill=tk.X, pady=4)
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
            messagebox.showinfo("Exportar", "Pega primero una URL o texto.", parent=self.root)
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Exportar imagen",
            defaultextension=".svg",
            filetypes=[
                ("SVG", "*.svg"),
                ("PNG", "*.png"),
                ("WEBP", "*.webp"),
            ],
        )
        if not path:
            return
        destino = Path(path)
        fmt = destino.suffix.lstrip(".").lower() or "svg"
        px = int(self.var_px.get())

        def trabajo() -> None:
            try:
                resultado = self.vm.exportar(fmt, px_modulo=px)
                destino.write_bytes(resultado.datos)
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, lambda: self._export_error(exc))
                return
            self.root.after(0, lambda: self._export_ok(resultado, destino))

        if fmt in {"png", "webp"}:
            self.var_estado.set("Exportando…")
            self.btn_exportar.config(state=tk.DISABLED)
            threading.Thread(target=trabajo, daemon=True).start()
        else:
            trabajo()

    def _export_ok(self, resultado, destino: Path) -> None:
        self.btn_exportar.config(state=tk.NORMAL)
        extra = ""
        if resultado.advertencias:
            extra = " — " + "; ".join(resultado.advertencias)
        self.var_estado.set(
            f"{destino.name}: {resultado.peso} bytes, {resultado.ancho}×{resultado.alto}{extra}"
        )

    def _export_error(self, exc: BaseException) -> None:
        self.btn_exportar.config(state=tk.NORMAL)
        self.var_estado.set("Error al exportar")
        messagebox.showerror("Exportar", str(exc), parent=self.root)

    def _sync(self) -> None:
        self._silencio = True
        try:
            p = self.vm.perfil
            self.var_modulo.set(p.modulo_estilo.value)
            self.var_ojo.set(p.ojo_estilo.value)
            self.var_marco.set(p.marco_tipo.value)
            self.var_marco_texto.set(p.marco_texto or "")
            self.var_ecc.set(p.correccion.value)
            for campo, var in self._colores.items():
                valor = p.colores.to_dict()[campo]
                var.set(valor)
                getattr(self, f"_sw_{campo}").config(bg=valor)
            self.lbl_activo.config(text=f"Activo: {self.vm.etiqueta_perfil}")
            self.lbl_aviso.config(text=self.vm.advertencia_contraste or "")
            sug = self.vm.ecc_recomendada
            if sug != p.correccion.value and p.correccion.value != "auto":
                self.lbl_ecc_sug.config(text=f"Sugerida para lectura: {sug} (el preview no cambia)")
            else:
                self.lbl_ecc_sug.config(text="")
            self.btn_exportar.config(state=tk.NORMAL if self.vm.puede_exportar else tk.DISABLED)
            if self.vm.escena is not None:
                pintar_canvas(self.canvas, self.vm.escena)
            else:
                self.canvas.delete("all")
                self.canvas.create_text(140, 140, text="QR", fill="#aaaaaa", font=("sans-serif", 24))
        finally:
            self._silencio = False


def run_gui() -> None:
    root = tk.Tk()
    QRDesignerApp(root)
    root.mainloop()
