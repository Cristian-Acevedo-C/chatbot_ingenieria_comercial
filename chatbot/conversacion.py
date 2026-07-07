"""Estado de sesión y seguimiento conversacional."""

import random

import streamlit as st

from chatbot.contratos import adaptar_contrato_respuesta
from chatbot.intenciones import clasificar_consulta
from utils.texto import normalizar
from chatbot.respuestas import (
    responder,
    responder_basica,
    respuesta_pedir_ramo,
    respuesta_recomendacion,
)
from config.settings import (
    APERTURAS,
    CLAVES_ESTADO_CONVERSACIONAL,
    MENSAJES_SOCIALES,
    PREGUNTAS_CIERRE,
    PREGUNTAS_GENERALES,
    ROLES_DEMO,
)
from services.datos import listar_carreras_disponibles


def limpiar_estado_conversacional():
    for clave in CLAVES_ESTADO_CONVERSACIONAL:
        st.session_state.pop(clave, None)


def construir_preguntas_rapidas(ramos, carrera=None, limite=7):
    """Preguntas rápidas generales más variantes según carrera y ramos inscritos.

    Las variantes de carrera solo cambian el texto mostrado (mencionan la
    carrera activa); usan las mismas palabras clave ya reconocidas por
    ``chatbot.intenciones`` (p. ej. "ramos inscritos", "alerta"), por lo que no
    se agrega ninguna intención nueva ni datos inventados.
    """
    preguntas = list(PREGUNTAS_GENERALES)
    if carrera:
        preguntas.extend(
            [
                f"¿Qué ramos tengo inscritos en {carrera}?",
                f"¿Tengo alguna alerta académica en {carrera}?",
            ]
        )
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


_FRASES_DERIVACION = (
    "coordinacion",
    "secretaria academica",
    "no tengo informacion validada",
    "no encontre evidencia",
    "pendiente",
    "registro academico",
)


def resumen_para_registro(mensaje_asistente):
    """Extrae ``(texto_plano, fuente, requiere_derivacion)`` de un turno.

    Aplana el mensaje del asistente (apertura + cuerpo + cierre) a texto para el
    registro anónimo, sin acoplar la capa de almacenamiento al contrato
    ``RespuestaChatbot``. ``fuente`` es ``"conversacional"`` cuando no hay cuerpo
    tipado (mensaje social) o el ``tipo`` de la respuesta en caso contrario.
    ``requiere_derivacion`` es una heurística de texto: la respuesta sugiere
    validar con canales oficiales o admite que no hay evidencia suficiente.
    """
    partes = []
    fuente = "conversacional"

    apertura = mensaje_asistente.get("apertura")
    if apertura:
        partes.append(str(apertura))

    cuerpo = mensaje_asistente.get("cuerpo")
    if cuerpo is not None:
        fuente = getattr(cuerpo, "tipo", None) or "documental"
        resumen = getattr(cuerpo, "resumen", "") or ""
        if resumen:
            partes.append(str(resumen))
        for seccion in getattr(cuerpo, "secciones", []) or []:
            titulo = getattr(seccion, "titulo", "")
            if titulo:
                partes.append(str(titulo))
        if getattr(cuerpo, "recomendacion", None):
            partes.append(str(cuerpo.recomendacion))

    cierre = mensaje_asistente.get("cierre")
    if cierre:
        partes.append(str(cierre))

    texto_plano = "\n".join(partes).strip()
    requiere_derivacion = any(
        frase in normalizar(texto_plano) for frase in _FRASES_DERIVACION
    )
    return texto_plano, str(fuente), requiere_derivacion


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
    carrera=None,
    malla_consulta=None,
):
    respuesta_basica = responder_basica(
        pregunta,
        contexto={
            "carrera": carrera,
            "carreras_disponibles": listar_carreras_disponibles(chunks),
            "perfiles_disponibles": ROLES_DEMO,
        },
    )
    if respuesta_basica is not None:
        st.session_state["ultima_intencion"] = respuesta_basica.tipo
        return {
            "apertura": None,
            "cuerpo": respuesta_basica,
            "cierre": respuesta_basica.metadata.get("cierre_sugerido"),
        }

    contexto_previo = None
    if st.session_state.get("ultimo_ramo_codigo"):
        contexto_previo = {
            "codigo_ramo": st.session_state["ultimo_ramo_codigo"],
            "nombre_ramo": st.session_state.get("ultimo_ramo_nombre"),
        }
    clasificacion = clasificar_consulta(
        pregunta,
        malla=malla_consulta if malla_consulta is not None else malla,
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
        carrera,
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

