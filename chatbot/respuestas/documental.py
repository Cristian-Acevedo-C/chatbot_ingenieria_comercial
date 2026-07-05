"""Respuestas basadas en evidencia documental recuperada."""

from chatbot.contratos import Evidencia, RespuestaChatbot, SeccionRespuesta
from rag.busqueda import fuente_fragmento, limpiar_fragmento, pagina_fragmento


def respuesta_sin_evidencia(nombre_ramo=None):
    contexto = f" para **{nombre_ramo}**" if nombre_ramo else ""
    return RespuestaChatbot(
        tipo="documental",
        resumen=(
            f"No encontré evidencia documental suficientemente similar{contexto}."
        ),
        secciones=[
            SeccionRespuesta(
                titulo="Evidencia encontrada",
                contenido=(
                    "La búsqueda quedó bajo el umbral mínimo de similitud, por lo que "
                    "no se muestran fragmentos potencialmente irrelevantes."
                ),
                formato="markdown",
            )
        ],
        recomendacion=(
            "Reformula la pregunta usando el código del ramo, su nombre completo "
            "o un tema específico."
        ),
        fuentes=["Base documental local `data/document_chunks.csv`."],
        metadata={"titulo_recomendacion": "Recomendación de estudio"},
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
