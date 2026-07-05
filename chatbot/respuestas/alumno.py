"""Respuestas sobre ficha, inscripción y avance del alumno."""

import pandas as pd

from chatbot.contratos import RespuestaChatbot, SeccionRespuesta
from chatbot.intenciones import normalizar


def respuesta_ramos(ramos):
    if ramos.empty:
        resumen = "No hay ramos inscritos registrados para el alumno seleccionado."
        evidencia = "El archivo de inscripciones no contiene filas asociadas a este alumno."
    else:
        resumen = f"El alumno tiene **{len(ramos)} ramos inscritos**."
        evidencia = "\n".join(
            f"- **{fila['codigo_ramo']}** — {fila['nombre_ramo']} ({fila['estado']})"
            for _, fila in ramos.iterrows()
        )
    return RespuestaChatbot(
        tipo="ramos_inscritos",
        resumen=resumen,
        secciones=[
            SeccionRespuesta(
                titulo="Evidencia encontrada",
                contenido=evidencia,
                formato="markdown",
            )
        ],
        recomendacion=(
            "Prioriza semanalmente los ramos con evaluaciones más próximas y "
            "reserva bloques de repaso para los cursos cuantitativos."
        ),
        fuentes=["`data/ramos_inscritos.csv`."],
        metadata={"titulo_recomendacion": "Recomendación de estudio"},
    )


def respuesta_datos_alumno(alumno):
    return RespuestaChatbot(
        tipo="datos_alumno",
        resumen=(
            f"**{alumno['nombre']}** estudia en sede **{alumno['sede']}**, jornada "
            f"**{alumno['jornada']}**, y cursa el semestre "
            f"**{alumno['semestre_actual']}**."
        ),
        secciones=[
            SeccionRespuesta(
                titulo="Evidencia encontrada",
                contenido=f"Carrera registrada: **{alumno['carrera']}**.",
                formato="markdown",
            )
        ],
        recomendacion=(
            "Organiza tu planificación según la jornada y los horarios oficiales "
            "informados por la institución."
        ),
        fuentes=["`data/alumnos.csv`."],
        metadata={"titulo_recomendacion": "Recomendación de estudio"},
    )


def respuesta_avance_curricular(alumno, historial, malla):
    estados = (
        historial["estado"].fillna("").astype(str).map(normalizar)
        if not historial.empty
        else pd.Series(dtype=str)
    )
    aprobados = int((estados == "aprobado").sum())
    cursando = int((estados == "cursando").sum())
    reprobados = int((estados == "reprobado").sum())
    return RespuestaChatbot(
        tipo="avance_curricular",
        resumen=(
            f"El alumno figura en el semestre **{alumno['semestre_actual']}**. "
            f"Con los registros locales disponibles se observan **{aprobados} "
            f"aprobados**, **{cursando} cursando** y **{reprobados} reprobados**."
        ),
        secciones=[
            SeccionRespuesta(
                titulo="Evidencia encontrada",
                contenido=(
                    f"La malla cargada contiene **{len(malla)} ramos**; el historial "
                    f"sintético contiene **{len(historial)} registros** para este alumno."
                ),
                formato="markdown",
            )
        ],
        advertencias=[
            "Estos datos no bastan para calcular un porcentaje oficial de avance curricular."
        ],
        fuentes=[
            "`data/alumnos.csv`, `data/historial_academico.csv` y `data/malla.csv`."
        ],
    )
