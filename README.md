# QR Designer

Generador de códigos QR personalizable para escritorio. Prioridad: **rápido y liviano**. La edición vive en una escena vectorial en memoria; Pillow solo se carga al exportar PNG/WEBP.

- Python ≥ 3.11
- Dependencia de runtime: [`segno`](https://pypi.org/project/segno/)
- GUI: tkinter (stdlib)
- Extra opcional: Pillow para PNG/WEBP

## Instalación

```bash
uv sync
# PNG / WEBP:
uv sync --extra raster
# tests de decodificación:
uv sync --extra raster --extra decode --extra dev
```

## Uso

```bash
# GUI (perfil Clásico ya aplicado)
uv run qr-designer

# CLI
uv run qr-designer --url "https://example.com" -o qr.svg
uv run qr-designer --url "https://example.com" --preset Puntos -o qr.png --px 8
```

Flujo de la GUI: pegar URL → el QR con el perfil por defecto ya está listo → **Exportar imagen**. Personalizar actualiza la vista previa en vivo. **Guardar perfil** es otra acción; el perfil nunca incluye la URL.

Los parámetros técnicos (corrección de errores, píxeles por módulo) están en **Avanzado**, colapsado por defecto.

## Arquitectura

```
contenido + perfil → MatrizQR (segno) → Escena (primitivas)
                                      → SVG | Canvas tkinter | Pillow
```

El raster **no** pasa por SVG. La quiet zone (≥ 4 módulos) no la recorta el marco. En preview se respeta la ECC del perfil; si está en `auto`, la elevación ocurre solo al exportar.

Perfiles de usuario: `~/.qr_designer/profiles.json` (schema versionado, escritura atómica). Los 5 presets de fábrica son de solo lectura.

## Tests

```bash
uv run pytest
uv run pytest -m unit
uv run pytest -m integration
# regenerar goldens SVG
UPDATE_GOLDEN=1 uv run pytest tests/unit_tests/test_svg.py
```

Marcadores: `unit`, `integration`, `raster` (Pillow), `decode` (zxing-cpp), `gui` (DISPLAY + tkinter).

## Criterios de aceptación → tests

| Criterio | Cómo se certifica |
|---|---|
| Combinaciones de estilo siguen siendo escaneables | `tests/integration_tests/test_roundtrip.py` (ZXing, pairwise + puntos/gota con ECC H + contraste ~3:1) |
| Arranque / generación liviana | `test_presupuestos.py` (matriz+SVG y rebuild de perfil < 200 ms en CI; meta local 50 ms) |
| Ningún import pesado en edición | `test_export.py::test_import_scene_svg_cli_no_carga_pillow` y `test_import_cli_no_carga_tkinter` |
| Guardar/cargar perfil sin reiniciar | `test_profiles.py`, `test_perfiles_flujo.py` |
| Tres formatos desde «Exportar imagen» | GUI con un botón; CLI `-o .svg/.png/.webp`; `test_cli.py`, `test_export.py` |
| Peso del archivo tras exportar | CLI imprime bytes; GUI lo muestra en la barra de estado; `test_cli_svg_reporta_peso` |
| URL → QR con default → exportar ≤ 2 clics | `test_viewmodel.py::test_rux01_url_deja_exportable_con_perfil_default` |
| Preview en vivo, debounce | `test_rux02_debounce_coalesce_rebuilds` |
| Advertencia de contraste no bloqueante | `test_rf08_advertencia_no_bloquea_export` |
| Quiet zone intocable | `test_scene.py::test_marco_no_recorta_quiet_zone` |
| Paleta PNG con colores reales | `test_png_paleta_colores_exactos` |

## Checklist manual (dispositivo)

Lo único no automatizable. Antes de un release, imprimir o mostrar en pantalla y escanear con 2–3 apps de cámara:

1. Preset **Clásico**, URL corta, ECC M.
2. **Puntos** + ojos círculo, ECC H, fondo blanco.
3. **Gota** + ojos hoja, marco perímetro.
4. Contraste justo (módulos gris oscuro sobre blanco).
5. Marco «Escanéame» con texto largo truncado.
6. PNG ~8 px/módulo y el mismo diseño en SVG abierto en el navegador.
7. QR invertido (fondo negro, módulos blancos): confirmar que la UI advierte; no hace falta que todas las apps lo lean.

Si un caso de estilo nuevo rompe el escaneo, añadirlo a `test_roundtrip.py` y, si hace falta, a la política de ECC recomendada en `config/contrast.py`.
