"""Métricas agregadas para el panel de resumen visual (sin lógica de negocio nueva).

Todas las cifras se calculan a partir de los datos ya cargados y filtrados por
``st.session_state["carrera"]``; no se agregan valores fijos ni supuestos.
"""

from services.cobertura import calcular_cobertura_documental
from services.datos import obtener_fecha_metadata, obtener_programas_pendientes
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


def calcular_metricas_sistema(
    carrera,
    alumnos_carrera,
    historial_carrera,
    chunks_carrera,
    malla_carrera,
    prerrequisitos_carrera,
    etiqueta_motor=None,
):
    """Métricas reales del sistema para la carrera activa (panel Admin demo).

    Todo se calcula desde los datos ya cargados y filtrados; lo que no puede
    calcularse (p. ej. no hay manifiesto de metadata para la carrera) se
    declara explícitamente "No disponible" en vez de omitirse o inventarse.
    """
    resumen_documental = calcular_resumen_documental(
        carrera, chunks_carrera, malla_carrera, prerrequisitos_carrera
    )
    fecha_metadata = obtener_fecha_metadata(carrera)
    return {
        "carrera": carrera,
        "documentos_disponibles": resumen_documental["programas_disponibles"],
        "programas_pendientes": len(resumen_documental["programas_pendientes"]),
        "ramos_en_malla": resumen_documental["ramos_en_malla"],
        "prerrequisitos_cargados": resumen_documental["prerrequisitos_extraidos"],
        "fragmentos_indexados": int(len(chunks_carrera)) if chunks_carrera is not None else 0,
        "alumnos_demo": int(len(alumnos_carrera)) if alumnos_carrera is not None else 0,
        "registros_historial": int(len(historial_carrera)) if historial_carrera is not None else 0,
        "ultima_actualizacion_metadata": fecha_metadata or "No disponible",
        "motor_busqueda": etiqueta_motor or "No disponible",
        "estado_general": "Operativo demo",
    }


def construir_guion_demo(carrera, alumno, chunks_carrera, resumen_documental, carreras_disponibles):
    """Guion de demo guiada: preguntas reales (basadas en datos cargados) y qué
    demuestra cada una. No hardcodea ningún ramo, alumno ni carrera: usa lo que
    esté efectivamente disponible en la sesión activa."""
    guion = [
        (
            "hola cómo estás",
            "Respuesta básica inmediata, sin activar el buscador documental (RAG).",
        ),
        (
            "qué puedes hacer",
            "Orientación conversacional: qué temas puede responder el asistente.",
        ),
    ]

    nombre_alumno = str(alumno["nombre"]) if alumno is not None else None
    if nombre_alumno:
        guion.append((
            "qué avance tengo",
            f"Usa el historial académico sintético del alumno demo activo ({nombre_alumno}).",
        ))
        guion.append((
            "qué significa el semáforo de este alumno",
            "Explica el semáforo académico calculado desde historial y prerrequisitos.",
        ))

    ramo_con_evidencia = None
    if (
        chunks_carrera is not None
        and not chunks_carrera.empty
        and "codigo_ramo" in chunks_carrera.columns
    ):
        codigos = chunks_carrera["codigo_ramo"].dropna().astype(str)
        if not codigos.empty:
            ramo_con_evidencia = codigos.iloc[0]
    if ramo_con_evidencia:
        guion.append((
            f"qué contenidos tiene {ramo_con_evidencia}",
            "Búsqueda documental (RAG) con fuente y evidencia citada del programa real.",
        ))
        guion.append((
            f"qué prerrequisitos tiene {ramo_con_evidencia}",
            "Consulta de prerrequisitos extraídos del programa de asignatura.",
        ))

    pendientes = resumen_documental.get("programas_pendientes") or []
    if pendientes:
        guion.append((
            f"qué contenidos tiene {pendientes[0]}",
            f"{pendientes[0]} está registrado como pendiente (sin PDF cargado): el asistente "
            "debe decir que no encuentra evidencia, sin inventar contenido.",
        ))

    otra_carrera = next((c for c in carreras_disponibles if c != carrera), None)
    if otra_carrera and ramo_con_evidencia:
        guion.append((
            f"(cambia a {otra_carrera} y repite) qué contenidos tiene {ramo_con_evidencia}",
            f"Demuestra el aislamiento multicarrera: {ramo_con_evidencia} es de {carrera} y no "
            f"debería reconocerse en {otra_carrera}.",
        ))
    return guion
