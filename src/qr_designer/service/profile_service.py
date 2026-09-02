"""CRUD de perfiles con entrada/salida dict. Envuelve GestorPerfiles."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from qr_designer.config.profiles import GestorPerfiles
from qr_designer.service.dto import perfil_a_dict, perfil_desde_dict


class ProfileService:
    def __init__(self, ruta: Path | None = None, gestor: GestorPerfiles | None = None) -> None:
        self._gestor = gestor or GestorPerfiles(ruta)

    @property
    def gestor(self) -> GestorPerfiles:
        return self._gestor

    def por_defecto(self) -> dict[str, Any]:
        return perfil_a_dict(self._gestor.por_defecto())

    def listar(self) -> list[dict[str, Any]]:
        return [perfil_a_dict(p) for p in self._gestor.listar()]

    def listar_todos(self) -> list[dict[str, Any]]:
        return [perfil_a_dict(p) for p in self._gestor.listar_todos()]

    def obtener(self, nombre: str) -> dict[str, Any]:
        return perfil_a_dict(self._gestor.obtener(nombre))

    def guardar(self, perfil_dict: dict[str, Any], overwrite: bool = False) -> None:
        self._gestor.guardar(perfil_desde_dict(perfil_dict), overwrite=overwrite)

    def eliminar(self, nombre: str) -> None:
        self._gestor.eliminar(nombre)

    def renombrar(self, viejo: str, nuevo: str) -> None:
        self._gestor.renombrar(viejo, nuevo)

    def duplicar(self, origen: str, nuevo: str) -> dict[str, Any]:
        return perfil_a_dict(self._gestor.duplicar(origen, nuevo))
