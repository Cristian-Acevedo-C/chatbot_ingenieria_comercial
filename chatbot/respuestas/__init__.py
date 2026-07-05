"""API pública compatible de las familias de respuestas."""

from chatbot.respuestas.academicas import construir_respuesta_academica
from chatbot.respuestas.alertas import respuesta_alertas
from chatbot.respuestas.alumno import (
    respuesta_avance_curricular,
    respuesta_datos_alumno,
    respuesta_ramos,
)
from chatbot.respuestas.documental import (
    respuesta_documental,
    respuesta_sin_evidencia,
)
from chatbot.respuestas.orquestador import responder
from chatbot.respuestas.prerrequisitos import (
    respuesta_prerrequisitos_no_cargados,
    respuesta_prerrequisitos_pendientes,
    respuesta_prerrequisitos_ramo,
    respuesta_puede_cursar,
    respuesta_ramos_por_tipo,
    respuesta_todos_prerrequisitos,
)
from chatbot.respuestas.recomendaciones import (
    respuesta_pedir_ramo,
    respuesta_recomendacion,
)

__all__ = [
    "construir_respuesta_academica",
    "responder",
    "respuesta_alertas",
    "respuesta_avance_curricular",
    "respuesta_datos_alumno",
    "respuesta_documental",
    "respuesta_pedir_ramo",
    "respuesta_prerrequisitos_no_cargados",
    "respuesta_prerrequisitos_pendientes",
    "respuesta_prerrequisitos_ramo",
    "respuesta_puede_cursar",
    "respuesta_ramos",
    "respuesta_ramos_por_tipo",
    "respuesta_recomendacion",
    "respuesta_sin_evidencia",
    "respuesta_todos_prerrequisitos",
]
