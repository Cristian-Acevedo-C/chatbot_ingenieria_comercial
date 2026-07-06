"""Clasificación heurística central de consultas."""

import re
from dataclasses import dataclass

from config.settings import AGRADECIMIENTOS, CONFUSION, HINTS_ACADEMICOS, SALUDOS
from utils.texto import normalizar  # reexport de compatibilidad temporal


@dataclass(frozen=True)
class ClasificacionConsulta:
    intencion: str
    codigo_ramo: str | None
    nombre_ramo: str | None
    confianza: str
    requiere_ramo: bool
    es_seguimiento: bool
    pregunta_normalizada: str


def normalizar_intencion(texto):
    texto = normalizar(texto)
    texto = re.sub(r"[-_/]+", " ", texto)
    texto = re.sub(r"[^a-z0-9ñ\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def es_consulta_prerrequisitos(texto):
    compacto = normalizar_intencion(texto).replace(" ", "")
    return "prerrequisit" in compacto or "prerequisit" in compacto


def es_consulta_evaluaciones(texto):
    consulta = normalizar_intencion(texto)
    return (
        "evalua" in consulta
        or any(
            frase in consulta
            for frase in ("cuanto vale", "porcentaje", "ponderacion")
        )
        or any(
            re.search(rf"\b{raiz}\w*\b", consulta)
            for raiz in ("prueba", "control", "examen", "catedra")
        )
    )


def es_consulta_ramos_inscritos(texto):
    consulta = normalizar_intencion(texto)
    return bool(
        re.search(r"\b(?:q|que)\s+ramos\s+tengo\b", consulta)
        or ("ramos" in consulta and any(clave in consulta for clave in ("inscrito", "tengo")))
    )


def es_consulta_alertas(texto):
    consulta = normalizar_intencion(texto)
    return any(
        clave in consulta
        for clave in (
            "alerta",
            "estoy atrasado",
            "voy atrasado",
            "atrasado",
            "riesgo academico",
            "riesgo",
            "reprobado",
        )
    )


def es_consulta_avance(texto):
    consulta = normalizar_intencion(texto)
    return any(
        clave in consulta
        for clave in ("malla", "avance curricular", "avance")
    )


def es_consulta_orientacion_academica(texto):
    """Preguntas de orientación (priorizar, ramos críticos, qué desbloquea, etc.).

    Distinto de ``es_consulta_avance``/``es_consulta_alertas``: no pide un dato
    puntual, sino una lectura combinada de malla + prerrequisitos + historial.
    Usa palabras clave sueltas (no frases rígidas) para tolerar variaciones
    naturales como "ramos son críticos" en vez de "ramos críticos".
    """
    consulta = normalizar_intencion(texto)
    if any(
        clave in consulta
        for clave in (
            "priorizar", "critico", "desbloquea", "antes de tomar",
            "repruebo", "atrasar", "significa el semaforo",
            "es el semaforo", "mi semaforo",
        )
    ):
        return True
    if "mejorar" in consulta and "avance" in consulta:
        return True
    if "importantes" in consulta and "avanzar" in consulta:
        return True
    return False

def detectar_ramo(malla, pregunta):
    if malla.empty:
        return None, None

    pregunta_normalizada = normalizar(pregunta)
    for _, ramo in malla.iterrows():
        codigo = str(ramo["codigo_ramo"])
        nombre = str(ramo["nombre_ramo"])
        if re.search(rf"\b{re.escape(normalizar(codigo))}\b", pregunta_normalizada):
            return codigo, nombre
        nombre_normalizado = normalizar(nombre)
        if re.search(rf"(?<!\w){re.escape(nombre_normalizado)}(?!\w)", pregunta_normalizada):
            return codigo, nombre

    mejor_ramo = None
    mejor_score = 0
    palabras_pregunta = set(re.findall(r"[a-z0-9]+", pregunta_normalizada))
    for _, ramo in malla.iterrows():
        palabras_ramo = {
            palabra
            for palabra in re.findall(r"[a-z0-9]+", normalizar(ramo["nombre_ramo"]))
            if len(palabra) >= 5
        }
        score = len(palabras_ramo & palabras_pregunta)
        if score > mejor_score:
            mejor_score = score
            mejor_ramo = ramo

    if mejor_ramo is not None and mejor_score > 0:
        return str(mejor_ramo["codigo_ramo"]), str(mejor_ramo["nombre_ramo"])
    return None, None

def detectar_tipo_pregunta(pregunta):
    texto = normalizar_intencion(pregunta)
    if es_consulta_prerrequisitos(texto):
        return "prerrequisitos"
    if "bibliograf" in texto or "libros" in texto or "lecturas" in texto:
        return "bibliografia"
    if "aprendiz" in texto or "resultados de aprendizaje" in texto:
        return "aprendizajes"
    if es_consulta_evaluaciones(texto):
        return "evaluaciones"
    if any(frase in texto for frase in ("que deberia estudiar", "que estudiar", "como estudiar")):
        return "estudio"
    if any(palabra in texto for palabra in ("contenidos", "unidades", "temas")):
        return "contenidos"
    return "documental"



def detectar_intencion_social(pregunta):
    texto = normalizar_intencion(pregunta)
    if any(frase in texto for frase in CONFUSION):
        return "confusion"
    if any(hint in texto for hint in HINTS_ACADEMICOS):
        return None
    palabras = texto.split()
    if len(palabras) <= 5:
        if any(saludo in palabras for saludo in ("hola", "holi", "buenas", "hey", "saludos")) or any(
            texto == saludo or texto.startswith(saludo) for saludo in SALUDOS
        ):
            return "saludo"
        if any(gracias in palabras for gracias in ("gracias", "vale", "perfecto", "genial", "excelente")) or any(
            texto.startswith(agradecimiento) for agradecimiento in AGRADECIMIENTOS
        ):
            return "agradecimiento"
    return None


def es_recomendacion(pregunta):
    texto = normalizar(pregunta)
    return any(
        frase in texto
        for frase in (
            "cual reviso primero", "cual reviso", "que reviso primero", "que hago ahora",
            "por donde parto", "por donde empiezo", "por donde comienzo",
            "que estudio primero", "cual estudio primero", "cual me recomiendas",
            "cual priorizo",
        )
    )


def es_seguimiento_de_ramo(pregunta):
    texto = normalizar_intencion(pregunta)
    if es_consulta_prerrequisitos(texto) or es_consulta_evaluaciones(texto):
        return True
    claves = (
        "bibliograf", "contenido", "puedo cursar", "cursarlo", "que estudiar",
        "deberia estudiar", "que repaso",
    )
    if any(clave in texto for clave in claves):
        return True
    return bool(re.match(r"^y\s+(la|el|los|las|del|de)\b", texto))


def clasificar_consulta(pregunta, malla=None, ramo_contexto=None):
    texto = normalizar_intencion(pregunta)
    social = detectar_intencion_social(pregunta)
    if social:
        return ClasificacionConsulta(
            social, None, None, "alta", False, False, texto
        )
    if es_recomendacion(pregunta):
        return ClasificacionConsulta(
            "recomendacion", None, None, "alta", False, False, texto
        )

    codigo = nombre = None
    if malla is not None and not malla.empty:
        codigo, nombre = detectar_ramo(malla, pregunta)
    seguimiento = es_seguimiento_de_ramo(pregunta)
    uso_contexto = False
    if codigo is None and seguimiento and ramo_contexto:
        codigo = ramo_contexto.get("codigo_ramo")
        nombre = ramo_contexto.get("nombre_ramo")
        uso_contexto = bool(codigo)

    if es_consulta_ramos_inscritos(texto):
        intencion = "ramos_inscritos"
    elif any(frase in texto for frase in ("puedo cursar", "cursarlo", "lo puedo tomar")):
        intencion = "puede_cursar"
    elif es_consulta_prerrequisitos(texto):
        intencion = "prerrequisitos"
    elif es_consulta_alertas(texto):
        intencion = "alertas"
    elif es_consulta_orientacion_academica(texto):
        intencion = "orientacion_academica"
    elif es_consulta_avance(texto):
        intencion = "avance_curricular"
    elif any(palabra in texto for palabra in ("sede", "jornada", "carrera", "semestre")):
        intencion = "datos_alumno"
    else:
        intencion = detectar_tipo_pregunta(pregunta)

    requiere_ramo = intencion in {
        "puede_cursar",
        "contenidos",
        "bibliografia",
        "evaluaciones",
        "estudio",
        "aprendizajes",
    }
    if intencion == "prerrequisitos":
        consulta_global = any(
            clave in texto
            for clave in (
                "todos",
                "pendiente",
                "no detectado",
                "no tienen",
                "sin prerequisito",
                "sin pre requisito",
            )
        )
        requiere_ramo = not consulta_global and (
            codigo is not None
            or seguimiento
            or any(clave in texto for clave in ("tiene", "para", " del ", " de "))
        )

    if requiere_ramo and not codigo:
        return ClasificacionConsulta(
            "pedir_ramo", None, None, "baja", True, seguimiento, texto
        )

    confianza = "alta" if codigo and not uso_contexto else "media" if uso_contexto else "alta"
    return ClasificacionConsulta(
        intencion,
        str(codigo) if codigo else None,
        str(nombre) if nombre else None,
        confianza,
        requiere_ramo,
        seguimiento,
        texto,
    )


def clasificar_intencion(pregunta, codigo=None):
    """Adaptador temporal para llamadas antiguas; usar `clasificar_consulta`."""
    contexto = (
        {"codigo_ramo": str(codigo), "nombre_ramo": None} if codigo else None
    )
    return clasificar_consulta(
        pregunta, malla=None, ramo_contexto=contexto
    ).intencion


