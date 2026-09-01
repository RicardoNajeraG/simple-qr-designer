"""Nunito empaquetada (OFL-1.1) y registro por proceso en cada SO."""

from __future__ import annotations

from pathlib import Path
import sys
import tkinter as tk
from tkinter import font as tkfont

FAMILIA = "Nunito"
_DIR = Path(__file__).resolve().parent
RUTA_REGULAR = _DIR / "Nunito-Regular.ttf"
RUTA_BOLD = _DIR / "Nunito-Bold.ttf"
RUTA_OFL = _DIR / "OFL.txt"

_registrado = False


def registrar_fuentes() -> bool:
    """Registra Regular y Bold para este proceso. Idempotente; no lanza."""
    global _registrado
    if _registrado:
        return True
    ok = False
    for path in (RUTA_REGULAR, RUTA_BOLD):
        if path.is_file() and _registrar_archivo(path):
            ok = True
    _registrado = ok
    return ok


def familia_activa(root: tk.Misc, fallbacks: tuple[str, ...] = ()) -> str:
    registrar_fuentes()
    try:
        disponibles = set(tkfont.families(root))
    except tk.TclError:
        disponibles = set()
    if FAMILIA in disponibles:
        return FAMILIA
    for nombre in disponibles:
        compacto = nombre.replace(" ", "").lower()
        if compacto.startswith("nunito"):
            return nombre
    for nombre in fallbacks:
        if nombre in disponibles:
            return nombre
    return "TkDefaultFont"


def _registrar_archivo(path: Path) -> bool:
    plat = sys.platform
    try:
        if plat == "win32":
            return _registrar_windows(path)
        if plat == "darwin":
            return _registrar_macos(path)
        return _registrar_fontconfig(path)
    except Exception:
        return False


def _registrar_windows(path: Path) -> bool:
    import ctypes

    fr_private = 0x10
    gdi32 = ctypes.WinDLL("gdi32")
    gdi32.AddFontResourceExW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint,
        ctypes.c_void_p,
    ]
    gdi32.AddFontResourceExW.restype = ctypes.c_int
    return gdi32.AddFontResourceExW(str(path), fr_private, None) > 0


def _registrar_macos(path: Path) -> bool:
    import ctypes
    from ctypes import c_bool, c_char_p, c_int32, c_long, c_void_p

    cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    ct = ctypes.CDLL("/System/Library/Frameworks/CoreText.framework/CoreText")
    cf.CFURLCreateFromFileSystemRepresentation.argtypes = [
        c_void_p,
        c_char_p,
        c_long,
        c_bool,
    ]
    cf.CFURLCreateFromFileSystemRepresentation.restype = c_void_p
    ct.CTFontManagerRegisterFontsForURL.argtypes = [c_void_p, c_int32, c_void_p]
    ct.CTFontManagerRegisterFontsForURL.restype = c_bool
    raw = str(path).encode("utf-8")
    url = cf.CFURLCreateFromFileSystemRepresentation(None, raw, len(raw), False)
    if not url:
        return False
    # kCTFontManagerScopeProcess = 1
    return bool(ct.CTFontManagerRegisterFontsForURL(url, 1, None))


def _registrar_fontconfig(path: Path) -> bool:
    import ctypes
    from ctypes.util import find_library

    nombre = find_library("fontconfig") or "libfontconfig.so.1"
    lib = ctypes.CDLL(nombre)
    lib.FcInit.restype = ctypes.c_int
    lib.FcConfigGetCurrent.restype = ctypes.c_void_p
    lib.FcConfigAppFontAddFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.FcConfigAppFontAddFile.restype = ctypes.c_int
    lib.FcInit()
    cfg = lib.FcConfigGetCurrent()
    if not cfg:
        return False
    ok = bool(lib.FcConfigAppFontAddFile(cfg, str(path).encode("utf-8")))
    try:
        lib.FcConfigBuildFonts.argtypes = [ctypes.c_void_p]
        lib.FcConfigBuildFonts.restype = ctypes.c_int
        lib.FcConfigBuildFonts(cfg)
    except Exception:
        pass
    return ok
