"""Índice documental: TF-IDF, selección de método y fallback a TF-IDF."""

from rag import indice
from rag.indice import construir_indice_documental, construir_indice_tfidf


TEXTOS = (
    "marketing estrategia ventas",
    "costos presupuesto variables",
)


def test_tfidf_wrapper_devuelve_vectorizador_y_matriz():
    vectorizador, matriz = construir_indice_tfidf(TEXTOS)
    assert vectorizador is not None
    assert matriz.shape[0] == 2


def test_tfidf_wrapper_con_textos_vacios_devuelve_none():
    vectorizador, matriz = construir_indice_tfidf(("", "   "))
    assert vectorizador is None
    assert matriz is None


def test_documental_tfidf_explicito():
    metodo, modelo, matriz = construir_indice_documental(TEXTOS, metodo="tfidf")
    assert metodo == "tfidf"
    assert modelo is not None
    assert matriz.shape[0] == 2


def test_documental_auto_cae_a_tfidf_si_embeddings_no_disponible(monkeypatch):
    def _falla(*_args, **_kwargs):
        raise ImportError("sentence-transformers no instalado")

    monkeypatch.setattr(indice, "_indice_embeddings_cacheado", _falla)
    metodo, modelo, _matriz = construir_indice_documental(TEXTOS, metodo="auto")
    assert metodo == "tfidf"
    assert modelo is not None


def test_documental_embeddings_forzado_tambien_cae_a_tfidf(monkeypatch):
    def _falla(*_args, **_kwargs):
        raise RuntimeError("modelo no disponible")

    monkeypatch.setattr(indice, "_indice_embeddings_cacheado", _falla)
    metodo, _modelo, _matriz = construir_indice_documental(TEXTOS, metodo="embeddings")
    assert metodo == "tfidf"


def test_documental_usa_embeddings_si_estan_disponibles(monkeypatch):
    import numpy as np

    class _EncoderDummy:
        def transform(self, textos):
            return np.ones((len(list(textos)), 3))

    def _fake(textos, _nombre_modelo):
        encoder = _EncoderDummy()
        return encoder, encoder.transform(textos)

    monkeypatch.setattr(indice, "_indice_embeddings_cacheado", _fake)
    metodo, modelo, matriz = construir_indice_documental(TEXTOS, metodo="auto")
    assert metodo == "embeddings"
    assert modelo is not None
    assert matriz.shape == (2, 3)
