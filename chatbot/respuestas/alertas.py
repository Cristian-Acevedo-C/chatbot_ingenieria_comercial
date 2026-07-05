"""Respuestas de alertas académicas."""

from chatbot.contratos import RespuestaChatbot, SeccionRespuesta
from utils.texto import normalizar


def respuesta_alertas(historial, prerrequisitos_alumno, prerrequisitos_cargados):
    if historial.empty:
        resumen = "No existe historial suficiente para calcular una alerta académica."
        evidencia = "No hay registros académicos asociados al alumno seleccionado."
        recomendacion = "Confirma o completa el historial antes de evaluar avance o riesgo."
    else:
        reprobados = historial[
            historial["estado"].astype(str).map(normalizar) == "reprobado"
        ]
        cantidad = len(reprobados)
        if cantidad == 0:
            resumen = "No se observan ramos reprobados en el historial disponible."
            evidencia = f"Se revisaron **{len(historial)} registros** y no hay reprobaciones."
            recomendacion = "Mantén seguimiento de notas y carga académica; esto no reemplaza una revisión oficial."
        else:
            resumen = f"Se detectaron **{cantidad} ramos reprobados** en el historial disponible."
            detalle = "\n".join(
                f"- **{fila['codigo_ramo']}** — {fila['nombre_ramo']} | Nota: {fila['nota']}"
                for _, fila in reprobados.iterrows()
            )
            evidencia = f"Cantidad de reprobaciones: **{cantidad}**.\n\n{detalle}"
            recomendacion = (
                "Prioriza los ramos reprobados y solicita orientación académica antes de definir "
                "la próxima carga. No es posible afirmar atraso curricular solo con estos datos."
            )

    if prerrequisitos_cargados.empty:
        evidencia += "\n\n**Prerrequisitos:** No hay prerrequisitos cargados."
        fuente_prerrequisitos = ""
    else:
        alertas = prerrequisitos_alumno[
            (prerrequisitos_alumno["tipo"] == "Prerrequisito")
            & (prerrequisitos_alumno["alerta"] != "OK")
        ]
        incompletos = prerrequisitos_alumno[
            prerrequisitos_alumno["tipo"] == "No detectado"
        ]
        if alertas.empty:
            evidencia += (
                "\n\n**Revisión de prerrequisitos:** no se detectaron relaciones "
                "incumplidas entre los ramos inscritos y el historial disponible."
            )
        else:
            detalle_alertas = "\n".join(
                f"- **{fila['codigo_ramo']}** requiere **{fila['codigo_prerrequisito']}** "
                f"({fila['estado_prerrequisito']}; {fila['alerta']})."
                for _, fila in alertas.iterrows()
            )
            evidencia += (
                f"\n\n**Alertas de prerrequisitos ({len(alertas)}):**\n\n"
                f"{detalle_alertas}"
            )
            recomendacion += (
                " Revisa estas relaciones con coordinación académica antes de mantener "
                "la inscripción correspondiente."
            )
        if not incompletos.empty:
            codigos = ", ".join(sorted(incompletos["codigo_ramo"].unique()))
            evidencia += (
                "\n\n**Advertencia informativa:** hay prerrequisitos no detectados para "
                f"{codigos}; no se infiere ninguna relación adicional."
            )
        fuente_prerrequisitos = " y `data/prerrequisitos.csv`"

    return RespuestaChatbot(
        tipo="alertas",
        resumen=resumen,
        secciones=[
            SeccionRespuesta(
                titulo="Evidencia encontrada",
                contenido=evidencia,
                formato="markdown",
            )
        ],
        recomendacion=recomendacion,
        fuentes=[
            f"`data/historial_academico.csv`{fuente_prerrequisitos}."
        ],
        metadata={"titulo_recomendacion": "Recomendación de estudio"},
    )
