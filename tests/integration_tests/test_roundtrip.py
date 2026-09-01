"""Round-trip de decodificación por pares de estilo."""

from __future__ import annotations

from io import BytesIO

import pytest

from qr_designer.config.models import (
    ColorScheme,
    Correccion,
    MarcoTipo,
    ModuloEstilo,
    OjoEstilo,
    Perfil,
    SolicitudQR,
)
from qr_designer.export.exporter import exportar

PAYLOAD = "https://example.com/qr-designer-test"
PAYLOAD_TEXTO = "Hola mundo, esto no es una URL"


def _casos_pairwise() -> list[tuple]:
    mods = list(ModuloEstilo)
    ojos = list(OjoEstilo)
    marcos = list(MarcoTipo)
    eccs = [Correccion.L, Correccion.M, Correccion.Q, Correccion.H]
    casos: list[tuple] = []
    for i, m in enumerate(mods):
        casos.append((m, ojos[i % len(ojos)], MarcoTipo.NINGUNO, Correccion.M))
    for i, o in enumerate(ojos):
        casos.append((ModuloEstilo.CUADRADO, o, marcos[i % len(marcos)], Correccion.Q))
    for i, f in enumerate(marcos):
        casos.append((mods[i % len(mods)], OjoEstilo.CUADRADO, f, eccs[i % len(eccs)]))
    for e in eccs:
        casos.append((ModuloEstilo.CUADRADO, OjoEstilo.CUADRADO, MarcoTipo.NINGUNO, e))
    casos.append((ModuloEstilo.PUNTOS, OjoEstilo.CIRCULO, MarcoTipo.NINGUNO, Correccion.H))
    casos.append((ModuloEstilo.GOTA, OjoEstilo.HOJA, MarcoTipo.PERIMETRO, Correccion.H))
    casos.append((ModuloEstilo.BARRAS_H, OjoEstilo.SQUIRCLE, MarcoTipo.BANDA, Correccion.H))
    return list(dict.fromkeys(casos))


def _decodificar_png(datos: bytes) -> str:
    zxingcpp = pytest.importorskip("zxingcpp")
    from PIL import Image

    img = Image.open(BytesIO(datos)).convert("RGB")
    encontrados = zxingcpp.read_barcodes(img)
    assert encontrados, "ZXing no leyó ningún código"
    return encontrados[0].text


@pytest.mark.integration
@pytest.mark.decode
@pytest.mark.raster
@pytest.mark.parametrize(
    "modulo,ojo,marco,ecc",
    _casos_pairwise(),
    ids=lambda v: getattr(v, "value", str(v)),
)
def test_roundtrip_pairwise(modulo, ojo, marco, ecc) -> None:
    pytest.importorskip("PIL")
    pytest.importorskip("zxingcpp")
    perfil = Perfil(
        nombre="t",
        modulo_estilo=modulo,
        ojo_estilo=ojo,
        marco_tipo=marco,
        correccion=ecc,
    )
    r = exportar(SolicitudQR(PAYLOAD, perfil), "png", px_modulo=10)
    assert _decodificar_png(r.datos) == PAYLOAD


@pytest.mark.integration
@pytest.mark.decode
@pytest.mark.raster
def test_roundtrip_contraste_limite_3_a_1() -> None:
    pytest.importorskip("PIL")
    pytest.importorskip("zxingcpp")
    perfil = Perfil(
        nombre="t",
        correccion=Correccion.H,
        colores=ColorScheme(fondo="#ffffff", modulos="#767676", ojos="#767676", marco="#767676"),
    )
    r = exportar(SolicitudQR(PAYLOAD, perfil), "png", px_modulo=12)
    assert _decodificar_png(r.datos) == PAYLOAD


@pytest.mark.integration
@pytest.mark.decode
@pytest.mark.raster
def test_roundtrip_puntos_ecc_h() -> None:
    pytest.importorskip("PIL")
    pytest.importorskip("zxingcpp")
    perfil = Perfil(
        nombre="t",
        modulo_estilo=ModuloEstilo.PUNTOS,
        ojo_estilo=OjoEstilo.CIRCULO,
        correccion=Correccion.H,
    )
    r = exportar(SolicitudQR(PAYLOAD, perfil), "png", px_modulo=10)
    assert _decodificar_png(r.datos) == PAYLOAD


@pytest.mark.integration
@pytest.mark.decode
@pytest.mark.raster
def test_roundtrip_texto_plano_no_url() -> None:
    pytest.importorskip("PIL")
    pytest.importorskip("zxingcpp")
    from qr_designer.service.dto import perfil_a_dict
    from qr_designer.service.qr_service import exportar_qr

    out = exportar_qr(PAYLOAD_TEXTO, perfil_a_dict(Perfil(nombre="t")), "png", 10)
    assert _decodificar_png(out["datos"]) == PAYLOAD_TEXTO
