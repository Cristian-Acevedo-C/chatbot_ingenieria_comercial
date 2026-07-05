"""Reglas de priorización académica.

La respuesta conversacional sigue en ``chatbot.respuestas``. Este módulo queda
como punto de extensión para reglas puras de recomendación, sin UI ni estado.
"""


def ordenar_por_alerta(alerta):
    """Devuelve una prioridad estable para los estados académicos conocidos."""
    return {"Riesgo alto": 0, "Riesgo medio": 1, "Pendiente": 2}.get(alerta, 3)
