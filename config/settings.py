"""Constantes y rutas compartidas por la aplicación."""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
LOGO_UDLA = ASSETS_DIR / "logo_udla.png"
LOGO_UDLA_FINE = ASSETS_DIR / "logo_udla_fine.png"
UMBRAL_SIMILITUD = 0.05
TOP_K = 4

# Motor de búsqueda documental: "auto" (embeddings si están disponibles, TF-IDF
# en caso contrario), "tfidf" (forzar disperso) o "embeddings" (forzar semántico
# con fallback a TF-IDF). Configurable por variable de entorno CHATBOT_BUSQUEDA.
_METODOS_BUSQUEDA_VALIDOS = {"auto", "tfidf", "embeddings"}
METODO_BUSQUEDA = os.environ.get("CHATBOT_BUSQUEDA", "auto").strip().lower()
if METODO_BUSQUEDA not in _METODOS_BUSQUEDA_VALIDOS:
    METODO_BUSQUEDA = "auto"

STOPWORDS_ES = {
    "a", "al", "algo", "como", "con", "cual", "cuando", "de", "del", "desde",
    "donde", "el", "ella", "en", "es", "esta", "este", "hay", "hoy", "la", "las", "lo",
    "los", "mi", "mis", "o", "para", "por", "que", "quien", "se", "si", "sin",
    "sobre", "su", "sus", "un", "una", "uno", "y", "ya",
}

PREGUNTAS_GENERALES = [
    "¿Qué ramos tengo inscritos?",
    "¿Cuál es mi sede y jornada?",
    "¿Tengo alguna alerta académica?",
    "¿Tengo prerrequisitos pendientes?",
]

CLAVES_ESTADO_CONVERSACIONAL = (
    "historial_conversacion",
    "ultimo_ramo_codigo",
    "ultimo_ramo_nombre",
    "ultima_intencion",
    "ultima_alerta",
    "ultimo_tema",
    "pregunta_pendiente",
)

ESQUEMAS = {
    "alumnos.csv": {"id_alumno", "nombre", "carrera", "sede", "jornada", "semestre_actual"},
    "malla.csv": {"codigo_ramo", "nombre_ramo", "semestre"},
    "ramos_inscritos.csv": {"id_alumno", "codigo_ramo", "nombre_ramo", "estado"},
    "historial_academico.csv": {"id_alumno", "codigo_ramo", "nombre_ramo", "estado", "nota"},
    "document_chunks.csv": {
        "chunk_id",
        "codigo_ramo",
        "nombre_ramo",
        "ruta_archivo",
        "texto",
    },
    "prerrequisitos.csv": {
        "codigo_ramo",
        "nombre_ramo",
        "codigo_prerrequisito",
        "nombre_prerrequisito",
        "tipo",
        "fuente_archivo",
        "evidencia_textual",
        "confianza",
    },
}


APERTURAS = (
    "Perfecto, revisé la información disponible.",
    "Buena pregunta. Te lo resumo de forma clara.",
    "Claro, revisemos eso con los datos cargados.",
    "Qué bueno que lo preguntes, porque esto ayuda a planificar mejor.",
    "Entiendo. Vamos por partes.",
)

MENSAJES_SOCIALES = {
    "saludo": (
        "Hola, qué bueno verte por acá. Soy tu asistente académico. Puedo ayudarte a "
        "revisar tus ramos, qué estudiar, prerrequisitos, bibliografía o alertas "
        "académicas. ¿Qué quieres revisar primero?"
    ),
    "agradecimiento": (
        "De nada. Me alegra que te sirva. ¿Quieres revisar otro ramo o prefieres ver "
        "tus alertas académicas?"
    ),
    "confusion": (
        "Tranquilo, podemos ordenarlo paso a paso. Primero puedo revisar tus ramos "
        "inscritos y luego sugerirte cuál estudiar según contenidos, prerrequisitos y "
        "alertas. ¿Quieres que partamos por tus ramos inscritos?"
    ),
}

PREGUNTAS_CIERRE = {
    "estudio": "¿Quieres que ahora revise la bibliografía o los prerrequisitos de este ramo?",
    "contenidos": "¿Quieres que revise las evaluaciones o los prerrequisitos de este ramo?",
    "bibliografia": "¿Quieres que también te sugiera qué contenidos estudiar primero?",
    "evaluaciones": "¿Quieres que veamos qué contenidos conviene priorizar para esas evaluaciones?",
    "aprendizajes": "¿Quieres que revise las unidades o la evaluación de este ramo?",
    "prerrequisitos": "¿Quieres que revise si tienes alguno pendiente según tu historial?",
    "puede_cursar": "¿Quieres que revise si tienes algún prerrequisito pendiente según tu historial?",
    "alertas": "¿Quieres que te muestre qué acción podrías tomar primero?",
    "ramos_inscritos": "¿Quieres que te recomiende cuál revisar primero?",
    "datos_alumno": "¿Quieres que revisemos tus ramos inscritos o tus alertas académicas?",
    "avance_curricular": "¿Quieres que revisemos tus ramos inscritos o alguna alerta académica?",
    "documental": "¿Quieres que lo veamos para un ramo específico? Indícame su nombre o código.",
    "recomendacion": "¿Quieres que abramos uno de esos ramos para ver qué estudiar?",
    "pedir_ramo": None,
}

SALUDOS = (
    "hola", "holi", "buenas", "buen dia", "buenos dias", "buenas tardes",
    "buenas noches", "que tal", "como estas", "como andas", "hey", "saludos",
)
AGRADECIMIENTOS = (
    "gracias", "muchas gracias", "mil gracias", "vale", "perfecto", "genial",
    "excelente", "buenisimo",
)
CONFUSION = (
    "estoy perdido", "estoy perdida", "no se que estudiar", "no entiendo",
    "no se por donde partir", "no se por donde empezar", "no se por donde comenzar",
    "no se por donde", "estoy confundido", "estoy confundida", "no se que hacer",
)
HINTS_ACADEMICOS = (
    "bibliograf", "contenido", "evaluacion", "evalua", "prerrequisit", "prerequisit",
    "estudiar", "estudio", "ramo", "cursar", "alerta", "riesgo", "inscrit", "sede",
    "jornada", "semestre", "malla", "avance", "ponderacion", "porcentaje", "cuanto vale", "examen",
    "prueba", "control", "catedra",
)

PREGUNTAS_RAPIDAS = PREGUNTAS_GENERALES
