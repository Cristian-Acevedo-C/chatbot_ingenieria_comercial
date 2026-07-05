"""Orquestador Streamlit del Asistente Académico."""

import streamlit as st

# Reexportaciones de compatibilidad para integraciones y tests existentes.
from chatbot.conversacion import (
    construir_preguntas_rapidas,
    limpiar_estado_conversacional,
    responder_conversacional,
)
from chatbot.intenciones import (
    ClasificacionConsulta,
    clasificar_consulta,
    clasificar_intencion,
    detectar_ramo,
    detectar_tipo_pregunta,
    normalizar,
)
from chatbot.contratos import RespuestaChatbot
from chatbot.respuestas import responder
from config.settings import METODO_BUSQUEDA
from rag.busqueda import buscar_documentos
from rag.indice import construir_indice_documental, construir_indice_tfidf
from services.datos import cargar_datos
from services.prerrequisitos import (
    calcular_metricas_prerrequisitos,
    construir_prerrequisitos_alumno,
    preparar_mapa_prerrequisitos,
)
from ui.estilos import aplicar_estilos
from ui.paneles import (
    render_chat,
    render_datos_expandibles,
    render_encabezado,
    render_ficha_alumno,
    render_mapa_prerrequisitos,
    render_prerrequisitos_alumno,
    render_sidebar,
    render_vista_admin,
    render_vista_coordinacion,
)


def main():
    st.set_page_config(
        page_title="Asistente Académico | Ingeniería Comercial",
        page_icon="🎓",
        layout="wide",
    )
    aplicar_estilos()
    render_encabezado()

    try:
        alumnos, malla, inscritos, historial, chunks, prerrequisitos = cargar_datos()
    except (FileNotFoundError, ValueError) as exc:
        st.error(f"No fue posible iniciar la aplicación: {exc}")
        st.stop()
    except Exception as exc:  # noqa: BLE001 - evita stack trace crudo en la UI
        st.error(
            "Ocurrió un error inesperado al cargar los datos locales: "
            f"{exc}. Revisa la carpeta data/ e inténtalo nuevamente."
        )
        st.stop()

    if chunks.empty:
        st.warning(
            "La base documental (document_chunks.csv) no tiene registros: la "
            "búsqueda en programas quedará deshabilitada. Puedes regenerarla con "
            "`python ingest.py`."
        )

    textos_indice = tuple(chunks["texto"].fillna("").astype(str))
    metodo_indice, vectorizador, matriz_tfidf = construir_indice_documental(
        textos_indice, metodo=METODO_BUSQUEDA
    )
    etiqueta_motor = (
        "Búsqueda semántica activa"
        if metodo_indice == "embeddings"
        else "Modo compatibilidad TF-IDF"
    )
    mapa_prerrequisitos = preparar_mapa_prerrequisitos(prerrequisitos, malla)
    metricas_prerrequisitos = calcular_metricas_prerrequisitos(prerrequisitos)

    contexto = render_sidebar(
        alumnos,
        malla,
        inscritos,
        historial,
        chunks,
        prerrequisitos,
        vectorizador,
        metricas_prerrequisitos,
        construir_preguntas_rapidas,
        etiqueta_motor=etiqueta_motor,
    )

    rol = contexto.get("rol", "Estudiante")
    if rol == "Coordinación demo":
        render_vista_coordinacion(
            alumnos, malla, inscritos, historial, chunks,
            prerrequisitos, metricas_prerrequisitos,
        )
        return
    if rol == "Admin demo":
        render_vista_admin(etiqueta_motor)
        return

    alumno = contexto["alumno"]
    ramos_alumno = contexto["ramos"]
    historial_alumno = contexto["historial"]
    prerrequisitos_alumno = construir_prerrequisitos_alumno(
        ramos_alumno, historial_alumno, prerrequisitos
    )

    render_ficha_alumno(alumno, ramos_alumno)
    render_prerrequisitos_alumno(prerrequisitos, prerrequisitos_alumno)
    consulta_usuario = render_chat(contexto["preguntas_rapidas"])

    if consulta_usuario and consulta_usuario.strip():
        st.session_state["historial_conversacion"].append(
            {"rol": "user", "texto": consulta_usuario}
        )
        with st.spinner("Consultando la base local..."):
            mensaje_asistente = responder_conversacional(
                consulta_usuario,
                alumno,
                ramos_alumno,
                historial_alumno,
                prerrequisitos,
                prerrequisitos_alumno,
                malla,
                chunks,
                vectorizador,
                matriz_tfidf,
                contexto["ramo_contexto"],
                contexto["opciones_ramos"],
            )
        mensaje_asistente["rol"] = "assistant"
        st.session_state["historial_conversacion"].append(mensaje_asistente)

        st.session_state["consultas_realizadas"] = (
            st.session_state.get("consultas_realizadas", 0) + 1
        )
        cuerpo = mensaje_asistente.get("cuerpo")
        if (
            isinstance(cuerpo, RespuestaChatbot)
            and cuerpo.tipo == "documental"
            and not cuerpo.evidencias
        ):
            st.session_state["consultas_sin_evidencia"] = (
                st.session_state.get("consultas_sin_evidencia", 0) + 1
            )
        st.rerun()

    render_mapa_prerrequisitos(
        mapa_prerrequisitos, prerrequisitos, metricas_prerrequisitos
    )
    render_datos_expandibles(historial_alumno, malla, chunks)


if __name__ == "__main__":
    main()
