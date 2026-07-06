"""Respuestas estructuradas de estudio, contenidos y evaluación."""

from pathlib import Path

import pandas as pd

from chatbot.contratos import Evidencia, RespuestaChatbot, SeccionRespuesta
from rag.busqueda import seleccionar_evidencias
from rag.extractores import (
    construir_plan_estudio,
    extraer_aprendizajes_desde_texto,
    extraer_bibliografia_desde_texto,
    extraer_contenidos_desde_texto,
    extraer_evaluaciones_desde_texto,
    reconstruir_texto_ramo,
)
from services.prerrequisitos import construir_prerrequisitos_alumno


def construir_respuesta_academica(
    tipo,
    codigo,
    nombre,
    chunks,
    resultados,
    prerrequisitos,
    historial,
):
    texto_programa = reconstruir_texto_ramo(chunks, codigo)
    contenidos = extraer_contenidos_desde_texto(texto_programa)
    aprendizajes = extraer_aprendizajes_desde_texto(texto_programa)
    bibliografia = extraer_bibliografia_desde_texto(texto_programa)
    evaluaciones = extraer_evaluaciones_desde_texto(texto_programa)
    evidencias = seleccionar_evidencias(chunks, codigo, tipo, resultados)

    if tipo == "estudio":
        if contenidos:
            bloques = ", ".join(
                contenido["Tema principal"] for contenido in contenidos[:5]
            )
            resumen = (
                f"Para **{codigo} — {nombre}**, prioriza estos bloques del programa: "
                f"{bloques}. Avanza en el orden de las unidades y usa los temas detectados "
                "como lista de repaso."
            )
        else:
            resumen = (
                f"Encontré evidencia para **{codigo} — {nombre}**, pero no pude convertir "
                "la sección de contenidos en una tabla confiable."
            )
    elif tipo == "contenidos":
        if contenidos:
            temas_destacados = ", ".join(
                contenido["Tema principal"] for contenido in contenidos[:3]
            )
            resumen = (
                f"**{codigo} — {nombre}** aborda contenidos como {temas_destacados}, según "
                f"la evidencia disponible en el programa cargado "
                f"({len(contenidos)} unidad(es) estructurada(s) detectada(s))."
            )
        else:
            resumen = f"No pude extraer una tabla limpia de contenidos para **{codigo} — {nombre}**."
    elif tipo == "bibliografia":
        resumen = (
            f"Detecté **{len(bibliografia)} referencias bibliográficas** en el programa de "
            f"**{codigo} — {nombre}**."
            if bibliografia
            else f"No pude extraer referencias bibliográficas estructuradas para **{codigo} — {nombre}**."
        )
    elif tipo == "evaluaciones":
        resumen = (
            f"Detecté **{len(evaluaciones)} componentes de evaluación** en el programa de "
            f"**{codigo} — {nombre}**."
            if evaluaciones
            else f"No pude extraer una tabla limpia de evaluaciones para **{codigo} — {nombre}**."
        )
    else:
        resumen = (
            f"Detecté **{len(aprendizajes)} resultados de aprendizaje** declarados "
            f"en el programa de **{codigo} — {nombre}**."
            if aprendizajes
            else f"No pude extraer resultados de aprendizaje estructurados para **{codigo} — {nombre}**."
        )

    vista_prerrequisitos = []
    if tipo == "estudio":
        ramo_objetivo = pd.DataFrame(
            [{"codigo_ramo": codigo, "nombre_ramo": nombre}]
        )
        tabla_prerrequisitos = construir_prerrequisitos_alumno(
            ramo_objetivo, historial, prerrequisitos
        )
        if not tabla_prerrequisitos.empty:
            vista_prerrequisitos = (
                tabla_prerrequisitos[
                    [
                        "codigo_prerrequisito",
                        "nombre_prerrequisito",
                        "tipo",
                        "estado_prerrequisito",
                        "alerta",
                    ]
                ]
                .rename(
                    columns={
                        "codigo_prerrequisito": "Código",
                        "nombre_prerrequisito": "Ramo previo",
                        "tipo": "Tipo",
                        "estado_prerrequisito": "Estado",
                        "alerta": "Alerta",
                    }
                )
                .to_dict("records")
            )

    contenidos_visibles = contenidos if tipo in {"estudio", "contenidos"} else []
    plan = construir_plan_estudio(contenidos) if tipo == "estudio" else []
    bibliografia_visible = (
        bibliografia if tipo in {"estudio", "bibliografia"} else []
    )
    evaluaciones_visibles = evaluaciones if tipo == "evaluaciones" else []
    aprendizajes_visibles = aprendizajes if tipo == "aprendizajes" else []
    fuentes = [
        f"Fuente: {nombre_archivo}"
        for nombre_archivo in dict.fromkeys(
            Path(str(ruta)).name
            for ruta in chunks.loc[
                chunks["codigo_ramo"].astype(str).eq(str(codigo)), "ruta_archivo"
            ].dropna()
        )
    ]
    secciones = []
    if contenidos_visibles:
        secciones.append(
            SeccionRespuesta(
                titulo=(
                    "Qué estudiar"
                    if tipo == "estudio"
                    else "Unidades y contenidos"
                ),
                contenido=contenidos_visibles,
                formato="tabla",
            )
        )
    if plan:
        secciones.append(
            SeccionRespuesta(
                titulo="Plan sugerido",
                contenido=plan,
                formato="tabla",
            )
        )
    if vista_prerrequisitos:
        secciones.append(
            SeccionRespuesta(
                titulo="Prerrequisitos académicos",
                contenido=vista_prerrequisitos,
                formato="tabla",
            )
        )
    if bibliografia_visible:
        secciones.append(
            SeccionRespuesta(
                titulo="Bibliografía",
                contenido=bibliografia_visible,
                formato="tabla",
            )
        )
    if evaluaciones_visibles:
        secciones.append(
            SeccionRespuesta(
                titulo="Evaluaciones detectadas",
                contenido=evaluaciones_visibles,
                formato="tabla",
            )
        )
    if aprendizajes_visibles:
        secciones.append(
            SeccionRespuesta(
                titulo="Resultados de aprendizaje",
                contenido=aprendizajes_visibles,
                formato="tabla",
            )
        )

    # La consulta general "qué contenidos tiene X" (el punto de entrada más común
    # al preguntar por un ramo) también asoma evaluación y bibliografía cuando hay
    # evidencia, o lo dice explícitamente cuando no la hay; nunca se inventa.
    if tipo == "contenidos":
        if evaluaciones:
            secciones.append(
                SeccionRespuesta(titulo="Evaluación", contenido=evaluaciones, formato="tabla")
            )
        else:
            secciones.append(
                SeccionRespuesta(
                    titulo="Evaluación",
                    contenido=(
                        "No encontré evidencia suficiente sobre evaluación en los "
                        "fragmentos consultados."
                    ),
                    formato="markdown",
                )
            )
        if bibliografia:
            secciones.append(
                SeccionRespuesta(titulo="Bibliografía", contenido=bibliografia, formato="tabla")
            )
        else:
            secciones.append(
                SeccionRespuesta(
                    titulo="Bibliografía",
                    contenido=(
                        "No encontré evidencia suficiente sobre bibliografía en los "
                        "fragmentos consultados."
                    ),
                    formato="markdown",
                )
            )

    return RespuestaChatbot(
        tipo=tipo,
        resumen=resumen,
        secciones=secciones,
        evidencias=[
            Evidencia(
                texto=str(evidencia.get("texto", "")),
                fuente=str(evidencia.get("fuente", "")),
            )
            for evidencia in evidencias
        ],
        fuentes=fuentes,
        metadata={
            "codigo": codigo,
            "nombre": nombre,
            "formato_original": "academico",
        },
    )
