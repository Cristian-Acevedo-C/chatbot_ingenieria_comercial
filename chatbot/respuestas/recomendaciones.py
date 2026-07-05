"""Respuestas de recomendación y solicitud de contexto."""

from chatbot.contratos import RespuestaChatbot, SeccionRespuesta
from utils.texto import normalizar


def respuesta_pedir_ramo(opciones_ramos):
    disponibles = [etiqueta for etiqueta in opciones_ramos if etiqueta != "Todos los ramos"]
    lista = "\n".join(f"- {etiqueta}" for etiqueta in disponibles)
    return RespuestaChatbot(
        tipo="pedir_ramo",
        resumen="¿Sobre qué ramo quieres que revise esa información?",
        secciones=[
            SeccionRespuesta(
                titulo="Ramos inscritos",
                contenido=(
                    lista
                    or "No hay ramos inscritos registrados para este alumno."
                ),
                formato="markdown",
            )
        ],
        recomendacion=(
            "Escribe el nombre o el código del ramo y lo reviso enseguida."
        ),
        fuentes=["`data/ramos_inscritos.csv`."],
    )


def respuesta_recomendacion(ramos, historial, prerrequisitos_alumno):
    if ramos.empty:
        return RespuestaChatbot(
            tipo="recomendacion",
            resumen="Aún no hay ramos inscritos registrados para recomendar.",
            recomendacion=(
                "Cuando existan ramos inscritos podré sugerirte un orden."
            ),
            fuentes=["`data/ramos_inscritos.csv`."],
            metadata={"titulo_recomendacion": "Recomendación de estudio"},
        )
    riesgos = prerrequisitos_alumno[
        (prerrequisitos_alumno["tipo"] == "Prerrequisito")
        & (prerrequisitos_alumno["alerta"].isin(["Riesgo alto", "Riesgo medio", "Pendiente"]))
    ].copy()
    if not riesgos.empty:
        orden = {"Riesgo alto": 0, "Riesgo medio": 1, "Pendiente": 2}
        riesgos["_orden"] = riesgos["alerta"].map(orden).fillna(3)
        riesgos = riesgos.sort_values("_orden")
        top = riesgos.iloc[0]
        breve = (
            f"Te sugiero partir por **{top['codigo_ramo']} — {top['nombre_ramo']}**, porque su "
            f"prerrequisito **{top['codigo_prerrequisito']} — {top['nombre_prerrequisito']}** "
            f"figura como **{top['estado_prerrequisito']} ({top['alerta']})**."
        )
        detalle = "\n".join(
            f"- **{fila['codigo_ramo']} — {fila['nombre_ramo']}** depende de "
            f"**{fila['codigo_prerrequisito']}** ({fila['estado_prerrequisito']}; {fila['alerta']})."
            for _, fila in riesgos.iterrows()
        )
        fuente = "`data/prerrequisitos.csv` y `data/historial_academico.csv`"
    else:
        reprobados = (
            historial[historial["estado"].astype(str).map(normalizar) == "reprobado"]
            if not historial.empty
            else historial.iloc[0:0]
        )
        if not reprobados.empty:
            primero = reprobados.iloc[0]
            breve = (
                "No veo prerrequisitos pendientes, pero podrías retomar primero "
                f"**{primero['codigo_ramo']} — {primero['nombre_ramo']}**, que figura reprobado "
                "en tu historial."
            )
            detalle = "\n".join(
                f"- **{fila['codigo_ramo']} — {fila['nombre_ramo']}** (nota {fila['nota']})."
                for _, fila in reprobados.iterrows()
            )
            fuente = "`data/historial_academico.csv`"
        else:
            primero = ramos.iloc[0]
            breve = (
                "No hay una señal de riesgo en tus datos, así que puedes empezar por "
                f"**{primero['codigo_ramo']} — {primero['nombre_ramo']}** y avanzar según tu preferencia."
            )
            detalle = "No se detectaron prerrequisitos pendientes ni ramos reprobados en tu historial."
            fuente = "`data/ramos_inscritos.csv`"
    return RespuestaChatbot(
        tipo="recomendacion",
        resumen=breve,
        secciones=[
            SeccionRespuesta(
                titulo="Evidencia encontrada",
                contenido=detalle,
                formato="markdown",
            )
        ],
        recomendacion=(
            "Esta sugerencia usa solo tus datos locales; confirma el orden con "
            "tu malla y con coordinación académica."
        ),
        fuentes=[f"{fuente}."],
        metadata={"titulo_recomendacion": "Recomendación de estudio"},
    )
