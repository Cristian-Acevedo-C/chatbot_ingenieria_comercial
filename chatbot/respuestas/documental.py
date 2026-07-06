"""Respuestas basadas en evidencia documental recuperada."""

from chatbot.contratos import Evidencia, RespuestaChatbot
from rag.busqueda import fuente_fragmento, limpiar_fragmento, pagina_fragmento


def respuesta_sin_evidencia(nombre_ramo=None):
    return RespuestaChatbot(
        tipo="documental",
        resumen=(
            "No encontré evidencia suficiente en los documentos cargados. "
            "Verifica esta información en la fuente oficial UDLA o con coordinación "
            "académica."
        ),
    )


def respuesta_documental(resultados, nombre_ramo=None):
    if resultados.empty:
        return respuesta_sin_evidencia(nombre_ramo)
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
