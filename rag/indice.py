"""Construcción cacheada del índice TF-IDF."""

import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer

from config.settings import STOPWORDS_ES


def construir_indice_tfidf(textos):
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


