"""CRUD de perfiles de usuario con escritura atómica y schema_version."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from qr_designer.config.models import Perfil
from qr_designer.config.presets import NOMBRES_PRESET, PRESETS, preset_por_nombre
from qr_designer.core.encoder import QRDesignerError

SCHEMA_VERSION = 1


class PerfilError(QRDesignerError):
    """Error de persistencia de perfiles."""


class PerfilNoEncontrado(PerfilError):
    pass


class PerfilProtegido(PerfilError):
    pass


class PerfilYaExiste(PerfilError):
    pass


class PerfilCorrupto(PerfilError):
    pass


def _atomic_write(path: Path, texto: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".profiles.", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(texto)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


class GestorPerfiles:
    def __init__(self, ruta: Path | None = None) -> None:
        self.ruta = Path(ruta) if ruta else Path.home() / ".qr_designer" / "profiles.json"

    def por_defecto(self) -> Perfil:
        return PRESETS[0]

    def listar(self) -> list[Perfil]:
        return list(self._usuarios().values())

    def listar_todos(self) -> list[Perfil]:
        usuarios = self._usuarios()
        return list(PRESETS) + [p for p in usuarios.values() if p.nombre not in NOMBRES_PRESET]

    def obtener(self, nombre: str) -> Perfil:
        preset = preset_por_nombre(nombre)
        if preset is not None:
            return preset
        usuarios = self._usuarios()
        if nombre not in usuarios:
            raise PerfilNoEncontrado(nombre)
        return usuarios[nombre]

    def guardar(self, perfil: Perfil, overwrite: bool = False) -> None:
        if perfil.nombre in NOMBRES_PRESET:
            raise PerfilProtegido(f"El preset '{perfil.nombre}' no se puede sobrescribir")
        usuarios = self._usuarios()
        if perfil.nombre in usuarios and not overwrite:
            raise PerfilYaExiste(perfil.nombre)
        usuarios[perfil.nombre] = perfil
        self._guardar_usuarios(usuarios)

    def eliminar(self, nombre: str) -> None:
        if nombre in NOMBRES_PRESET:
            raise PerfilProtegido(f"El preset '{nombre}' no se puede eliminar")
        usuarios = self._usuarios()
        if nombre not in usuarios:
            raise PerfilNoEncontrado(nombre)
        del usuarios[nombre]
        self._guardar_usuarios(usuarios)

    def renombrar(self, viejo: str, nuevo: str) -> None:
        nuevo = nuevo.strip()
        if not nuevo:
            raise ValueError("El nuevo nombre está vacío")
        if viejo in NOMBRES_PRESET or nuevo in NOMBRES_PRESET:
            raise PerfilProtegido("No se pueden renombrar presets de fábrica")
        usuarios = self._usuarios()
        if viejo not in usuarios:
            raise PerfilNoEncontrado(viejo)
        if nuevo in usuarios and nuevo != viejo:
            raise PerfilYaExiste(nuevo)
        perfil = usuarios.pop(viejo)
        usuarios[nuevo] = Perfil(
            nombre=nuevo,
            modulo_estilo=perfil.modulo_estilo,
            ojo_estilo=perfil.ojo_estilo,
            marco_tipo=perfil.marco_tipo,
            marco_texto=perfil.marco_texto,
            correccion=perfil.correccion,
            colores=perfil.colores,
            quiet_zone=perfil.quiet_zone,
        )
        self._guardar_usuarios(usuarios)

    def _usuarios(self) -> dict[str, Perfil]:
        if not self.ruta.exists():
            return {}
        crudo = self.ruta.read_text(encoding="utf-8")
        try:
            data = json.loads(crudo)
        except json.JSONDecodeError as exc:
            self._backup_corrupto()
            raise PerfilCorrupto(f"JSON inválido en {self.ruta}") from exc
        perfiles, migrar = _parse_almacen(data)
        if migrar:
            self._guardar_usuarios(perfiles)
        return perfiles

    def _guardar_usuarios(self, usuarios: dict[str, Perfil]) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "perfiles": {n: p.to_dict() for n, p in usuarios.items() if n not in NOMBRES_PRESET},
        }
        _atomic_write(self.ruta, json.dumps(payload, ensure_ascii=False, indent=2))

    def _backup_corrupto(self) -> None:
        bak = self.ruta.with_suffix(self.ruta.suffix + ".bak")
        if self.ruta.exists() and not bak.exists():
            bak.write_bytes(self.ruta.read_bytes())


def _parse_almacen(data: Any) -> tuple[dict[str, Perfil], bool]:
    if not isinstance(data, dict):
        raise PerfilCorrupto("El almacén de perfiles no es un objeto JSON")
    migrar = False
    if "schema_version" not in data and "perfiles" not in data:
        # v0: mapa plano nombre → perfil
        bloques = data
        migrar = True
    else:
        version = int(data.get("schema_version", 0))
        bloques = data.get("perfiles", {})
        if version < SCHEMA_VERSION:
            migrar = True
        if not isinstance(bloques, dict):
            raise PerfilCorrupto("La clave 'perfiles' debe ser un objeto")
    resultado: dict[str, Perfil] = {}
    for nombre, bloque in bloques.items():
        if nombre in NOMBRES_PRESET:
            continue
        if not isinstance(bloque, dict):
            raise PerfilCorrupto(f"Perfil {nombre!r} inválido")
        payload = dict(bloque)
        payload.setdefault("nombre", nombre)
        resultado[nombre] = Perfil.from_dict(payload)
    return resultado, migrar
