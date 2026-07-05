"""Búsqueda y selección de evidencia documental."""

import re

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
    top_k=TOP_K,
    umbral=UMBRAL_SIMILITUD,
):
    if chunks.empty or vectorizador is None or matriz is None or not pregunta.strip():
        return pd.DataFrame()

    if codigo_ramo:
        mascara = (
            chunks["codigo_ramo"].astype(str).eq(str(codigo_ramo)).to_numpy()
        )
        posiciones = mascara.nonzero()[0]
    else:
        posiciones = pd.RangeIndex(len(chunks)).to_numpy()

    if len(posiciones) == 0:
        return pd.DataFrame()

    consulta = vectorizador.transform([pregunta])
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
    if "fuente_legible" in fila.index and pd.notna(fila["fuente_legible"]):
        fuente = str(fila["fuente_legible"])
    else:
        fuente = f"{fila['nombre_ramo']} — {fila['ruta_archivo']}"
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

