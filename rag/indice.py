"""Construcción cacheada del índice documental (TF-IDF y embeddings)."""

import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer

from config.settings import STOPWORDS_ES

MODELO_EMBEDDINGS = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def construir_indice_tfidf(textos):
    """Índice TF-IDF disperso. Wrapper compatible: devuelve (vectorizador, matriz)."""
    textos = list(textos)
    if not textos or not any(texto.strip() for texto in textos):
        return None, None

    vectorizador = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        max_features=20000,
        sublinear_tf=True,
        stop_words=sorted(STOPWORDS_ES),
    )
    matriz = vectorizador.fit_transform(textos)
    return vectorizador, matriz


class _EncoderEmbeddings:
    """Adaptador con interfaz ``.transform()`` sobre un modelo SentenceTransformer.

    Expone el mismo contrato mínimo que ``TfidfVectorizer`` (``transform(textos)``)
    y devuelve una matriz densa normalizada, de modo que ``rag.busqueda`` reutiliza
    la misma ruta de similitud coseno para ambos motores.
    """

    def __init__(self, modelo):
        self._modelo = modelo

    def transform(self, textos):
        return self._modelo.encode(
            list(textos),
            normalize_embeddings=True,
            convert_to_numpy=True,
        )


@st.cache_resource(show_spinner="Cargando modelo de búsqueda semántica...")
def _indice_embeddings_cacheado(textos, nombre_modelo):
    """Carga el modelo (cacheado como recurso) y calcula la matriz densa."""
    from sentence_transformers import SentenceTransformer

    modelo = SentenceTransformer(nombre_modelo)
    encoder = _EncoderEmbeddings(modelo)
    matriz = encoder.transform(list(textos))
    return encoder, matriz


def construir_indice_embeddings(textos, nombre_modelo=MODELO_EMBEDDINGS):
    """Índice denso de embeddings. Devuelve (encoder, matriz).

    Si ``sentence-transformers`` no está instalado o el modelo no puede cargarse,
    devuelve ``(None, None)`` para que el llamador caiga a TF-IDF.
    """
    textos = tuple(textos)
    if not textos or not any(texto.strip() for texto in textos):
        return None, None
    try:
        return _indice_embeddings_cacheado(textos, nombre_modelo)
    except Exception:
        return None, None


def construir_indice_documental(textos, metodo="auto"):
    """Construye el índice documental según el método solicitado.

    - ``"tfidf"``: fuerza el índice disperso TF-IDF.
    - ``"embeddings"``: intenta búsqueda semántica; si no está disponible, TF-IDF.
    - ``"auto"``: intenta embeddings y cae a TF-IDF (opción segura por defecto).

    Devuelve ``(metodo_real, modelo, matriz)``, donde ``metodo_real`` refleja el
    motor efectivamente construido (``"tfidf"`` o ``"embeddings"``).
    """
    if metodo in {"auto", "embeddings"}:
        encoder, matriz = construir_indice_embeddings(textos)
        if encoder is not None and matriz is not None:
            return "embeddings", encoder, matriz

    vectorizador, matriz = construir_indice_tfidf(textos)
    return "tfidf", vectorizador, matriz
