"""Renderizadores reutilizables de respuestas y mensajes."""

import pandas as pd
import streamlit as st

from chatbot.contratos import normalizar_respuesta
from chatbot.respuestas.render_contract import construir_bloques_render


def _render_payload_academico(respuesta):
    if not isinstance(respuesta, dict):
        st.markdown(respuesta)
        return
    if respuesta.get("formato") == "legacy":
        for seccion in respuesta.get("secciones", []):
            if seccion.get("tipo") == "markdown":
                st.markdown(seccion.get("contenido", ""))
        return
    if respuesta.get("formato") != "academico":
        st.markdown(str(respuesta))
        return

    st.markdown("### Respuesta breve")
    st.markdown(respuesta["resumen"])
    tipo = respuesta["tipo"]

    if tipo in {"estudio", "contenidos"}:
        titulo = "Qué estudiar" if tipo == "estudio" else "Unidades y contenidos"
        st.markdown(f"### {titulo}")
        if respuesta["contenidos"]:
            st.dataframe(
                pd.DataFrame(respuesta["contenidos"]),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No fue posible formar una tabla limpia; consulta la evidencia del PDF.")

    if tipo == "estudio":
        st.markdown("### Plan sugerido")
        if respuesta["plan"]:
            st.dataframe(
                pd.DataFrame(respuesta["plan"]),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No se propone un plan porque no se detectaron contenidos estructurados.")

        st.markdown("### Prerrequisitos académicos")
        st.caption(
            "Los prerrequisitos ayudan a identificar qué conocimientos previos conviene "
            "reforzar antes de estudiar este ramo."
        )
        if respuesta["prerrequisitos"]:
            tabla_prerrequisitos = pd.DataFrame(respuesta["prerrequisitos"])[
                [
                    "codigo_prerrequisito",
                    "nombre_prerrequisito",
                    "tipo",
                    "estado_prerrequisito",
                    "alerta",
                ]
            ].rename(
                columns={
                    "codigo_prerrequisito": "Código",
                    "nombre_prerrequisito": "Ramo previo",
                    "tipo": "Tipo",
                    "estado_prerrequisito": "Estado",
                    "alerta": "Alerta",
                }
            )
            st.dataframe(tabla_prerrequisitos, width="stretch", hide_index=True)
        else:
            st.info("No hay prerrequisitos cargados para mostrar.")

    if respuesta["bibliografia"]:
        st.markdown("### Bibliografía")
        st.dataframe(
            pd.DataFrame(respuesta["bibliografia"]),
            width="stretch",
            hide_index=True,
        )
    elif tipo == "bibliografia":
        st.info("No fue posible formar una tabla bibliográfica limpia.")

    if tipo == "evaluaciones":
        st.markdown("### Evaluaciones detectadas")
        if respuesta["evaluaciones"]:
            st.dataframe(
                pd.DataFrame(respuesta["evaluaciones"]),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No fue posible formar una tabla limpia de evaluaciones.")

    with st.expander("Ver evidencia del PDF"):
        if respuesta["evidencias"]:
            for indice, evidencia in enumerate(respuesta["evidencias"], start=1):
                st.markdown(f"**Evidencia {indice}**")
                st.write(evidencia["texto"][:500])
                st.caption(evidencia["fuente"])
        else:
            st.info("No se encontraron extractos breves para mostrar.")


def render_respuesta_academica(respuesta):
    contrato = normalizar_respuesta(respuesta)
    payload_original = contrato.metadata.get("payload_original")
    if (
        contrato.metadata.get("formato_original") == "academico"
        and isinstance(payload_original, dict)
    ):
        _render_payload_academico(payload_original)
        return

    for bloque in construir_bloques_render(contrato):
        tipo = bloque["tipo"]
        titulo = bloque["titulo"]
        contenido = bloque["contenido"]

        if tipo == "titulo":
            st.markdown(f"### {titulo}")
        elif tipo == "resumen":
            st.markdown("### Respuesta breve")
            st.markdown(contenido)
        elif tipo == "markdown":
            if titulo:
                st.markdown(f"### {titulo}")
            st.markdown(contenido or "")
        elif tipo == "tabla":
            if titulo:
                st.markdown(f"### {titulo}")
            st.dataframe(
                pd.DataFrame(contenido or []),
                width="stretch",
                hide_index=True,
            )
        elif tipo == "lista":
            if titulo:
                st.markdown(f"### {titulo}")
            for item in contenido or []:
                st.markdown(f"- {item}")
        elif tipo == "texto":
            if titulo:
                st.markdown(f"### {titulo}")
            st.write(contenido or "")
        elif tipo == "advertencia":
            st.warning(contenido)
        elif tipo == "recomendacion":
            titulo_recomendacion = contrato.metadata.get(
                "titulo_recomendacion", "Recomendación"
            )
            st.markdown(f"### {titulo_recomendacion}")
            st.markdown(contenido)
        elif tipo == "fuentes":
            st.markdown("### Fuente consultada")
            st.markdown("\n\n".join(contenido))
        elif tipo == "evidencias":
            with st.expander("Ver evidencia del PDF"):
                for indice, evidencia in enumerate(contenido, start=1):
                    st.markdown(f"**Evidencia {indice}**")
                    st.write(evidencia.texto[:500])
                    if evidencia.fuente:
                        st.caption(evidencia.fuente)


def render_mensaje(mensaje):
    rol = mensaje["rol"]
    avatar = "🎓" if rol == "assistant" else None
    with st.chat_message(rol, avatar=avatar):
        if rol == "user":
            st.markdown(mensaje["texto"])
            return
        if mensaje.get("apertura"):
            st.markdown(
                f'<div class="udla-apertura">{mensaje["apertura"]}</div>',
                unsafe_allow_html=True,
            )
        if mensaje.get("cuerpo") is not None:
            render_respuesta_academica(mensaje["cuerpo"])
        if mensaje.get("cierre"):
            st.markdown(
                f'<div class="udla-followup">{mensaje["cierre"]}</div>',
                unsafe_allow_html=True,
            )
