"""Pinta una Escena en un tk.Canvas. Importar este módulo carga tkinter."""

from __future__ import annotations

from qr_designer.render.preview import PREVIEW_MAX_LADO, px_para_preview
from qr_designer.scene.primitives import Circle, Escena, Path, Rect, Text


def escala_preview(escena: Escena, max_lado: float = PREVIEW_MAX_LADO) -> float:
    return float(px_para_preview(escena, max_lado))


def pintar_canvas(
    canvas,
    escena: Escena,
    scale: float | None = None,
    lienzo: int | None = None,
) -> float:
    max_lado = float(lienzo) if lienzo else PREVIEW_MAX_LADO
    if scale is None:
        scale = escala_preview(escena, max_lado)
    w = max(1, round(escena.width * scale))
    h = max(1, round(escena.height * scale))
    canvas.delete("all")
    canvas.config(width=w, height=h)
    canvas.create_rectangle(
        0,
        0,
        w,
        h,
        fill=escena.background,
        outline="",
        tags=("fondo",),
    )
    for item in escena.items:
        tags = (item.role, item.id)
        if isinstance(item, Rect):
            canvas.create_rectangle(
                item.x * scale,
                item.y * scale,
                (item.x + item.w) * scale,
                (item.y + item.h) * scale,
                fill=item.fill,
                outline="",
                tags=tags,
            )
        elif isinstance(item, Circle):
            r = item.r * scale
            canvas.create_oval(
                item.cx * scale - r,
                item.cy * scale - r,
                item.cx * scale + r,
                item.cy * scale + r,
                fill=item.fill,
                outline="",
                tags=tags,
            )
        elif isinstance(item, Path):
            coords: list[float] = []
            for x, y in item.points:
                coords.extend((x * scale, y * scale))
            if len(coords) >= 6:
                canvas.create_polygon(*coords, fill=item.fill, outline="", tags=tags)
        elif isinstance(item, Text):
            canvas.create_text(
                item.x * scale,
                item.y * scale,
                text=item.text,
                fill=item.fill,
                font=("TkDefaultFont", max(8, int(item.font_size * scale))),
                anchor="center",
                tags=tags,
            )
    return scale


def recolorear(canvas, role: str, color: str) -> None:
    canvas.itemconfig(role, fill=color)
    if role == "fondo":
        canvas.itemconfig("ojo_hueco", fill=color)
        canvas.itemconfig("marco_hueco", fill=color)
