"""Estado de la aplicación sin widgets. Debounce inyectable."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Protocol

from qr_designer.config.models import (
    ColorScheme,
    Correccion,
    MarcoTipo,
    ModuloEstilo,
    OjoEstilo,
    Perfil,
)
from qr_designer.config.profiles import GestorPerfiles
from qr_designer.core.encoder import MatrizQR
from qr_designer.scene.primitives import Escena
from qr_designer.service.dto import perfil_a_dict, resultado_desde_dict
from qr_designer.service.qr_service import evaluar, exportar_qr, previsualizar

DEBOUNCE_MS = 16


class Programador(Protocol):
    def programar(self, ms: int, callback: Callable[[], None]) -> object: ...
    def cancelar(self, handle: object) -> None: ...


class ProgramadorInmediato:
    def programar(self, ms: int, callback: Callable[[], None]) -> object:
        callback()
        return 0

    def cancelar(self, handle: object) -> None:
        return None


@dataclass
class _Pendiente:
    handle: object
    ms: int
    callback: Callable[[], None]


class ProgramadorManual:
    """Acumula callbacks para tests de coalescing."""

    def __init__(self) -> None:
        self.pendientes: list[_Pendiente] = []

    def programar(self, ms: int, callback: Callable[[], None]) -> object:
        handle = object()
        self.pendientes.append(_Pendiente(handle, ms, callback))
        return handle

    def cancelar(self, handle: object) -> None:
        self.pendientes = [p for p in self.pendientes if p.handle is not handle]

    def flush(self) -> None:
        cbs = [p.callback for p in self.pendientes]
        self.pendientes.clear()
        for cb in cbs:
            cb()


class ViewModel:
    def __init__(
        self,
        gestor: GestorPerfiles | None = None,
        programador: Programador | None = None,
        debounce_ms: int = DEBOUNCE_MS,
    ) -> None:
        self.gestor = gestor or GestorPerfiles()
        self.programador = programador or ProgramadorInmediato()
        self.debounce_ms = debounce_ms
        self.contenido = ""
        self.perfil = self.gestor.por_defecto()
        self.perfil_origen = self.perfil.nombre
        self.modificado = False
        self.avanzado_colapsado = True
        self.acciones = 0
        self.rebuilds = 0
        self.escena: Escena | None = None
        self.matriz: MatrizQR | None = None
        self._handle: object | None = None
        self.on_change: Callable[[], None] | None = None
        self._rebuild()

    @property
    def puede_exportar(self) -> bool:
        return bool(self.contenido.strip()) and self.escena is not None

    @property
    def etiqueta_perfil(self) -> str:
        base = self.perfil_origen
        return f"{base} (modificado)" if self.modificado else base

    @property
    def _eval(self) -> dict:
        return evaluar(perfil_a_dict(self.perfil))

    @property
    def advertencia_contraste(self) -> str | None:
        avisos = self._eval["advertencias"]
        return " · ".join(avisos) if avisos else None

    @property
    def ecc_recomendada(self) -> str:
        return str(self._eval["ecc_recomendada"])

    def set_url(self, url: str) -> None:
        self.acciones += 1
        self.contenido = url
        self._rebuild()

    def aplicar_perfil(self, nombre: str) -> None:
        self.acciones += 1
        self.perfil = self.gestor.obtener(nombre)
        self.perfil_origen = nombre
        self.modificado = False
        self._programar_rebuild()

    def guardar_perfil(self, nombre: str | None = None, overwrite: bool = False) -> None:
        destino = (nombre or self.perfil.nombre).strip()
        perfil = replace(self.perfil, nombre=destino)
        self.gestor.guardar(perfil, overwrite=overwrite)
        self.perfil = perfil
        self.perfil_origen = destino
        self.modificado = False

    def duplicar_perfil(self, origen: str, nuevo: str) -> Perfil:
        return self.gestor.duplicar(origen, nuevo)

    def renombrar_perfil(self, viejo: str, nuevo: str) -> None:
        self.gestor.renombrar(viejo, nuevo)
        if self.perfil_origen != viejo:
            return
        self.perfil_origen = nuevo
        datos = self.perfil.to_dict()
        datos["nombre"] = nuevo
        self.perfil = Perfil.from_dict(datos)

    def eliminar_perfil(self, nombre: str) -> None:
        activo = self.perfil_origen == nombre
        self.gestor.eliminar(nombre)
        if activo:
            self.aplicar_perfil("Clásico")

    def set_modulo(self, estilo: ModuloEstilo) -> None:
        self._touch(self.perfil.__class__(**{**self.perfil.to_dict(), "modulo_estilo": estilo}))

    def set_ojo(self, estilo: OjoEstilo) -> None:
        self._touch(Perfil(**{**self.perfil.to_dict(), "ojo_estilo": estilo}))

    def set_marco(self, tipo: MarcoTipo) -> None:
        self._touch(Perfil(**{**self.perfil.to_dict(), "marco_tipo": tipo}))

    def set_marco_texto(self, texto: str) -> None:
        self._touch(Perfil(**{**self.perfil.to_dict(), "marco_texto": texto}))

    def set_correccion(self, correccion: Correccion) -> None:
        self._touch(Perfil(**{**self.perfil.to_dict(), "correccion": correccion}))

    def set_color(self, campo: str, valor: str) -> None:
        actual = self.perfil.colores.to_dict()
        if campo not in actual:
            raise ValueError(f"Campo de color desconocido: {campo}")
        actual[campo] = valor
        self._touch(Perfil(**{**self.perfil.to_dict(), "colores": ColorScheme.from_dict(actual)}))

    def set_logo(self, ruta: str | None) -> None:
        path = None if ruta is None else (str(ruta).strip() or None)
        self.perfil = replace(self.perfil, logo_path=path, logo_id=None)
        self.modificado = True
        self._rebuild()

    def set_logo_catalogo(self, ident: str) -> None:
        clave = str(ident).strip()
        self.perfil = replace(self.perfil, logo_id=clave or None, logo_path=None)
        self.modificado = True
        self._rebuild()

    def exportar(self, formato: str, px_modulo: int | None = None):
        if not self.puede_exportar:
            raise ValueError("No hay contenido para exportar")
        self.acciones += 1
        bruto = exportar_qr(
            self.contenido, perfil_a_dict(self.perfil), formato, px_modulo
        )
        return resultado_desde_dict(bruto)

    def _touch(self, perfil: Perfil) -> None:
        self.perfil = perfil
        self.modificado = True
        self._programar_rebuild()

    def _programar_rebuild(self) -> None:
        if self._handle is not None:
            self.programador.cancelar(self._handle)
        self._handle = self.programador.programar(self.debounce_ms, self._rebuild)

    def _rebuild(self) -> None:
        self._handle = None
        escena, matriz = previsualizar(self.contenido, perfil_a_dict(self.perfil))
        self.escena = escena
        self.matriz = matriz
        if escena is not None:
            self.rebuilds += 1
        if self.on_change is not None:
            self.on_change()
