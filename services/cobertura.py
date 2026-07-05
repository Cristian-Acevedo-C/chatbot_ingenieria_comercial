"""Métricas de cobertura de la base documental local."""

import pandas as pd


def calcular_cobertura_documental(chunks, ramos_inscritos=None):
    """Resume qué tan cubierta está la base documental.

    Devuelve un dict con totales, un DataFrame de chunks por ramo y los ramos
    inscritos que no tienen evidencia documental. No modifica los datos de entrada.
    """
    vacio = {
        "total_chunks": 0,
        "ramos_con_documentos": 0,
        "fuentes_distintas": 0,
        "chunks_por_ramo": pd.DataFrame(
            columns=["codigo_ramo", "nombre_ramo", "chunks"]
        ),
        "ramos_inscritos_sin_evidencia": [],
    }
    if chunks is None or chunks.empty or "codigo_ramo" not in chunks.columns:
        return vacio

    base = chunks.assign(codigo_ramo=chunks["codigo_ramo"].astype(str))
    codigos_con_doc = set(base["codigo_ramo"])

    columnas_grupo = ["codigo_ramo"]
    if "nombre_ramo" in base.columns:
        columnas_grupo.append("nombre_ramo")
    chunks_por_ramo = (
        base.groupby(columnas_grupo, dropna=False)
        .size()
        .reset_index(name="chunks")
        .sort_values("chunks", ascending=False)
        .reset_index(drop=True)
    )

    fuentes = base["ruta_archivo"].nunique() if "ruta_archivo" in base.columns else 0

    sin_evidencia = []
    if ramos_inscritos is not None and not ramos_inscritos.empty:
        tiene_nombre = "nombre_ramo" in ramos_inscritos.columns
        for _, fila in ramos_inscritos.iterrows():
            codigo = str(fila["codigo_ramo"])
            if codigo not in codigos_con_doc:
                sin_evidencia.append(
                    {
                        "codigo_ramo": codigo,
                        "nombre_ramo": str(fila["nombre_ramo"]) if tiene_nombre else "",
                    }
                )

    return {
        "total_chunks": int(len(base)),
        "ramos_con_documentos": int(len(codigos_con_doc)),
        "fuentes_distintas": int(fuentes),
        "chunks_por_ramo": chunks_por_ramo,
        "ramos_inscritos_sin_evidencia": sin_evidencia,
    }
