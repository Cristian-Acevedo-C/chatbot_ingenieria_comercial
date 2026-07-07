"""Renderizadores reutilizables de respuestas y mensajes del chat."""

import html

import pandas as pd
import streamlit as st

from chatbot.contratos import normalizar_respuesta
from chatbot.respuestas.render_contract import construir_bloques_render
from services.interacciones import actualizar_feedback


def render_fuentes_inline(fuentes):
    """Fuentes documentales como chips compactos, dentro del mismo mensaje."""
    if not fuentes:
        return
    chips = "".join(
        f'<span class="udla-source-chip">📄 {html.escape(str(fuente))}</span>'
        for fuente in fuentes
    )
    st.markdown(
        '<div class="udla-sources-label">Fuentes consultadas</div>'
        f'<div class="udla-sources-row">{chips}</div>',
        unsafe_allow_html=True,
    )


def render_evidencias_inline(evidencias):
    """Evidencia documental colapsable, asociada a la respuesta correspondiente."""
    if not evidencias:
        return
    with st.expander(f"🔎 Ver evidencia documental ({len(evidencias)})"):
        for indice, evidencia in enumerate(evidencias, start=1):
            insignias = []
            if evidencia.pagina:
                insignias.append(
                    f'<span class="udla-badge">Página {html.escape(str(evidencia.pagina))}</span>'
                )
            if evidencia.score is not None:
                insignias.append(
                    f'<span class="udla-badge">Similitud {evidencia.score:.2f}</span>'
                )
            st.markdown(
                '<div class="udla-evidencia-card udla-evidence-card">'
                '<div class="udla-evidencia-card__encabezado">'
                f'<span class="udla-evidencia-card__titulo">Evidencia {indice}</span>'
                f'<span>{" ".join(insignias)}</span>'
                "</div></div>",
                unsafe_allow_html=True,
            )
            st.write(evidencia.texto[:500])
            if evidencia.fuente:
                st.caption(f"📄 {evidencia.fuente}")


def render_acciones_sugeridas(cierre, key, interactivo=False):
    """Pregunta de seguimiento como acción de continuación del mismo mensaje.

    Solo el turno más reciente del historial es interactivo (botón real que
    reenvía la pregunta al chat); los turnos anteriores muestran el mismo
    texto sin botón, para no acumular acciones obsoletas en pantalla.
    """
    if not cierre:
        return
    if interactivo:
        if st.button(cierre, key=key, width="stretch"):
            st.session_state["pregunta_pendiente"] = cierre
    else:
        st.markdown(
            f'<div class="udla-followup-card udla-followup">{html.escape(cierre)}</div>',
            unsafe_allow_html=True,
        )


def render_respuesta_academica(respuesta):
    """Renderiza cualquier respuesta compatible desde el contrato tipado.

    Acepta ``RespuestaChatbot``, string legacy o dict legacy: todos se
    normalizan al contrato y se renderizan por bloques, sin depender de
    ``metadata['payload_original']``.
    """
    contrato = normalizar_respuesta(respuesta)
    bloques = construir_bloques_render(contrato)

    # Una respuesta conversacional simple (capa básica: saludo, agradecimiento,
    # ayuda, etc.) solo trae un bloque de resumen. Se muestra como texto de
    # chat liso, sin el encabezado "Respuesta breve" propio de las respuestas
    # académicas/documentales estructuradas.
    if len(bloques) == 1 and bloques[0]["tipo"] == "resumen":
        st.markdown(bloques[0]["contenido"])
        return

    for bloque in bloques:
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
            render_fuentes_inline(contenido)
        elif tipo == "evidencias":
            render_evidencias_inline(contenido)


def render_feedback(interaccion_id):
    """Feedback simple de utilidad bajo una respuesta del asistente.

    Enlaza con la fila exacta de ``services.interacciones`` mediante su id. Una
    vez enviado, se reemplazan los botones por un agradecimiento. Cualquier
    fallo de escritura se maneja dentro de ``actualizar_feedback`` (no lanza).
    """
    clave_dado = f"feedback_dado_{interaccion_id}"
    if st.session_state.get(clave_dado):
        st.caption("Gracias por tu feedback 🙌")
        return

    st.caption("¿Te sirvió esta respuesta?")
    comentario = st.text_input(
        "¿Qué faltó? (opcional)",
        key=f"feedback_comentario_{interaccion_id}",
        label_visibility="collapsed",
        placeholder="¿Qué faltó? (opcional)",
    )
    col_si, col_no, _ = st.columns([1, 1, 4])
    if col_si.button("👍 Sí", key=f"feedback_si_{interaccion_id}"):
        actualizar_feedback(interaccion_id, "positivo", comentario)
        st.session_state[clave_dado] = True
        st.rerun()
    if col_no.button("👎 No", key=f"feedback_no_{interaccion_id}"):
        actualizar_feedback(interaccion_id, "negativo", comentario)
        st.session_state[clave_dado] = True
        st.rerun()


def render_mensaje(mensaje, indice=0, interactivo=False):
    """Renderiza un turno del historial dentro de ``st.chat_message``.

    ``interactivo`` habilita la acción de continuación (botón) del turno más
    reciente; el resto del historial se muestra en modo lectura.
    """
    rol = mensaje["rol"]
    avatar = "🎓" if rol == "assistant" else None
    with st.chat_message(rol, avatar=avatar):
        if rol == "user":
            st.markdown(f'<div class="udla-user-message">{html.escape(mensaje["texto"])}</div>', unsafe_allow_html=True)
            return
        if mensaje.get("apertura"):
            st.markdown(
                f'<div class="udla-assistant-message udla-apertura">{mensaje["apertura"]}</div>',
                unsafe_allow_html=True,
            )
        if mensaje.get("cuerpo") is not None:
            render_respuesta_academica(mensaje["cuerpo"])
        if mensaje.get("cierre"):
            render_acciones_sugeridas(
                mensaje["cierre"], key=f"cierre_{indice}", interactivo=interactivo
            )
        if mensaje.get("interaccion_id") is not None:
            render_feedback(mensaje["interaccion_id"])
