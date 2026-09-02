"""Tests de la capa escena: estilos, ojos, quiet zone y marcos."""

from __future__ import annotations

import pytest

from qr_designer.config.models import (
    ColorScheme,
    MarcoTipo,
    ModuloEstilo,
    OjoEstilo,
    Perfil,
)
from qr_designer.core.encoder import TipoModulo, codificar
from qr_designer.scene.builders import (
    FRAME_GROSOR,
    MARCO_TEXTO_DEFECTO,
    RADIO_PUNTO,
    TEXT_BANDA,
    celdas_tinta_modulo,
    construir_escena,
)
from qr_designer.scene.primitives import Circle, Imagen, Path, Rect, Text


def _perfil(**kwargs) -> Perfil:
    kwargs.setdefault("nombre", "t")
    return Perfil(**kwargs)


def _escena(contenido: str = "HI", **kwargs):
    perfil = _perfil(**kwargs)
    matriz = codificar(contenido, perfil.correccion)
    return construir_escena(matriz, perfil), matriz, perfil


@pytest.mark.unit
def test_cuadrado_genera_rects_por_modulo_oscuro_de_datos() -> None:
    escena, matriz, _ = _escena(modulo_estilo=ModuloEstilo.CUADRADO)
    mods = [i for i in escena.items if i.role == "modulo"]
    assert mods
    assert all(isinstance(i, Rect) for i in mods)
    assert all(i.rx == 0 and i.w == 1 and i.h == 1 for i in mods)  # type: ignore[union-attr]
    assert len(mods) == celdas_tinta_modulo(matriz)


@pytest.mark.unit
def test_puntos_son_circulos_con_radio_menor_que_medio_modulo() -> None:
    escena, _, _ = _escena(modulo_estilo=ModuloEstilo.PUNTOS)
    mods = [i for i in escena.items if i.role == "modulo"]
    assert mods
    assert all(isinstance(i, Circle) for i in mods)
    assert all(i.r < 0.5 for i in mods)  # type: ignore[union-attr]
    assert all(i.r == pytest.approx(RADIO_PUNTO) for i in mods)  # type: ignore[union-attr]


@pytest.mark.unit
def test_gota_y_squircle_son_paths() -> None:
    for estilo in (ModuloEstilo.GOTA, ModuloEstilo.SQUIRCLE):
        escena, _, _ = _escena(modulo_estilo=estilo)
        mods = [i for i in escena.items if i.role == "modulo"]
        assert mods
        assert all(isinstance(i, Path) for i in mods)
        assert all(len(i.points) >= 8 for i in mods)  # type: ignore[union-attr]


@pytest.mark.unit
def test_barras_h_fusionan_vecinos() -> None:
    escena, matriz, _ = _escena(modulo_estilo=ModuloEstilo.BARRAS_H)
    mods = [i for i in escena.items if i.role == "modulo"]
    assert mods
    assert all(isinstance(i, Rect) for i in mods)
    n_celdas = celdas_tinta_modulo(matriz)
    assert len(mods) < n_celdas
    assert any(i.w > 1 for i in mods)  # type: ignore[union-attr]


@pytest.mark.unit
def test_barras_v_fusionan_vecinos() -> None:
    escena, matriz, _ = _escena(modulo_estilo=ModuloEstilo.BARRAS_V)
    mods = [i for i in escena.items if i.role == "modulo"]
    n_celdas = celdas_tinta_modulo(matriz)
    assert len(mods) < n_celdas
    assert any(i.h > 1 for i in mods)  # type: ignore[union-attr]


@pytest.mark.unit
def test_ojos_independientes_del_estilo_de_modulo() -> None:
    a, _, _ = _escena(modulo_estilo=ModuloEstilo.PUNTOS, ojo_estilo=OjoEstilo.CUADRADO)
    b, _, _ = _escena(modulo_estilo=ModuloEstilo.PUNTOS, ojo_estilo=OjoEstilo.CIRCULO)
    ojos_a = a.por_rol("ojo")
    ojos_b = b.por_rol("ojo")
    assert len(ojos_a) == 3
    assert len(ojos_b) == 3
    assert all(isinstance(i, Rect) for i in ojos_a)
    assert all(isinstance(i, Circle) for i in ojos_b)
    # los módulos siguen siendo círculos en ambos
    assert all(isinstance(i, Circle) for i in a.por_rol("modulo"))


@pytest.mark.unit
def test_separadores_no_generan_tinta() -> None:
    escena, matriz, _ = _escena("HI")
    ox, oy = escena.origen_qr
    posiciones_modulo = set()
    for item in escena.por_rol("modulo"):
        if isinstance(item, Rect):
            # puede ser barra: cubrir varias celdas
            x0 = int(round(item.x - ox))
            y0 = int(round(item.y - oy))
            for dy in range(int(round(item.h))):
                for dx in range(int(round(item.w))):
                    posiciones_modulo.add((x0 + dx, y0 + dy))
        elif isinstance(item, Circle):
            posiciones_modulo.add((int(round(item.cx - ox - 0.5)), int(round(item.cy - oy - 0.5))))
        elif isinstance(item, Path):
            xs = [p[0] for p in item.points]
            ys = [p[1] for p in item.points]
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            posiciones_modulo.add((int(round(cx - ox - 0.5)), int(round(cy - oy - 0.5))))
    for y in range(matriz.size):
        for x in range(matriz.size):
            if matriz.tipo(x, y) is TipoModulo.SEPARADOR:
                assert (x, y) not in posiciones_modulo
            if matriz.tipo(x, y) is TipoModulo.FINDER:
                assert (x, y) not in posiciones_modulo


@pytest.mark.unit
def test_quiet_zone_sin_marco() -> None:
    escena, matriz, perfil = _escena(marco_tipo=MarcoTipo.NINGUNO)
    n = matriz.size
    q = perfil.quiet_zone
    assert q >= 4
    assert escena.width == n + 2 * q
    assert escena.height == n + 2 * q
    assert escena.origen_qr == (q, q)
    assert escena.pad == (0.0, 0.0, 0.0, 0.0)


@pytest.mark.unit
def test_marco_no_recorta_quiet_zone() -> None:
    escena, matriz, perfil = _escena(marco_tipo=MarcoTipo.PERIMETRO)
    n = matriz.size
    q = perfil.quiet_zone
    inner = n + 2 * q
    assert escena.pad[0] == FRAME_GROSOR
    assert escena.width == inner + 2 * FRAME_GROSOR
    assert escena.origen_qr == (FRAME_GROSOR + q, FRAME_GROSOR + q)
    # el hueco del marco coincide con inner (quiet + módulos)
    hueco = next(i for i in escena.items if i.id == "marco-hueco")
    assert isinstance(hueco, Rect)
    assert hueco.x == pytest.approx(FRAME_GROSOR)
    assert hueco.w == pytest.approx(inner)
    assert hueco.h == pytest.approx(inner)


@pytest.mark.unit
def test_escaneame_anade_banda_y_texto() -> None:
    escena, matriz, perfil = _escena(marco_tipo=MarcoTipo.ESCANEAME, marco_texto=None)
    n = matriz.size
    q = perfil.quiet_zone
    inner = n + 2 * q
    assert escena.height == pytest.approx(inner + 2 * FRAME_GROSOR + TEXT_BANDA)
    textos = [i for i in escena.items if isinstance(i, Text)]
    assert len(textos) == 1
    assert textos[0].text == MARCO_TEXTO_DEFECTO
    # el texto vive debajo del inner, no encima de los módulos
    ox, oy = escena.origen_qr
    assert textos[0].y > oy + n


@pytest.mark.unit
def test_texto_vacio_usa_default_y_largo_se_trunca() -> None:
    corta, _, _ = _escena(marco_tipo=MarcoTipo.ESCANEAME, marco_texto="   ")
    larga, _, _ = _escena(
        marco_tipo=MarcoTipo.ESCANEAME,
        marco_texto="A" * 200,
    )
    t0 = next(i for i in corta.items if isinstance(i, Text))
    t1 = next(i for i in larga.items if isinstance(i, Text))
    assert t0.text == MARCO_TEXTO_DEFECTO
    assert t1.text.endswith("…")
    assert len(t1.text) < 50


@pytest.mark.unit
def test_cambio_solo_de_color_preserva_geometria() -> None:
    m = codificar("https://example.com")
    a = construir_escena(
        m,
        _perfil(colores=ColorScheme(fondo="#ffffff", modulos="#000000", ojos="#111111")),
    )
    b = construir_escena(
        m,
        _perfil(colores=ColorScheme(fondo="#ffffee", modulos="#aa0000", ojos="#0000aa")),
    )
    assert a.geometry() == b.geometry()
    assert a.ids() == b.ids()
    fills_a = tuple(getattr(i, "fill") for i in a.items)
    fills_b = tuple(getattr(i, "fill") for i in b.items)
    assert fills_a != fills_b


@pytest.mark.unit
def test_matriz_minima_version_1() -> None:
    escena, matriz, _ = _escena("HI")
    assert matriz.version == 1
    assert matriz.size == 21
    assert escena.module_count == 21
    assert len(escena.por_rol("ojo")) == 3
    assert len(escena.por_rol("pupila")) == 3
    assert escena.por_rol("logo") == ()
    assert escena.por_rol("logo_fondo") == ()


@pytest.mark.unit
def test_escena_con_logo_centrado_en_matriz(tmp_path) -> None:
    from tests.png_bytes import escribir_png

    ruta = escribir_png(tmp_path / "logo.png", 8, 8)
    escena, matriz, _ = _escena("HI", logo_path=str(ruta))
    fondos = escena.por_rol("logo_fondo")
    logos = escena.por_rol("logo")
    assert len(fondos) == 1 and len(logos) == 1
    assert isinstance(fondos[0], Rect)
    assert isinstance(logos[0], Imagen)
    ox, oy = escena.origen_qr
    n = matriz.size
    item = logos[0]
    assert item.x >= ox + 8 - 1e-6
    assert item.y >= oy + 8 - 1e-6
    assert item.x + item.w <= ox + n - 8 + 1e-6
    assert item.y + item.h <= oy + n + 1e-6
    assert item.x + item.w / 2 == pytest.approx(ox + n / 2)
    assert item.ruta == str(ruta)


@pytest.mark.unit
def test_logo_inexistente_no_rompe_escena() -> None:
    escena, _, _ = _escena("HI", logo_path="/no/existe/marca.png")
    assert escena.por_rol("logo") == ()
    assert escena.por_rol("logo_fondo") == ()


@pytest.mark.unit
def test_escena_con_logo_id_de_catalogo(tmp_path, monkeypatch) -> None:
    from qr_designer.logos import LogoDesconocido
    from tests.png_bytes import escribir_png

    ruta = escribir_png(tmp_path / "wifi.png", 8, 8)

    def _resolver(ident: str, raiz=None):
        if ident == "wifi":
            return ruta
        raise LogoDesconocido(ident)

    monkeypatch.setattr("qr_designer.logos.resolver_logo", _resolver)
    escena, _, _ = _escena("HI", logo_id="wifi")
    logos = escena.por_rol("logo")
    assert len(logos) == 1
    assert isinstance(logos[0], Imagen)
    assert logos[0].ruta == str(ruta)


@pytest.mark.unit
def test_logo_id_gana_sobre_logo_path(tmp_path, monkeypatch) -> None:
    from qr_designer.logos import LogoDesconocido
    from tests.png_bytes import escribir_png

    catalogo = escribir_png(tmp_path / "wifi.png", 8, 8)
    extra = escribir_png(tmp_path / "otro.png", 8, 8)

    def _resolver(ident: str, raiz=None):
        if ident == "wifi":
            return catalogo
        raise LogoDesconocido(ident)

    monkeypatch.setattr("qr_designer.logos.resolver_logo", _resolver)
    escena, _, _ = _escena("HI", logo_id="wifi", logo_path=str(extra))
    assert escena.por_rol("logo")[0].ruta == str(catalogo)


@pytest.mark.unit
def test_logo_id_desconocido_no_usa_path(tmp_path, monkeypatch) -> None:
    from qr_designer.logos import LogoDesconocido
    from tests.png_bytes import escribir_png

    extra = escribir_png(tmp_path / "otro.png", 8, 8)

    def _resolver(ident: str, raiz=None):
        raise LogoDesconocido(ident)

    monkeypatch.setattr("qr_designer.logos.resolver_logo", _resolver)
    escena, _, _ = _escena("HI", logo_id="nope", logo_path=str(extra))
    assert escena.por_rol("logo") == ()
