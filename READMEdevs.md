# Simple QR Designer — documentación para desarrollo

Guía técnica del repositorio. La presentación del producto, la instalación para usuarios y el uso de la GUI/CLI están en [`README.md`](README.md).

## Requisitos de entorno

- Python ≥ 3.11
- Dependencia de runtime: [`segno`](https://pypi.org/project/segno/)
- GUI: tkinter (stdlib)
- Extra opcional: Pillow para PNG/WEBP (también para la vista previa a la misma calidad que el export)

```bash
uv sync
# PNG / WEBP:
uv sync --extra raster
# tests de decodificación:
uv sync --extra raster --extra decode --extra dev
```

## Arquitectura

```
contenido + perfil dict
        → service (fachada JSON-friendly)
            → MatrizQR (segno) → Escena
                → SVG | Pillow (export y preview)
        → ui/viewmodel → GUI tkinter
```

La carpeta `src/qr_designer/service/` es el contrato previsto para un backend HTTP (FastAPI u otro) y un frontend web: entradas y salidas son `str`, `dict` y `bytes`. No hay tkinter ahí. Hoy lo consumen la GUI de escritorio y la CLI; mañana un servidor puede exponer los mismos métodos sin reescribir el núcleo.

El raster **no** pasa por SVG. Estilos con curvas se supersamplean (y se reducen con LANCZOS) para anti-aliasing; el estilo clásico (rectángulos) sigue el fast path de paleta exacta. La quiet zone (≥ 4 módulos) no la recorta el marco. En preview se respeta la ECC del perfil; si está en `auto`, la elevación ocurre solo al exportar.

El ícono de ventana es el mapache en PNG preescalados (`qr-designer-icon-32/64/256.png`). La cabecera usa `qr-designer-pet` y el banner ilustrado (sin texto «QR Designer»). La UI usa **Nunito** empaquetada (SIL OFL 1.1, TTF estáticos Regular/Bold) registrada en el proceso; si el registro falla, se cae a Segoe UI / SF Pro Text / Ubuntu. `tk scaling` se ajusta al DPI. Fondo blanco (`#ffffff`) como las ilustraciones.

Perfiles de usuario (schema versionado, escritura atómica). Los 5 presets de fábrica son de solo lectura. Rutas de `profiles.json` y migración del legado: ver [`README.md`](README.md#perfiles).

### Backend futuro

Sin añadir dependencias ahora. El mapeo natural sería:

| HTTP (previsto) | Servicio actual |
|---|---|
| `POST /qr` body `{contenido, perfil, formato, px}` | `qr_service.exportar_qr` |
| `POST /qr.svg` | `qr_service.generar_svg` |
| `POST /evaluar` | `qr_service.evaluar` |
| `GET/PUT/DELETE /perfiles` | `ProfileService` |

El frontend web llamaría a ese API y no necesitaría instalar Python ni descargar el escritorio.

## Tests

```bash
uv run pytest
uv run pytest -m unit
uv run pytest -m integration
# regenerar goldens SVG
UPDATE_GOLDEN=1 uv run pytest tests/unit_tests/test_svg.py
```

Marcadores: `unit`, `integration`, `raster` (Pillow), `decode` (zxing-cpp), `gui` (DISPLAY + tkinter).

## Publicar una versión

Al hacer push a `master` o `main` con un cambio de `version` en `pyproject.toml`, CI corre los tests y sube a [GitHub Releases](https://github.com/RicardoNajeraG/simple-qr-designer/releases) un `.exe` (Windows), un `.deb` (Linux) y un `.dmg` (macOS).

La primera vez, o si quieres regenerar la versión actual sin subir el número: **Actions → Release → Run workflow** y marca `force`.

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
| Paleta PNG con colores reales | `test_png_paleta_colores_exactos` (estilo cuadrado) |
| PNG con logo centrado sigue siendo escaneable | `test_roundtrip_con_logo_central`, `test_logo.py` (caja segura) |
| Preview = mismo raster que export | `test_preview.py` |
| PNG/WEBP no se guardan como SVG | `test_export_dialog.py` (`resolver_export`, `filetypes_para`) |
| Diálogo de guardado muestra el formato elegido | `test_filetypes_png_primero` |
| Export PNG no se queda en «Exportando…» | `test_export_png_no_se_queda_exportando` |
| Texto plano (no URL) se codifica y se lee | `test_roundtrip_texto_plano_no_url` |
| Ícono, Nunito OFL, cabecera ilustrada y fondo blanco | `test_theme.py` |
| Fachada lista para backend | `test_service.py` |

## Checklist manual (dispositivo)

Lo único no automatizable. Antes de un release, imprimir o mostrar en pantalla y escanear con 2–3 apps de cámara:

1. Preset **Clásico**, URL corta, ECC M.
2. **Puntos** + ojos círculo, ECC H, fondo blanco.
3. **Gota** + ojos hoja, marco perímetro.
4. Contraste justo (módulos gris oscuro sobre blanco).
5. Marco «Escanéame» con texto largo truncado.
6. PNG ~8 px/módulo y el mismo diseño en SVG abierto en el navegador.
7. QR invertido (fondo negro, módulos blancos): confirmar que la UI advierte; no hace falta que todas las apps lo lean.
8. Logotipo PNG o SVG en el centro (ECC efectiva H): escanear con 2 apps.

Si un caso de estilo nuevo rompe el escaneo, añadirlo a `test_roundtrip.py` y, si hace falta, a la política de ECC recomendada en `config/contrast.py`.
