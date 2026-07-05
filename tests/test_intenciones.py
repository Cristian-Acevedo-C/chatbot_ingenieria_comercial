import pandas as pd
import pytest

from chatbot.intenciones import clasificar_consulta


@pytest.fixture
def malla():
    return pd.DataFrame([
        {"codigo_ramo": "AEA315", "nombre_ramo": "Microeconomía II"},
        {"codigo_ramo": "AEA425", "nombre_ramo": "Econometría"},
    ])


@pytest.mark.parametrize(("texto", "intencion"), [
    ("hola", "saludo"),
    ("muchas gracias", "agradecimiento"),
    ("estoy perdido", "confusion"),
    ("¿qué pre-requisito tiene AEA315?", "prerrequisitos"),
    ("¿cuánto vale AEA315?", "evaluaciones"),
])
def test_clasificacion_por_dominio(malla, texto, intencion):
    assert clasificar_consulta(texto, malla=malla).intencion == intencion


def test_seguimiento_conserva_ramo(malla):
    contexto = {"codigo_ramo": "AEA315", "nombre_ramo": "Microeconomía II"}
    resultado = clasificar_consulta("¿y la bibliografía?", malla, contexto)
    assert resultado.codigo_ramo == "AEA315"
    assert resultado.intencion == "bibliografia"
    assert resultado.es_seguimiento

