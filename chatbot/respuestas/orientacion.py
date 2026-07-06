"""Orientación académica: prioridades, ramos críticos y qué desbloquea qué.

Cruza malla, prerrequisitos, historial y semáforo —siempre con datos ya
cargados y filtrados por carrera—. No inventa prerrequisitos, notas ni avance
oficial: cuando no hay suficiente evidencia, lo dice explícitamente. Toda
recomendación se marca como demo y sintética, separada de información oficial.
"""

import pandas as pd

from chatbot.contratos import RespuestaChatbot, SeccionRespuesta
from chatbot.respuestas.prerrequisitos import respuesta_prerrequisitos_ramo
from services.resumen import calcular_semaforo_academico

FUENTE_PRERREQUISITOS = "`data/prerrequisitos.csv`."
FUENTE_HISTORIAL_PRERREQUISITOS = "`data/prerrequisitos.csv` y `data/historial_academico.csv`."
NOTA_DEMO = (
    "Esta recomendación usa datos sintéticos y los prerrequisitos cargados en el "
    "sistema. Para decisiones oficiales, valida con coordinación académica."
)


def obtener_ramos_criticos(prerrequisitos, top=5):
    """Ramos que actúan como prerrequisito de más de un curso (cuellos de botella).

    Se basa solo en conteos reales de ``prerrequisitos.csv``; un ramo se marca
    crítico únicamente si aparece como prerrequisito de más de un curso.
    """
    columnas = ["codigo_prerrequisito", "nombre_prerrequisito", "veces_requerido"]
    if prerrequisitos is None or prerrequisitos.empty:
        return pd.DataFrame(columns=columnas)
    relaciones = prerrequisitos[prerrequisitos["tipo"] == "Prerrequisito"]
    if relaciones.empty:
        return pd.DataFrame(columns=columnas)
    conteo = (
        relaciones.groupby(["codigo_prerrequisito", "nombre_prerrequisito"])
        .size()
        .reset_index(name="veces_requerido")
        .sort_values("veces_requerido", ascending=False)
    )
    return conteo[conteo["veces_requerido"] > 1].head(top).reset_index(drop=True)


def obtener_ramos_desbloqueados(prerrequisitos, codigo_ramo):
    """Ramos que exigen ``codigo_ramo`` como prerrequisito (lo que este curso desbloquea)."""
    columnas = ["codigo_ramo", "nombre_ramo"]
    if prerrequisitos is None or prerrequisitos.empty or not codigo_ramo:
        return pd.DataFrame(columns=columnas)
    filas = prerrequisitos[
        (prerrequisitos["tipo"] == "Prerrequisito")
        & (prerrequisitos["codigo_prerrequisito"].astype(str) == str(codigo_ramo))
    ]
    return filas[columnas].drop_duplicates().reset_index(drop=True)


def recomendar_prioridades_academicas(prerrequisitos, prerrequisitos_alumno, ramos_criticos):
    """Ordena qué priorizar: primero riesgos reales del alumno, luego cuellos de botella de la malla."""
    prioridades = []
    if prerrequisitos_alumno is not None and not prerrequisitos_alumno.empty:
        riesgos = prerrequisitos_alumno[
            (prerrequisitos_alumno["tipo"] == "Prerrequisito")
            & (prerrequisitos_alumno["alerta"].isin(["Riesgo alto", "Riesgo medio"]))
        ]
        for _, fila in riesgos.iterrows():
            prioridades.append(
                {
                    "codigo": str(fila["codigo_ramo"]),
                    "nombre": str(fila["nombre_ramo"]),
                    "motivo": (
                        f"depende de {fila['codigo_prerrequisito']} "
                        f"({fila['estado_prerrequisito']}; {fila['alerta']})"
                    ),
                }
            )
    if ramos_criticos is not None and not ramos_criticos.empty:
        for _, fila in ramos_criticos.iterrows():
            prioridades.append(
                {
                    "codigo": str(fila["codigo_prerrequisito"]),
                    "nombre": str(fila["nombre_prerrequisito"]),
                    "motivo": f"es prerrequisito de {int(fila['veces_requerido'])} ramo(s) posteriores",
                }
            )

    vistos = set()
    unicos = []
    for item in prioridades:
        if item["codigo"] in vistos:
            continue
        vistos.add(item["codigo"])
        unicos.append(item)
    return unicos


def _respuesta_semaforo_alumno(alumno, historial, prerrequisitos_alumno):
    semaforo = calcular_semaforo_academico(historial, prerrequisitos_alumno)
    nombre_alumno = alumno["nombre"] if alumno is not None else None
    quien = f"de **{nombre_alumno}**" if nombre_alumno else "del alumno seleccionado"
    resumen = (
        f"El semáforo académico {quien} está en **{semaforo['etiqueta']}**. {semaforo['detalle']}"
    )
    return RespuestaChatbot(
        tipo="orientacion_academica",
        resumen=resumen,
        secciones=[
            SeccionRespuesta(
                titulo="Cómo se calcula (regla demo)",
                contenido=(
                    "- **Verde**: avance normal, sin reprobaciones ni alertas de prerrequisitos.\n"
                    "- **Amarillo**: un ramo reprobado o un prerrequisito en riesgo medio.\n"
                    "- **Rojo**: dos o más ramos reprobados, o un prerrequisito en riesgo alto.\n\n"
                    "Se calcula únicamente con `historial_academico.csv` y las relaciones de "
                    "`prerrequisitos.csv`; no reemplaza una evaluación oficial de coordinación."
                ),
                formato="markdown",
            )
        ],
        recomendacion=NOTA_DEMO,
        fuentes=[FUENTE_HISTORIAL_PRERREQUISITOS],
    )


def _respuesta_antes_de_tomar(prerrequisitos, codigo_ramo, nombre_ramo, historial):
    """Qué requiere ESTE ramo (dirección "hacia atrás"): reutiliza la respuesta
    de prerrequisitos ya existente y probada, en vez de duplicar su lógica."""
    if not codigo_ramo:
        return RespuestaChatbot(
            tipo="orientacion_academica",
            resumen=(
                "Indícame el código o el nombre del ramo que quieres tomar para revisar qué "
                "prerrequisito conviene repasar antes."
            ),
            recomendacion="Por ejemplo: «¿qué debería estudiar antes de tomar EIN970?».",
            fuentes=[FUENTE_PRERREQUISITOS],
        )
    return respuesta_prerrequisitos_ramo(prerrequisitos, codigo_ramo, nombre_ramo, historial)


def _respuesta_impacto_ramo(prerrequisitos, codigo_ramo, nombre_ramo):
    """Qué desbloquea ESTE ramo (dirección "hacia adelante"): ramos posteriores
    que lo exigen como prerrequisito."""
    if not codigo_ramo:
        return RespuestaChatbot(
            tipo="orientacion_academica",
            resumen="Indícame el código o el nombre del ramo para revisar qué desbloquea.",
            recomendacion="Por ejemplo: «¿qué ramos desbloquea EIN971?».",
            fuentes=[FUENTE_PRERREQUISITOS],
        )

    desbloqueados = obtener_ramos_desbloqueados(prerrequisitos, codigo_ramo)
    identificador = f"**{codigo_ramo} — {nombre_ramo}**" if nombre_ramo else f"**{codigo_ramo}**"
    if desbloqueados.empty:
        resumen = (
            f"No encontré ramos que registren a {identificador} como prerrequisito en los "
            "datos cargados."
        )
        secciones = []
    else:
        resumen = (
            f"{identificador} es prerrequisito de **{len(desbloqueados)} ramo(s)** según los "
            "datos cargados."
        )
        secciones = [
            SeccionRespuesta(
                titulo="Ramos que dependen de este curso",
                contenido=desbloqueados.rename(
                    columns={"codigo_ramo": "Código", "nombre_ramo": "Ramo"}
                ).to_dict("records"),
                formato="tabla",
            )
        ]
    return RespuestaChatbot(
        tipo="orientacion_academica",
        resumen=resumen,
        secciones=secciones,
        recomendacion=NOTA_DEMO,
        fuentes=[FUENTE_PRERREQUISITOS],
    )


def _respuesta_prioridades(prerrequisitos, prerrequisitos_alumno, alumno):
    criticos = obtener_ramos_criticos(prerrequisitos)
    prioridades = recomendar_prioridades_academicas(prerrequisitos, prerrequisitos_alumno, criticos)
    nombre_alumno = alumno["nombre"] if alumno is not None else None

    if not prioridades:
        return RespuestaChatbot(
            tipo="orientacion_academica",
            resumen=(
                "No encontré señales de riesgo ni ramos críticos en los datos cargados para "
                "sugerir una prioridad distinta a tu plan actual."
            ),
            recomendacion=NOTA_DEMO,
            fuentes=[FUENTE_HISTORIAL_PRERREQUISITOS],
        )

    quien = f"Para **{nombre_alumno}**" if nombre_alumno else "Para este perfil"
    resumen = (
        f"{quien}, la recomendación demo es priorizar los ramos que funcionan como "
        "prerrequisito de cursos posteriores o que muestran alertas pendientes en tu historial."
    )
    return RespuestaChatbot(
        tipo="orientacion_academica",
        resumen=resumen,
        secciones=[
            SeccionRespuesta(
                titulo="Prioridades sugeridas",
                contenido=[
                    {"Código": item["codigo"], "Ramo": item["nombre"], "Motivo": item["motivo"]}
                    for item in prioridades[:5]
                ],
                formato="tabla",
            )
        ],
        recomendacion=NOTA_DEMO,
        fuentes=[FUENTE_HISTORIAL_PRERREQUISITOS],
    )


def responder_orientacion_academica(
    pregunta_normalizada,
    alumno,
    historial,
    prerrequisitos,
    prerrequisitos_alumno,
    codigo_ramo=None,
    nombre_ramo=None,
):
    """Enruta la consulta de orientación al sub-caso adecuado.

    ``pregunta_normalizada`` ya viene sin tildes/mayúsculas (ver
    ``chatbot.intenciones.normalizar_intencion``).
    """
    if "semaforo" in pregunta_normalizada:
        return _respuesta_semaforo_alumno(alumno, historial, prerrequisitos_alumno)

    if "antes de tomar" in pregunta_normalizada:
        return _respuesta_antes_de_tomar(prerrequisitos, codigo_ramo, nombre_ramo, historial)

    if any(clave in pregunta_normalizada for clave in ("desbloquea", "repruebo")):
        return _respuesta_impacto_ramo(prerrequisitos, codigo_ramo, nombre_ramo)

    return _respuesta_prioridades(prerrequisitos, prerrequisitos_alumno, alumno)
