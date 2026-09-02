"""Genera el instalador nativo de la plataforma actual en dist/release/."""

from __future__ import annotations

import os
import platform
import shutil
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DIST = RAIZ / "dist"
RELEASE = DIST / "release"
BUILD = RAIZ / "build"
ASSETS = RAIZ / "src" / "qr_designer" / "ui" / "assets"
ICONO_PNG = ASSETS / "qr-designer-icon-256.png"
DESKTOP = RAIZ / "packaging" / "linux" / "qr-designer.desktop"
SPEC = RAIZ / "packaging" / "qr-designer.spec"

ARCH_DEB = {
    "x86_64": "amd64",
    "amd64": "amd64",
    "aarch64": "arm64",
    "arm64": "arm64",
}


def version_proyecto() -> str:
    with (RAIZ / "pyproject.toml").open("rb") as fh:
        return str(tomllib.load(fh)["project"]["version"])


def etiqueta_arch() -> str:
    maquina = platform.machine().lower()
    if maquina in {"x86_64", "amd64"}:
        return "amd64"
    if maquina in {"aarch64", "arm64"}:
        return "arm64"
    return maquina or "unknown"


def correr(cmd: list[str], **kwargs) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kwargs)


def asegurar_icono() -> str | None:
    BUILD.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "win32":
            destino = BUILD / "qr-designer.ico"
            if not ICONO_PNG.is_file():
                return None
            from PIL import Image

            imagen = Image.open(ICONO_PNG)
            if imagen.mode not in {"RGB", "RGBA"}:
                imagen = imagen.convert("RGBA")
            imagen.save(
                destino,
                format="ICO",
                sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)],
            )
            return str(destino)
        if sys.platform == "darwin" and ICONO_PNG.is_file():
            destino = BUILD / "qr-designer.icns"
            iconset = BUILD / "qr-designer.iconset"
            if iconset.exists():
                shutil.rmtree(iconset)
            iconset.mkdir(parents=True)
            for lado in (16, 32, 64, 128, 256, 512):
                correr(
                    [
                        "sips",
                        "-z",
                        str(lado),
                        str(lado),
                        str(ICONO_PNG),
                        "--out",
                        str(iconset / f"icon_{lado}x{lado}.png"),
                    ]
                )
                retina = lado * 2
                if retina <= 1024:
                    correr(
                        [
                            "sips",
                            "-z",
                            str(retina),
                            str(retina),
                            str(ICONO_PNG),
                            "--out",
                            str(iconset / f"icon_{lado}x{lado}@2x.png"),
                        ]
                    )
            correr(["iconutil", "-c", "icns", str(iconset), "-o", str(destino)])
            return str(destino)
        return str(ICONO_PNG) if ICONO_PNG.is_file() else None
    except Exception as exc:
        print(f"Aviso: no se pudo generar el icono ({exc})", flush=True)
        return None


def pyinstaller(icono: str | None) -> None:
    env = os.environ.copy()
    if icono:
        env["QR_DESIGNER_ICON"] = icono
    correr(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            f"--distpath={DIST}",
            f"--workpath={BUILD / 'pyinstaller'}",
            str(SPEC),
        ],
        cwd=RAIZ,
        env=env,
    )


def empaquetar_windows(version: str) -> Path:
    exe = DIST / "qr-designer.exe"
    if not exe.is_file():
        raise FileNotFoundError(f"No está el exe de PyInstaller: {exe}")
    destino = RELEASE / f"qr-designer-{version}-windows-{etiqueta_arch()}.exe"
    shutil.copy2(exe, destino)
    return destino


def _chmod_exec(ruta: Path) -> None:
    modo = ruta.stat().st_mode
    ruta.chmod(modo | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def empaquetar_linux(version: str) -> Path:
    onedir = DIST / "qr-designer"
    binario = onedir / "qr-designer"
    if not binario.is_file():
        raise FileNotFoundError(f"No está el binario de PyInstaller: {binario}")
    arch = ARCH_DEB.get(platform.machine().lower(), "amd64")
    raiz_deb = BUILD / "deb" / "qr-designer"
    if raiz_deb.exists():
        shutil.rmtree(raiz_deb)
    lib = raiz_deb / "usr" / "lib" / "qr-designer"
    bin_dir = raiz_deb / "usr" / "bin"
    apps = raiz_deb / "usr" / "share" / "applications"
    icons = raiz_deb / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"
    debian = raiz_deb / "DEBIAN"
    for carpeta in (lib.parent, bin_dir, apps, icons, debian):
        carpeta.mkdir(parents=True, exist_ok=True)
    shutil.copytree(onedir, lib, dirs_exist_ok=True)
    _chmod_exec(lib / "qr-designer")
    wrapper = bin_dir / "qr-designer"
    wrapper.write_text(
        "#!/bin/sh\nexec /usr/lib/qr-designer/qr-designer \"$@\"\n",
        encoding="utf-8",
        newline="\n",
    )
    _chmod_exec(wrapper)
    if DESKTOP.is_file():
        shutil.copy2(DESKTOP, apps / "qr-designer.desktop")
    if ICONO_PNG.is_file():
        shutil.copy2(ICONO_PNG, icons / "qr-designer.png")
    control = debian / "control"
    control.write_text(
        "\n".join(
            [
                "Package: qr-designer",
                f"Version: {version}",
                "Section: graphics",
                "Priority: optional",
                f"Architecture: {arch}",
                "Maintainer: Ricardo Nájera <ricardonajera93@gmail.com>",
                "Depends: libx11-6, libxext6, libxrender1, libxft2, libxss1, libfontconfig1, libfreetype6, libxcb1",
                "Homepage: https://github.com/RicardoNajeraG/simple-qr-designer",
                "Description: Generador de códigos QR personalizable, rápido y liviano",
                " Aplicación de escritorio (GUI y CLI) para diseñar y exportar códigos QR.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    destino = RELEASE / f"qr-designer-{version}-linux-{arch}.deb"
    correr(
        [
            "dpkg-deb",
            "--build",
            "--root-owner-group",
            str(raiz_deb),
            str(destino),
        ]
    )
    return destino


def empaquetar_macos(version: str) -> Path:
    app = DIST / "QR Designer.app"
    if not app.is_dir():
        raise FileNotFoundError(f"No está el bundle de PyInstaller: {app}")
    staging = BUILD / "dmg"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    shutil.copytree(app, staging / "QR Designer.app")
    (staging / "Applications").symlink_to("/Applications")
    destino = RELEASE / f"qr-designer-{version}-macos-{etiqueta_arch()}.dmg"
    if destino.exists():
        destino.unlink()
    correr(
        [
            "hdiutil",
            "create",
            "-volname",
            "QR Designer",
            "-srcfolder",
            str(staging),
            "-ov",
            "-format",
            "UDZO",
            str(destino),
        ]
    )
    return destino


def main() -> None:
    version = version_proyecto()
    RELEASE.mkdir(parents=True, exist_ok=True)
    icono = asegurar_icono()
    pyinstaller(icono)
    if sys.platform == "win32":
        artefacto = empaquetar_windows(version)
    elif sys.platform == "darwin":
        artefacto = empaquetar_macos(version)
    elif sys.platform.startswith("linux"):
        artefacto = empaquetar_linux(version)
    else:
        raise SystemExit(f"Plataforma no soportada: {sys.platform}")
    print(f"Artefacto: {artefacto} ({artefacto.stat().st_size} bytes)", flush=True)


if __name__ == "__main__":
    main()
