"""Representación pura de un contrato como bloques renderizables."""

from chatbot.contratos import normalizar_respuesta


def construir_bloques_render(respuesta):
    """Convierte cualquier respuesta compatible en instrucciones sin Streamlit."""
    contrato = normalizar_respuesta(respuesta)
    bloques = []
    if contrato.titulo:
        bloques.append(
            {"tipo": "titulo", "titulo": contrato.titulo, "contenido": None}
        )
    if contrato.resumen:
        bloques.append(
            {
                "tipo": "resumen",
                "titulo": "Respuesta breve",
                "contenido": contrato.resumen,
            }
        )
    for seccion in contrato.secciones:
        bloques.append(
            {
                "tipo": seccion.formato,
                "titulo": seccion.titulo,
                "contenido": seccion.contenido,
            }
        )
    for advertencia in contrato.advertencias:
        bloques.append(
            {
                "tipo": "advertencia",
                "titulo": "Advertencia",
                "contenido": advertencia,
            }
        )
    if contrato.recomendacion:
        bloques.append(
            {
                "tipo": "recomendacion",
                "titulo": "Recomendación",
                "contenido": contrato.recomendacion,
            }
        )
    if contrato.fuentes:
        bloques.append(
            {
                "tipo": "fuentes",
                "titulo": "Fuentes",
                "contenido": contrato.fuentes,
            }
        )
    if contrato.evidencias:
        bloques.append(
            {
                "tipo": "evidencias",
                "titulo": "Evidencia",
                "contenido": contrato.evidencias,
            }
        )
    return bloques
