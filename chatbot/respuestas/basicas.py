"""Capa conversacional básica: saludos, agradecimientos, identidad y ayuda.

Responde de inmediato mensajes simples sin activar el RAG documental ni el
enrutador académico. Las frases reconocidas y sus respuestas viven en
``data/respuestas/respuestas_basicas.csv`` (editable sin tocar código). Si el
mensaje parece una consulta documental o académica (contiene alguna de las
mismas palabras clave que ya usa ``chatbot.intenciones``, o un código de ramo
tipo ``EIN908``), esta capa se abstiene y devuelve ``None`` para que el flujo
existente (clasificación + RAG) se encargue.
"""

import re

import pandas as pd

from chatbot.contratos import RespuestaChatbot
from config.settings import DATA_DIR, HINTS_ACADEMICOS
from utils.texto import normalizar

RESPUESTAS_BASICAS_CSV = DATA_DIR / "respuestas" / "respuestas_basicas.csv"
COLUMNAS = (
    "intencion",
    "ejemplos_usuario",
    "respuesta",
    "prioridad",
    "usar_carrera",
    "pasar_a_rag",
)
_PATRON_CODIGO_RAMO = re.compile(r"\b[a-zñ]{2,4}\d{3}\b")


def cargar_respuestas_basicas(ruta=None):
    """Lee el CSV editable de respuestas básicas. Vacío si no existe."""
    ruta = ruta or RESPUESTAS_BASICAS_CSV
    if not ruta.exists():
        return pd.DataFrame(columns=COLUMNAS)
    try:
        df = pd.read_csv(ruta)
    except (pd.errors.EmptyDataError, OSError):
        return pd.DataFrame(columns=COLUMNAS)
    faltantes = set(COLUMNAS) - set(df.columns)
    if faltantes:
        return pd.DataFrame(columns=COLUMNAS)
    return df.sort_values("prioridad", kind="stable").reset_index(drop=True)


def _es_afirmativo(valor):
    return normalizar(str(valor)) in {"si", "sí", "true", "1"}


def es_consulta_academica_o_documental(mensaje):
    """Guarda de seguridad: nunca responder básico si huele a RAG/académico."""
    texto = normalizar(mensaje)
    if any(hint in texto for hint in HINTS_ACADEMICOS):
        return True
    if _PATRON_CODIGO_RAMO.search(texto):
        return True
    return False


def detectar_fila_basica(mensaje, tabla=None):
    """Devuelve la fila (dict) cuyo ejemplo coincide con el mensaje, o None."""
    tabla = cargar_respuestas_basicas() if tabla is None else tabla
    if tabla.empty:
        return None
    texto = normalizar(mensaje)
    for _, fila in tabla.iterrows():
        if _es_afirmativo(fila.get("pasar_a_rag")):
            continue
        ejemplos = str(fila.get("ejemplos_usuario", "")).split("|")
        for ejemplo in ejemplos:
            ejemplo_normalizado = normalizar(ejemplo)
            if ejemplo_normalizado and ejemplo_normalizado in texto:
                return fila.to_dict()
    return None


def _formatear_respuesta(plantilla, contexto):
    contexto = contexto or {}
    carrera = contexto.get("carrera") or "la carrera seleccionada"
    carreras_disponibles = contexto.get("carreras_disponibles") or []
    perfiles_disponibles = contexto.get("perfiles_disponibles") or []
    return plantilla.format(
        carrera=carrera,
        carreras_disponibles=(
            " y ".join(carreras_disponibles)
            if carreras_disponibles
            else "las carreras cargadas en este MVP"
        ),
        perfiles_disponibles=(
            ", ".join(perfiles_disponibles)
            if perfiles_disponibles
            else "Estudiante, Coordinación demo y Admin demo"
        ),
    )


def responder_basica(mensaje, contexto=None):
    """Responde de inmediato saludos/identidad/ayuda; ``None`` si debe pasar a RAG."""
    if not mensaje or not str(mensaje).strip():
        return None
    if es_consulta_academica_o_documental(mensaje):
        return None

    fila = detectar_fila_basica(mensaje)
    if fila is None:
        return None

    texto = _formatear_respuesta(str(fila.get("respuesta", "")), contexto)
    if not texto:
        return None

    return RespuestaChatbot(tipo=str(fila["intencion"]), resumen=texto)
