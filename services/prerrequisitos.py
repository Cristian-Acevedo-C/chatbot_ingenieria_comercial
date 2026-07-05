"""Reglas locales para evaluar prerrequisitos académicos."""

import pandas as pd

from services.datos import valor_texto
from utils.texto import normalizar


def preparar_mapa_prerrequisitos(prerrequisitos, malla):
    if prerrequisitos.empty:
        return pd.DataFrame(columns=[*prerrequisitos.columns, "semestre"])
    semestres = malla[["codigo_ramo", "semestre"]].copy()
    semestres["codigo_ramo"] = semestres["codigo_ramo"].astype(str)
    mapa = prerrequisitos.copy()
    mapa["codigo_ramo"] = mapa["codigo_ramo"].astype(str)
    return mapa.merge(semestres, on="codigo_ramo", how="left", validate="many_to_one")


def obtener_estado_prerrequisito(historial, codigo_prerrequisito, tipo):
    tipo_normalizado = normalizar(tipo)
    if tipo_normalizado in {"sin prerrequisito", "no detectado"}:
        return "No aplica"
    if not codigo_prerrequisito or historial.empty:
        return "Pendiente"

    registros = historial[
        historial["codigo_ramo"].astype(str) == str(codigo_prerrequisito)
    ]
    if registros.empty:
        return "Pendiente"

    estados = set(registros["estado"].fillna("").astype(str).map(normalizar))
    if "aprobado" in estados:
        return "Aprobado"
    if "cursando" in estados:
        return "Cursando"
    if "reprobado" in estados:
        return "Reprobado"
    return "Pendiente"


def obtener_alerta_prerrequisito(estado, tipo):
    if normalizar(tipo) == "no detectado":
        return "Información incompleta"
    return {
        "Aprobado": "OK",
        "No aplica": "OK",
        "Reprobado": "Riesgo alto",
        "Cursando": "Riesgo medio",
        "Pendiente": "Pendiente",
    }.get(estado, "Pendiente")


def construir_prerrequisitos_alumno(ramos, historial, prerrequisitos):
    columnas = [
        "codigo_ramo",
        "nombre_ramo",
        "codigo_prerrequisito",
        "nombre_prerrequisito",
        "tipo",
        "estado_prerrequisito",
        "alerta",
        "fuente_archivo",
        "evidencia_textual",
        "confianza",
    ]
    if ramos.empty or prerrequisitos.empty:
        return pd.DataFrame(columns=columnas)

    registros = []
    for _, ramo in ramos.iterrows():
        codigo_ramo = str(ramo["codigo_ramo"])
        relaciones = prerrequisitos[
            prerrequisitos["codigo_ramo"].astype(str) == codigo_ramo
        ]
        if relaciones.empty:
            relaciones = pd.DataFrame(
                [
                    {
                        "codigo_ramo": codigo_ramo,
                        "nombre_ramo": ramo["nombre_ramo"],
                        "codigo_prerrequisito": "",
                        "nombre_prerrequisito": "",
                        "tipo": "No detectado",
                        "fuente_archivo": "",
                        "evidencia_textual": "No existe una fila para este ramo en prerrequisitos.csv.",
                        "confianza": "No aplica",
                    }
                ]
            )

        for _, relacion in relaciones.iterrows():
            tipo = valor_texto(relacion.get("tipo"))
            codigo_prerrequisito = valor_texto(relacion.get("codigo_prerrequisito"))
            estado = obtener_estado_prerrequisito(
                historial, codigo_prerrequisito, tipo
            )
            registros.append(
                {
                    "codigo_ramo": codigo_ramo,
                    "nombre_ramo": str(ramo["nombre_ramo"]),
                    "codigo_prerrequisito": codigo_prerrequisito,
                    "nombre_prerrequisito": valor_texto(
                        relacion.get("nombre_prerrequisito")
                    ),
                    "tipo": tipo,
                    "estado_prerrequisito": estado,
                    "alerta": obtener_alerta_prerrequisito(estado, tipo),
                    "fuente_archivo": valor_texto(relacion.get("fuente_archivo")),
                    "evidencia_textual": valor_texto(
                        relacion.get("evidencia_textual")
                    ),
                    "confianza": valor_texto(relacion.get("confianza")),
                }
            )

    return pd.DataFrame(registros, columns=columnas)


def calcular_metricas_prerrequisitos(prerrequisitos):
    if prerrequisitos.empty:
        return {
            "analizados": 0,
            "con_prerrequisito": 0,
            "sin_prerrequisito": 0,
            "no_detectados": 0,
            "relaciones": 0,
        }
    return {
        "analizados": prerrequisitos["codigo_ramo"].nunique(),
        "con_prerrequisito": prerrequisitos.loc[
            prerrequisitos["tipo"] == "Prerrequisito", "codigo_ramo"
        ].nunique(),
        "sin_prerrequisito": prerrequisitos.loc[
            prerrequisitos["tipo"] == "Sin prerrequisito", "codigo_ramo"
        ].nunique(),
        "no_detectados": prerrequisitos.loc[
            prerrequisitos["tipo"] == "No detectado", "codigo_ramo"
        ].nunique(),
        "relaciones": int((prerrequisitos["tipo"] == "Prerrequisito").sum()),
    }


