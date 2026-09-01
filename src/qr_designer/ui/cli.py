"""Punto de entrada CLI. Imports pesados (tkinter, Pillow) van dentro de ramas."""

from __future__ import annotations

import sys
from typing import Sequence


def main(argv: Sequence[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"--gui", "-g"}:
        from qr_designer.ui.gui import run_gui

        run_gui()
        return
    from qr_designer.ui.cli_export import exportar_desde_argv

    raise SystemExit(exportar_desde_argv(args))
