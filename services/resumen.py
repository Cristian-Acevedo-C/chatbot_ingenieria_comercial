"""Métricas agregadas para el panel de resumen visual (sin lógica de negocio nueva).

Todas las cifras se calculan a partir de los datos ya cargados y filtrados por
``st.session_state["carrera"]``; no se agregan valores fijos ni supuestos.
"""

from services.cobertura import calcular_cobertura_documental
from services.datos import obtener_programas_pendientes
from utils.texto import normalizar


def calcular_resumen_documental(carrera, chunks_carrera, malla_carrera, prerrequisitos_carrera):
    """Resume cobertura documental y de prerrequisitos de la carrera activa."""
    cobertura = calcular_cobertura_documental(chunks_carrera)
    pendientes = obtener_programas_pendientes(carrera)
    disponibles = cobertura["fuentes_distintas"]
    return {
        "programas_disponibles": disponibles,
        "programas_pendientes": pendientes,
        "total_programas": disponibles + len(pendientes),
        "ramos_en_malla": int(len(malla_carrera)),
        "prerrequisitos_extraidos": int(len(prerrequisitos_carrera)),
    }


def calcular_semaforo_academico(historial_alumno, prerrequisitos_alumno):
    """Semáforo derivado del historial y de las alertas de prerrequisitos ya calculadas.

    Regla (deliberadamente simple y transparente, no un promedio ponderado):
    - Rojo: 2+ ramos reprobados o algún prerrequisito en "Riesgo alto".
    - Amarillo: 1 ramo reprobado o algún prerrequisito en "Riesgo medio".
    - Verde: sin reprobaciones ni alertas de prerrequisitos pendientes.
    """
    reprobados = 0
    if historial_alumno is not None and not historial_alumno.empty and "estado" in historial_alumno.columns:
        reprobados = int(
            historial_alumno["estado"].astype(str).map(normalizar).eq("reprobado").sum()
        )

    riesgo_alto = riesgo_medio = 0
    if (
        prerrequisitos_alumno is not None
        and not prerrequisitos_alumno.empty
        and "alerta" in prerrequisitos_alumno.columns
    ):
        riesgo_alto = int((prerrequisitos_alumno["alerta"] == "Riesgo alto").sum())
        riesgo_medio = int((prerrequisitos_alumno["alerta"] == "Riesgo medio").sum())

    if reprobados >= 2 or riesgo_alto >= 1:
        nivel = "rojo"
        etiqueta = "Riesgo académico"
    elif reprobados == 1 or riesgo_medio >= 1:
        nivel = "amarillo"
        etiqueta = "Atención"
    else:
        nivel = "verde"
        etiqueta = "Avance normal"

    detalle_partes = []
    if reprobados:
        detalle_partes.append(f"{reprobados} ramo(s) reprobado(s)")
    if riesgo_alto:
        detalle_partes.append(f"{riesgo_alto} prerrequisito(s) en riesgo alto")
    if riesgo_medio:
        detalle_partes.append(f"{riesgo_medio} prerrequisito(s) en riesgo medio")
    detalle = "; ".join(detalle_partes) or "Sin reprobaciones ni alertas de prerrequisitos detectadas."

    return {
        "nivel": nivel,
        "etiqueta": etiqueta,
        "detalle": detalle,
        "reprobados": reprobados,
        "riesgo_alto": riesgo_alto,
        "riesgo_medio": riesgo_medio,
    }
