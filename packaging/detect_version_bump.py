"""Compara project.version entre el commit actual y un ref anterior."""

from __future__ import annotations

import argparse
import subprocess
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def version_desde_texto(texto: str) -> str:
    return str(tomllib.loads(texto)["project"]["version"])


def version_en_ref(ref: str) -> str | None:
    compacto = ref.strip()
    if not compacto or set(compacto) <= {"0"}:
        return None
    try:
        crudo = subprocess.check_output(
            ["git", "show", f"{compacto}:pyproject.toml"],
            cwd=RAIZ,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    try:
        return version_desde_texto(crudo.decode("utf-8"))
    except (tomllib.TOMLDecodeError, KeyError, UnicodeDecodeError):
        return None


def version_actual() -> str:
    return version_desde_texto((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--before",
        default="",
        help="SHA o ref del commit anterior (github.event.before o HEAD^)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Publicar aunque la versión no haya cambiado",
    )
    parser.add_argument(
        "--github-output",
        default="",
        help="Ruta de $GITHUB_OUTPUT si corre en Actions",
    )
    args = parser.parse_args()

    nueva = version_actual()
    anterior = version_en_ref(args.before)
    publicar = bool(args.force) or anterior != nueva
    lineas = [
        f"version={nueva}",
        f"previous_version={anterior or ''}",
        f"should_release={'true' if publicar else 'false'}",
    ]
    texto = "\n".join(lineas) + "\n"
    print(texto, end="")
    if args.github_output:
        Path(args.github_output).open("a", encoding="utf-8").write(texto)


if __name__ == "__main__":
    main()
