"""Renderizadores reutilizables de respuestas y mensajes."""

import pandas as pd
import streamlit as st

from chatbot.contratos import normalizar_respuesta
from chatbot.respuestas.render_contract import construir_bloques_render


def render_respuesta_academica(respuesta):
    """Renderiza cualquier respuesta compatible desde el contrato tipado.

    Acepta ``RespuestaChatbot``, string legacy o dict legacy: todos se
    normalizan al contrato y se renderizan por bloques, sin depender de
    ``metadata['payload_original']``.
    """
    contrato = normalizar_respuesta(respuesta)

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
