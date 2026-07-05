"""Enrutador principal de respuestas del chatbot."""

from chatbot.contratos import RespuestaChatbot, normalizar_respuesta
from chatbot.intenciones import clasificar_consulta, normalizar
from chatbot.respuestas.academicas import construir_respuesta_academica
from chatbot.respuestas.alertas import respuesta_alertas
from chatbot.respuestas.alumno import respuesta_avance_curricular, respuesta_datos_alumno, respuesta_ramos
from chatbot.respuestas.documental import respuesta_documental
from chatbot.respuestas.prerrequisitos import (
    respuesta_prerrequisitos_pendientes,
    respuesta_prerrequisitos_ramo,
    respuesta_puede_cursar,
    respuesta_ramos_por_tipo,
    respuesta_todos_prerrequisitos,
)
from rag.busqueda import buscar_documentos
from services.prerrequisitos import construir_prerrequisitos_alumno


def _responder_sin_normalizar(
    pregunta,
    alumno,
    ramos,
    historial,
    prerrequisitos,
    malla,
    chunks,
    vectorizador,
    matriz,
    ramo_contexto=None,
    clasificacion=None,
):
    clasificacion = clasificacion or clasificar_consulta(
        pregunta, malla=malla, ramo_contexto=ramo_contexto
    )
    pregunta_normalizada = clasificacion.pregunta_normalizada
    codigo = clasificacion.codigo_ramo
    nombre = clasificacion.nombre_ramo
    intencion = clasificacion.intencion
    prerrequisitos_alumno = construir_prerrequisitos_alumno(
        ramos, historial, prerrequisitos
    )

    if intencion == "ramos_inscritos":
        return respuesta_ramos(ramos)
    if intencion == "puede_cursar":
        return respuesta_puede_cursar(codigo, nombre, historial, prerrequisitos)
    if intencion == "prerrequisitos":
        if "pendiente" in pregunta_normalizada and any(
            palabra in pregunta_normalizada for palabra in ("tengo", "mis")
        ):
            return respuesta_prerrequisitos_pendientes(
                prerrequisitos_alumno, prerrequisitos
            )
        if "no detectado" in pregunta_normalizada:
            return respuesta_ramos_por_tipo(
                prerrequisitos,
                "No detectado",
                "con prerrequisito no detectado",
            )
        if (
            "no tienen" in pregunta_normalizada
            or "sin prerrequisito" in pregunta_normalizada
            or "sin pre requisito" in pregunta_normalizada
        ):
            return respuesta_ramos_por_tipo(
                prerrequisitos,
                "Sin prerrequisito",
                "sin prerrequisito explícito",
            )
        if "todos" in pregunta_normalizada:
            return respuesta_todos_prerrequisitos(prerrequisitos)
        if codigo:
            return respuesta_prerrequisitos_ramo(
                prerrequisitos, codigo, nombre, historial
            )
        return respuesta_todos_prerrequisitos(prerrequisitos)
    if intencion == "alertas":
        return respuesta_alertas(
            historial, prerrequisitos_alumno, prerrequisitos
        )
    if intencion == "avance_curricular":
        return respuesta_avance_curricular(alumno, historial, malla)
    if intencion == "datos_alumno":
        return respuesta_datos_alumno(alumno)
    if intencion == "pedir_ramo":
        return RespuestaChatbot(
            tipo="pedir_ramo",
            resumen="Necesito que indiques un ramo para responder esa consulta.",
            recomendacion="Escribe el nombre o código del ramo.",
        )

    consulta = f"{pregunta} {nombre}" if nombre and normalizar(nombre) not in pregunta_normalizada else pregunta
    resultados = buscar_documentos(
        chunks,
        consulta,
        vectorizador,
        matriz,
        codigo_ramo=codigo,
    )
    tipo_pregunta = intencion
    if codigo and tipo_pregunta in {
        "estudio",
        "contenidos",
        "bibliografia",
        "evaluaciones",
    }:
        return construir_respuesta_academica(
            tipo_pregunta,
            codigo,
            nombre,
            chunks,
            resultados,
            prerrequisitos,
            historial,
        )
    return respuesta_documental(resultados, nombre_ramo=nombre)


def responder(
    pregunta,
    alumno,
    ramos,
    historial,
    prerrequisitos,
    malla,
    chunks,
    vectorizador,
    matriz,
    ramo_contexto=None,
    clasificacion=None,
):
    """Único límite de normalización del motor de respuestas."""
    clasificacion = clasificacion or clasificar_consulta(
        pregunta, malla=malla, ramo_contexto=ramo_contexto
    )
    respuesta = _responder_sin_normalizar(
        pregunta,
        alumno,
        ramos,
        historial,
        prerrequisitos,
        malla,
        chunks,
        vectorizador,
        matriz,
        ramo_contexto=ramo_contexto,
        clasificacion=clasificacion,
    )
    return normalizar_respuesta(respuesta, tipo=clasificacion.intencion)
