import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from rag.busqueda import buscar_documentos


def _indice():
    chunks = pd.DataFrame([
        {"codigo_ramo": "AAA100", "texto": "marketing estrategia ventas"},
        {"codigo_ramo": "BBB200", "texto": "costos presupuesto variables"},
        {"codigo_ramo": "BBB200", "texto": "presupuesto control costos"},
    ], index=[101, 205, 999])
    vectorizador = TfidfVectorizer()
    return chunks, vectorizador, vectorizador.fit_transform(chunks["texto"])


def test_busqueda_funciona_con_indice_reindexado():
    chunks, vectorizador, matriz = _indice()
    resultado = buscar_documentos(chunks, "costos presupuesto", vectorizador, matriz, umbral=0)
    assert not resultado.empty
    assert resultado.iloc[0]["codigo_ramo"] == "BBB200"


def test_busqueda_filtra_por_ramo():
    chunks, vectorizador, matriz = _indice()
    resultado = buscar_documentos(
        chunks, "presupuesto", vectorizador, matriz, codigo_ramo="BBB200", umbral=0
    )
    assert set(resultado["codigo_ramo"]) == {"BBB200"}


def test_umbral_alto_no_devuelve_resultados():
    chunks, vectorizador, matriz = _indice()
    resultado = buscar_documentos(chunks, "astronomía", vectorizador, matriz, umbral=0.99)
    assert resultado.empty

