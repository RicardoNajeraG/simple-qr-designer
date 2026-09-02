# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller para QR Designer (tkinter + Pillow + segno)."""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.osx import BUNDLE
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules, copy_metadata

SPECDIR = Path(SPECPATH).resolve()
ROOT = SPECDIR.parent
SRC = ROOT / "src"

with (ROOT / "pyproject.toml").open("rb") as fh:
    VERSION = str(tomllib.load(fh)["project"]["version"])

ONEFILE = sys.platform == "win32"
CONSOLE = sys.platform.startswith("linux")
APP_NAME = "QR Designer" if sys.platform == "darwin" else "qr-designer"
ICON = os.environ.get("QR_DESIGNER_ICON") or ""

datas = collect_data_files("qr_designer")
binaries: list = []
hiddenimports = collect_submodules("qr_designer")

try:
    datas += copy_metadata("qr-designer")
except Exception:
    pass

pyproject = ROOT / "pyproject.toml"
if pyproject.is_file():
    datas.append((str(pyproject), "."))

for paquete in ("PIL", "segno"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(paquete)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

a = Analysis(
    [str(SRC / "qr_designer" / "__main__.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "_pytest", "zxingcpp"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe_kwargs = dict(
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
)
if ICON:
    exe_kwargs["icon"] = ICON

if ONEFILE:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        **exe_kwargs,
    )
    coll = None
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        **exe_kwargs,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        name=APP_NAME,
    )

if sys.platform == "darwin" and coll is not None:
    bundle_kwargs = {}
    if ICON:
        bundle_kwargs["icon"] = ICON
    BUNDLE(
        coll,
        name="QR Designer.app",
        bundle_identifier="com.ricardonajera.qrdesigner",
        version=VERSION,
        info_plist={
            "CFBundleName": "QR Designer",
            "CFBundleDisplayName": "QR Designer",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
        },
        **bundle_kwargs,
    )
