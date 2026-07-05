"""Respuestas sobre relaciones y cumplimiento de prerrequisitos."""

import pandas as pd

from chatbot.contratos import RespuestaChatbot, SeccionRespuesta
from rag.busqueda import limpiar_fragmento
from services.datos import valor_texto
from services.prerrequisitos import calcular_metricas_prerrequisitos, construir_prerrequisitos_alumno


def _respuesta_prerrequisito(
    resumen,
    evidencia,
    recomendacion,
    fuentes,
    tipo="prerrequisitos",
):
    return RespuestaChatbot(
        tipo=tipo,
        resumen=resumen,
        secciones=[
            SeccionRespuesta(
                titulo="Evidencia encontrada",
                contenido=evidencia,
                formato="markdown",
            )
        ],
        recomendacion=recomendacion,
        fuentes=[fuentes],
        metadata={"titulo_recomendacion": "Recomendación de estudio"},
    )


def respuesta_todos_prerrequisitos(prerrequisitos):
    if prerrequisitos.empty:
        return respuesta_prerrequisitos_no_cargados()
    relaciones = prerrequisitos[prerrequisitos["tipo"] == "Prerrequisito"]
    detalle = "\n".join(
        f"- **{fila['codigo_ramo']} — {fila['nombre_ramo']}** requiere "
        f"**{fila['codigo_prerrequisito']} — {fila['nombre_prerrequisito']}**."
        for _, fila in relaciones.iterrows()
    )
    metricas = calcular_metricas_prerrequisitos(prerrequisitos)
    return _respuesta_prerrequisito(
        resumen=(
            f"Hay **{metricas['relaciones']} relaciones** de prerrequisito para "
            f"**{metricas['con_prerrequisito']} ramos**."
        ),
        evidencia=detalle,
        recomendacion=(
            "Usa el mapa como orientación y contrasta cada relación con la "
            "evidencia del programa de asignatura."
        ),
        fuentes="`data/prerrequisitos.csv`.",
    )


def respuesta_prerrequisitos_no_cargados():
    return _respuesta_prerrequisito(
        resumen="No hay prerrequisitos cargados.",
        evidencia="No existe información utilizable en `data/prerrequisitos.csv`.",
        recomendacion=(
            "Ejecuta el extractor local antes de consultar relaciones curriculares."
        ),
        fuentes="`data/prerrequisitos.csv`.",
    )


def respuesta_prerrequisitos_ramo(prerrequisitos, codigo, nombre, historial=None):
    if prerrequisitos.empty:
        return respuesta_prerrequisitos_no_cargados()
    if not codigo:
        return _respuesta_prerrequisito(
            resumen="No pude identificar el ramo consultado.",
            evidencia="Indica el código o el nombre completo del ramo.",
            recomendacion="Prueba, por ejemplo, `AEA315` o `Microeconomía II`.",
            fuentes="`data/malla.csv` y `data/prerrequisitos.csv`.",
        )

    filas = prerrequisitos[
        prerrequisitos["codigo_ramo"].astype(str) == str(codigo)
    ]
    if filas.empty:
        return _respuesta_prerrequisito(
            resumen=f"No hay información cargada para **{codigo} — {nombre}**.",
            evidencia="No existe una fila asociada en el CSV.",
            recomendacion="Revisa la cobertura del extractor.",
            fuentes="`data/prerrequisitos.csv`.",
        )

    tipo = valor_texto(filas.iloc[0]["tipo"])
    historial = historial if historial is not None else pd.DataFrame()
    ramo_objetivo = pd.DataFrame(
        [{"codigo_ramo": codigo, "nombre_ramo": nombre}]
    )
    vista = construir_prerrequisitos_alumno(
        ramo_objetivo, historial, prerrequisitos
    )
    if tipo == "Sin prerrequisito":
        breve = f"**{codigo} — {nombre}** figura sin prerrequisito explícito."
        detalle = "El campo de requisito del programa está vacío. Estado: **No aplica (OK)**."
    elif tipo == "No detectado":
        breve = f"Los prerrequisitos de **{codigo} — {nombre}** no fueron detectados."
        detalle = (
            "La evidencia existe, pero no produjo una relación válida con la malla actual. "
            "Estado: **No aplica (Información incompleta)**."
        )
    else:
        breve = f"**{codigo} — {nombre}** tiene {len(filas)} prerrequisito(s) registrado(s)."
        detalle = "\n".join(
            f"- **{fila['codigo_prerrequisito']} — {fila['nombre_prerrequisito']}**: "
            f"{fila['estado_prerrequisito']} ({fila['alerta']}; confianza: "
            f"{fila['confianza']})."
            for _, fila in vista.iterrows()
        )

    evidencias = "\n".join(
        f"- {limpiar_fragmento(fila['evidencia_textual'], limite=420)}"
        for _, fila in filas.drop_duplicates("evidencia_textual").iterrows()
    )
    fuentes = "\n".join(
        f"- {fuente}"
        for fuente in filas["fuente_archivo"].dropna().astype(str).unique()
        if fuente
    )
    return _respuesta_prerrequisito(
        resumen=breve,
        evidencia=f"{detalle}\n\n{evidencias}",
        recomendacion=(
            "Verifica el cumplimiento en tu historial y confirma las alternativas "
            "del requisito con coordinación académica."
        ),
        fuentes=fuentes or "`data/prerrequisitos.csv`.",
    )


def respuesta_ramos_por_tipo(prerrequisitos, tipo, descripcion):
    if prerrequisitos.empty:
        return respuesta_prerrequisitos_no_cargados()
    filas = prerrequisitos[prerrequisitos["tipo"] == tipo].drop_duplicates("codigo_ramo")
    detalle = "\n".join(
        f"- **{fila['codigo_ramo']} — {fila['nombre_ramo']}**"
        for _, fila in filas.iterrows()
    )
    return _respuesta_prerrequisito(
        resumen=f"Hay **{len(filas)} ramos** {descripcion}.",
        evidencia=detalle or "No se encontraron ramos.",
        recomendacion=(
            "Consulta la evidencia textual del mapa antes de tomar decisiones académicas."
        ),
        fuentes="`data/prerrequisitos.csv`.",
    )


def respuesta_prerrequisitos_pendientes(prerrequisitos_alumno, prerrequisitos):
    if prerrequisitos.empty:
        return respuesta_prerrequisitos_no_cargados()
    alertas = prerrequisitos_alumno[
        (prerrequisitos_alumno["tipo"] == "Prerrequisito")
        & (prerrequisitos_alumno["alerta"] != "OK")
    ]
    incompletos = prerrequisitos_alumno[
        prerrequisitos_alumno["tipo"] == "No detectado"
    ]
    if alertas.empty:
        breve = "No se detectaron prerrequisitos pendientes en los ramos inscritos."
        detalle = "Todos los prerrequisitos registrados aparecen aprobados o no aplican."
    else:
        breve = f"Se detectaron **{len(alertas)} relaciones pendientes o en riesgo**."
        detalle = "\n".join(
            f"- **{fila['codigo_ramo']}** requiere **{fila['codigo_prerrequisito']}**: "
            f"{fila['estado_prerrequisito']} ({fila['alerta']})."
            for _, fila in alertas.iterrows()
        )
    if not incompletos.empty:
        detalle += (
            "\n\nInformación incompleta para: "
            + ", ".join(sorted(incompletos["codigo_ramo"].unique()))
            + "."
        )
    return _respuesta_prerrequisito(
        resumen=breve,
        evidencia=detalle,
        recomendacion=(
            "Regulariza primero los prerrequisitos reprobados o pendientes y "
            "confirma los casos incompletos con coordinación académica."
        ),
        fuentes=(
            "`data/prerrequisitos.csv` y `data/historial_academico.csv`."
        ),
    )


def respuesta_puede_cursar(codigo, nombre, historial, prerrequisitos):
    if prerrequisitos.empty:
        return respuesta_prerrequisitos_no_cargados()
    if not codigo:
        return respuesta_prerrequisitos_ramo(
            prerrequisitos, codigo, nombre, historial
        )
    ramo = pd.DataFrame([{"codigo_ramo": codigo, "nombre_ramo": nombre}])
    vista = construir_prerrequisitos_alumno(ramo, historial, prerrequisitos)
    if vista.empty:
        return respuesta_prerrequisitos_ramo(
            prerrequisitos, codigo, nombre, historial
        )

    tipo = vista.iloc[0]["tipo"]
    if tipo == "Sin prerrequisito":
        breve = f"**{codigo} — {nombre}** no tiene prerrequisito explícito registrado."
        detalle = "Estado: No aplica (OK)."
    elif tipo == "No detectado":
        breve = f"No es posible evaluar **{codigo} — {nombre}** con información completa."
        detalle = "El CSV marca el requisito como No detectado; no se infieren relaciones."
    else:
        pendientes = vista[vista["alerta"] != "OK"]
        if pendientes.empty:
            breve = (
                f"Todos los prerrequisitos registrados para **{codigo} — {nombre}** "
                "figuran aprobados."
            )
        else:
            breve = (
                f"No se puede confirmar el cumplimiento de todos los prerrequisitos "
                f"registrados para **{codigo} — {nombre}**."
            )
        detalle = "\n".join(
            f"- **{fila['codigo_prerrequisito']} — {fila['nombre_prerrequisito']}**: "
            f"{fila['estado_prerrequisito']} ({fila['alerta']})."
            for _, fila in vista.iterrows()
        )
    return _respuesta_prerrequisito(
        resumen=breve,
        evidencia=detalle,
        recomendacion=(
            "Esta evaluación usa solo el historial y las relaciones extraídas; "
            "confirma la autorización formal con la universidad."
        ),
        fuentes=(
            "`data/prerrequisitos.csv` y `data/historial_academico.csv`."
        ),
        tipo="puede_cursar",
    )
