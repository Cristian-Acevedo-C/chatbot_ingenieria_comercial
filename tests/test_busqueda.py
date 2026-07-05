import numpy as np
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


class _EncoderBoW:
    """Encoder denso determinista (bolsa de palabras normalizada) para simular
    embeddings sin descargar ningún modelo."""

    def __init__(self, vocabulario):
        self.vocabulario = vocabulario

    def _vector(self, texto):
        tokens = str(texto).lower().split()
        vector = np.array(
            [float(tokens.count(palabra)) for palabra in self.vocabulario]
        )
        norma = np.linalg.norm(vector)
        return vector / norma if norma else vector

    def transform(self, textos):
        return np.vstack([self._vector(texto) for texto in textos])


def _indice_denso():
    chunks = pd.DataFrame([
        {"codigo_ramo": "AAA100", "texto": "marketing estrategia ventas"},
        {"codigo_ramo": "BBB200", "texto": "costos presupuesto variables"},
        {"codigo_ramo": "BBB200", "texto": "presupuesto control costos"},
    ], index=[101, 205, 999])
    vocabulario = [
        "marketing", "estrategia", "ventas",
        "costos", "presupuesto", "variables", "control",
    ]
    encoder = _EncoderBoW(vocabulario)
    matriz = encoder.transform(chunks["texto"].tolist())
    return chunks, encoder, matriz


def test_busqueda_densa_embeddings_funciona_y_filtra_por_ramo():
    chunks, encoder, matriz = _indice_denso()
    resultado = buscar_documentos(
        chunks, "presupuesto costos", encoder, matriz, codigo_ramo="BBB200", umbral=0.0
    )
    assert not resultado.empty
    assert set(resultado["codigo_ramo"]) == {"BBB200"}
    assert "score" in resultado.columns


def test_busqueda_densa_embeddings_respeta_indice_reindexado():
    chunks, encoder, matriz = _indice_denso()
    resultado = buscar_documentos(chunks, "marketing ventas", encoder, matriz, umbral=0.0)
    assert not resultado.empty
    assert resultado.iloc[0]["codigo_ramo"] == "AAA100"

