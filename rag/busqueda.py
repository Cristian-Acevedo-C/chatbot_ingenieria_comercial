"""Búsqueda y selección de evidencia documental."""

import re
from pathlib import Path

import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from config.settings import TOP_K, UMBRAL_SIMILITUD
from utils.texto import normalizar


def buscar_documentos(
    chunks,
    pregunta,
    vectorizador,
    matriz,
    codigo_ramo=None,
    carrera=None,
    top_k=TOP_K,
    umbral=UMBRAL_SIMILITUD,
):
    if chunks.empty or vectorizador is None or matriz is None or not pregunta.strip():
        return pd.DataFrame()

    mascara = pd.Series(True, index=chunks.index)
    if carrera:
        if "carrera" not in chunks.columns:
            return pd.DataFrame()
        mascara &= chunks["carrera"].fillna("").astype(str).eq(str(carrera))
    if codigo_ramo:
        mascara &= chunks["codigo_ramo"].astype(str).eq(str(codigo_ramo))
    posiciones = mascara.to_numpy().nonzero()[0]

    if len(posiciones) == 0:
        return pd.DataFrame()

    consulta = vectorizador.transform([pregunta])
    # El guard por vocabulario mínimo aplica solo al índice disperso TF-IDF;
    # un índice denso de embeddings no expone ``nnz`` y siempre produce vector.
    if hasattr(consulta, "nnz"):
        terminos_minimos = 1 if codigo_ramo else 2
        if consulta.nnz < terminos_minimos:
            return pd.DataFrame()

    similitudes = cosine_similarity(consulta, matriz[posiciones]).ravel()
    orden_local = similitudes.argsort()[::-1]
    seleccion = [indice for indice in orden_local if similitudes[indice] >= umbral][:top_k]
    if not seleccion:
        return pd.DataFrame()

    posiciones_finales = posiciones[seleccion]
    resultados = chunks.iloc[posiciones_finales].copy()
    resultados["score"] = [float(similitudes[indice]) for indice in seleccion]
    return resultados.reset_index(drop=True)


def limpiar_fragmento(texto, limite=850):
    fragmento = " ".join(str(texto).replace("\n", " ").split())
    return fragmento if len(fragmento) <= limite else fragmento[:limite].rstrip() + "..."


def pagina_fragmento(fila):
    if "pagina_aproximada" in fila.index and pd.notna(fila["pagina_aproximada"]):
        return str(int(float(fila["pagina_aproximada"])))
    coincidencia = re.search(r"\[Página\s+(\d+)\]", str(fila["texto"]))
    return coincidencia.group(1) if coincidencia else None


def fuente_fragmento(fila):
    archivo = Path(str(fila["ruta_archivo"])).name
    fuente = f"Fuente: {archivo}"
    pagina = pagina_fragmento(fila)
    return f"{fuente}, página aproximada {pagina}" if pagina else fuente



def seleccionar_evidencias(chunks, codigo_ramo, tipo, resultados=None):
    filas = chunks[chunks["codigo_ramo"].astype(str) == str(codigo_ramo)].copy()
    terminos = {
        "estudio": ("5. contenidos", "n° unidad", "unidad", "tema"),
        "contenidos": ("5. contenidos", "n° unidad", "unidad", "tema"),
        "bibliografia": (
            "8.1 bibliografía básica",
            "8.2 bibliografía complementaria",
            "bibliografía",
        ),
        "evaluaciones": (
            "7.2. estrategia evaluativa",
            "7.3. descripción de la estrategia evaluativa",
            "evaluación de la asignatura",
        ),
        "aprendizajes": (
            "3. resultados de aprendizaje",
            "resultados de aprendizaje",
            "aprendizajes esperados",
        ),
    }.get(tipo, ())
    seleccionadas = []
    if terminos:
        filas["_prioridad_evidencia"] = filas["texto"].fillna("").astype(str).map(
            lambda texto: sum(
                len(terminos) - indice
                for indice, termino in enumerate(terminos)
                if normalizar(termino) in normalizar(texto)
            )
        )
        filas = filas.sort_values("_prioridad_evidencia", ascending=False)
    for _, fila in filas.iterrows():
        texto_normalizado = normalizar(fila["texto"])
        if terminos and not any(normalizar(termino) in texto_normalizado for termino in terminos):
            continue
        seleccionadas.append(
            {
                "texto": limpiar_fragmento(fila["texto"], limite=500),
                "fuente": fuente_fragmento(fila),
            }
        )
        if len(seleccionadas) == 3:
            break
    if not seleccionadas and resultados is not None and not resultados.empty:
        for _, fila in resultados.head(3).iterrows():
            seleccionadas.append(
                {
                    "texto": limpiar_fragmento(fila["texto"], limite=500),
                    "fuente": fuente_fragmento(fila),
                }
            )
    return seleccionadas

