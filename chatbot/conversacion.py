"""Estado de sesión y seguimiento conversacional."""

import random

import streamlit as st

from chatbot.contratos import adaptar_contrato_respuesta
from chatbot.intenciones import clasificar_consulta
from utils.texto import normalizar
from chatbot.respuestas import responder, respuesta_pedir_ramo, respuesta_recomendacion
from config.settings import (
    APERTURAS,
    CLAVES_ESTADO_CONVERSACIONAL,
    MENSAJES_SOCIALES,
    PREGUNTAS_CIERRE,
    PREGUNTAS_GENERALES,
)


def limpiar_estado_conversacional():
    for clave in CLAVES_ESTADO_CONVERSACIONAL:
        st.session_state.pop(clave, None)


def construir_preguntas_rapidas(ramos, limite=7):
    preguntas = list(PREGUNTAS_GENERALES)
    if not ramos.empty:
        nombre = str(ramos.iloc[0]["nombre_ramo"])
        preguntas.extend(
            [
                f"¿Qué debería estudiar para {nombre}?",
                f"¿Qué prerrequisitos tiene {nombre}?",
                f"¿Cómo se evalúa {nombre}?",
            ]
        )
    return preguntas[:limite]


def elegir_apertura():
    return random.choice(APERTURAS)


def responder_conversacional(
    pregunta,
    alumno,
    ramos,
    historial,
    prerrequisitos,
    prerrequisitos_alumno,
    malla,
    chunks,
    vectorizador,
    matriz,
    ramo_contexto,
    opciones_ramos,
):
    contexto_previo = None
    if st.session_state.get("ultimo_ramo_codigo"):
        contexto_previo = {
            "codigo_ramo": st.session_state["ultimo_ramo_codigo"],
            "nombre_ramo": st.session_state.get("ultimo_ramo_nombre"),
        }
    clasificacion = clasificar_consulta(
        pregunta,
        malla=malla,
        ramo_contexto=contexto_previo or ramo_contexto,
    )

    if clasificacion.intencion in MENSAJES_SOCIALES:
        st.session_state["ultima_intencion"] = clasificacion.intencion
        return {
            "apertura": MENSAJES_SOCIALES[clasificacion.intencion],
            "cuerpo": None,
            "cierre": None,
        }

    if clasificacion.intencion == "recomendacion":
        st.session_state["ultima_intencion"] = "recomendacion"
        return {
            "apertura": elegir_apertura(),
            "cuerpo": adaptar_contrato_respuesta(
                respuesta_recomendacion(ramos, historial, prerrequisitos_alumno),
                "recomendacion",
            ),
            "cierre": PREGUNTAS_CIERRE["recomendacion"],
        }

    if clasificacion.intencion == "pedir_ramo":
        st.session_state["ultima_intencion"] = "pedir_ramo"
        return {
            "apertura": elegir_apertura(),
            "cuerpo": adaptar_contrato_respuesta(
                respuesta_pedir_ramo(opciones_ramos), "pedir_ramo"
            ),
            "cierre": None,
        }

    pregunta_efectiva = pregunta
    if (
        clasificacion.es_seguimiento
        and clasificacion.nombre_ramo
        and normalizar(clasificacion.nombre_ramo) not in normalizar(pregunta)
    ):
        pregunta_efectiva = f"{pregunta} {clasificacion.nombre_ramo}"

    cuerpo = responder(
        pregunta_efectiva,
        alumno,
        ramos,
        historial,
        prerrequisitos,
        malla,
        chunks,
        vectorizador,
        matriz,
        ramo_contexto,
        clasificacion,
    )

    if clasificacion.codigo_ramo:
        st.session_state["ultimo_ramo_codigo"] = clasificacion.codigo_ramo
        st.session_state["ultimo_ramo_nombre"] = clasificacion.nombre_ramo

    st.session_state["ultima_intencion"] = clasificacion.intencion
    return {
        "apertura": elegir_apertura(),
        "cuerpo": adaptar_contrato_respuesta(cuerpo, clasificacion.intencion),
        "cierre": PREGUNTAS_CIERRE.get(clasificacion.intencion),
    }

