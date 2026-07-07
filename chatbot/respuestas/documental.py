"""Respuestas basadas en evidencia documental recuperada."""

from chatbot.contratos import Evidencia, RespuestaChatbot, SeccionRespuesta
from rag.busqueda import fuente_fragmento, limpiar_fragmento, pagina_fragmento
from services.datos import obtener_programas_pendientes


def respuesta_sin_evidencia(nombre_ramo=None, codigo_ramo=None, carrera=None):
    """Respuesta profesional cuando no hay evidencia documental suficiente.

    No inventa contenido: solo explica por qué puede faltar evidencia (programa
    registrado como pendiente, sin PDF oficial cargado, o a verificar con
    coordinación) y ofrece alternativas ya disponibles en el sistema.
    """
    if codigo_ramo and nombre_ramo:
        identificador = f"**{codigo_ramo} — {nombre_ramo}**"
    elif codigo_ramo:
        identificador = f"**{codigo_ramo}**"
    elif nombre_ramo:
        identificador = f"**{nombre_ramo}**"
    else:
        identificador = None

    if identificador is None:
        # Catch-all también para consultas ambiguas o fuera de alcance: sin
        # ramo/código detectado, no tiene sentido devolver un bloque largo.
        return RespuestaChatbot(
            tipo="documental",
            resumen=(
                "No tengo información validada para responder eso en esta demo. "
                "Puedo orientarte de forma general sobre malla, ramos, prerrequisitos, "
                "práctica o titulación; para una respuesta oficial, confírmalo con "
                "coordinación o secretaría académica."
            ),
        )

    pendientes = obtener_programas_pendientes(carrera) if (codigo_ramo and carrera) else []
    esta_pendiente = bool(codigo_ramo) and str(codigo_ramo) in {str(item) for item in pendientes}

    if esta_pendiente:
        resumen = (
            f"No encontré evidencia suficiente sobre {identificador} porque su programa de "
            "asignatura figura **pendiente** en la base documental (aún no tiene PDF oficial "
            "cargado)."
        )
        razones = (
            "1. El curso está registrado como **pendiente**: todavía no tiene programa de "
            "asignatura (PDF) cargado.\n"
            "2. Por eso no existen fragmentos indexados para buscar evidencia.\n"
            "3. La información oficial debe verificarse con coordinación académica."
        )
    else:
        resumen = (
            "No encontré evidencia suficiente en los documentos cargados para responder con "
            f"seguridad sobre {identificador}."
        )
        razones = (
            "1. El programa de asignatura no está disponible en la base documental de esta "
            "carrera.\n"
            "2. El curso podría no tener PDF oficial cargado.\n"
            "3. La información debe verificarse directamente con coordinación académica."
        )

    return RespuestaChatbot(
        tipo="documental",
        resumen=resumen,
        secciones=[
            SeccionRespuesta(
                titulo="Esto puede ocurrir porque", contenido=razones, formato="markdown"
            ),
        ],
        recomendacion=(
            "Puedo ayudarte a revisar la malla, los prerrequisitos disponibles o ramos "
            "relacionados con este curso."
        ),
    )


def respuesta_documental(resultados, nombre_ramo=None, codigo_ramo=None, carrera=None):
    if resultados.empty:
        return respuesta_sin_evidencia(nombre_ramo, codigo_ramo=codigo_ramo, carrera=carrera)
    contexto = f" sobre {nombre_ramo}" if nombre_ramo else " en la base documental"
    evidencias = [
        Evidencia(
            texto=limpiar_fragmento(fila["texto"], limite=500),
            fuente=fuente_fragmento(fila),
            score=float(fila["score"]) if "score" in fila.index else None,
            pagina=pagina_fragmento(fila),
        )
        for _, fila in resultados.head(3).iterrows()
    ]
    return RespuestaChatbot(
        tipo="documental",
        resumen=(
            f"Encontré evidencia pertinente{contexto} en los programas de asignatura "
            "cargados localmente. Revisa los extractos breves para precisar la consulta."
        ),
        evidencias=evidencias,
    )
