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
from rag.busqueda import buscar_documentos
from rag.indice import construir_indice_documental, construir_indice_tfidf
from services.datos import (
    cargar_datos,
    construir_catalogo_documental,
    filtrar_chunks_por_carrera,
    filtrar_por_carrera,
    listar_carreras_disponibles,
)
from services.prerrequisitos import (
    calcular_metricas_prerrequisitos,
    construir_prerrequisitos_alumno,
    preparar_mapa_prerrequisitos,
)
from services.resumen import (
    calcular_metricas_sistema,
    calcular_resumen_documental,
    calcular_semaforo_academico,
    construir_guion_demo,
)
from ui.estilos import aplicar_estilos
from ui.paneles import (
    render_chat,
    render_datos_expandibles,
    render_demo_guiada,
    render_encabezado,
    render_ficha_alumno,
    render_mapa_prerrequisitos,
    render_panel_resumen,
    render_prerrequisitos_alumno,
    render_sidebar,
    seleccionar_carrera_documental,
    render_vista_admin,
    render_vista_coordinacion,
)

# Import defensivo: si el módulo de configuración desplegado no expone la
# constante (p. ej. un desfase de versión en Streamlit Cloud), se usa el valor
# por defecto "auto" para no impedir el arranque. No altera la lógica del motor.
try:
    from config.settings import METODO_BUSQUEDA
except ImportError:
    METODO_BUSQUEDA = "auto"


def main():
    st.set_page_config(
        page_title="Asistente Académico Multicarrera",
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

    carrera = seleccionar_carrera_documental(chunks)
    alumnos_carrera = filtrar_por_carrera(alumnos, carrera)
    malla_carrera = filtrar_por_carrera(malla, carrera)
    inscritos_carrera = filtrar_por_carrera(inscritos, carrera)
    historial_carrera = filtrar_por_carrera(historial, carrera)
    prerrequisitos_carrera = filtrar_por_carrera(prerrequisitos, carrera)
    chunks_carrera = filtrar_chunks_por_carrera(chunks, carrera)
    malla_consulta = construir_catalogo_documental(
        malla_carrera, chunks_carrera, carrera
    )

    if alumnos_carrera.empty:
        st.error(f"No hay alumnos disponibles para la carrera {carrera}.")
        st.stop()

    if chunks_carrera.empty:
        st.warning(
            f"La base documental de {carrera} no tiene registros: la búsqueda en "
            "programas quedará deshabilitada. Revisa el comando de reconstrucción "
            "indicado en README.md."
        )

    textos_indice = tuple(chunks_carrera["texto"].fillna("").astype(str))
    metodo_indice, vectorizador, matriz_tfidf = construir_indice_documental(
        textos_indice, metodo=METODO_BUSQUEDA
    )
    etiqueta_motor = (
        "Búsqueda semántica activa"
        if metodo_indice == "embeddings"
        else "Modo compatibilidad TF-IDF"
    )
    mapa_prerrequisitos = preparar_mapa_prerrequisitos(
        prerrequisitos_carrera, malla_carrera
    )
    metricas_prerrequisitos = calcular_metricas_prerrequisitos(
        prerrequisitos_carrera
    )

    contexto = render_sidebar(
        alumnos_carrera,
        malla_carrera,
        inscritos_carrera,
        historial_carrera,
        chunks_carrera,
        prerrequisitos_carrera,
        vectorizador,
        metricas_prerrequisitos,
        construir_preguntas_rapidas,
        etiqueta_motor=etiqueta_motor,
        carrera=carrera,
    )

    rol = contexto.get("rol", "Estudiante")
    alumno = contexto["alumno"]
    ramos_alumno = contexto["ramos"]
    historial_alumno = contexto["historial"]
    prerrequisitos_alumno = construir_prerrequisitos_alumno(
        ramos_alumno, historial_alumno, prerrequisitos_carrera
    )

    resumen_documental = calcular_resumen_documental(
        carrera, chunks_carrera, malla_carrera, prerrequisitos_carrera
    )
    semaforo = calcular_semaforo_academico(historial_alumno, prerrequisitos_alumno)
    render_panel_resumen(carrera, rol, alumno, resumen_documental, semaforo)

    if rol == "Coordinación demo":
        render_vista_coordinacion(
            alumnos_carrera, malla_carrera, inscritos_carrera,
            historial_carrera, chunks_carrera,
            prerrequisitos_carrera, metricas_prerrequisitos,
        )
        return
    if rol == "Admin demo":
        metricas_sistema = calcular_metricas_sistema(
            carrera,
            alumnos_carrera,
            historial_carrera,
            chunks_carrera,
            malla_carrera,
            prerrequisitos_carrera,
            etiqueta_motor=etiqueta_motor,
        )
        render_vista_admin(etiqueta_motor, metricas_sistema)
        return

    # El chat va inmediatamente después de las tarjetas de resumen, como un
    # bloque único y continuo. Los paneles complementarios (ficha del alumno,
    # prerrequisitos, mapa curricular, datos crudos) se muestran después, para
    # no cortar el flujo de la conversación.
    consulta_usuario = render_chat(contexto["preguntas_rapidas"], carrera=carrera)

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
                prerrequisitos_carrera,
                prerrequisitos_alumno,
                malla_carrera,
                chunks_carrera,
                vectorizador,
                matriz_tfidf,
                contexto["ramo_contexto"],
                contexto["opciones_ramos"],
                carrera=carrera,
                malla_consulta=malla_consulta,
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

    st.divider()
    st.caption("Paneles complementarios (no forman parte de la conversación)")
    with st.expander("🎬 Demo guiada (modo presentación)", expanded=False):
        guion_demo = construir_guion_demo(
            carrera,
            alumno,
            chunks_carrera,
            resumen_documental,
            listar_carreras_disponibles(chunks),
        )
        render_demo_guiada(carrera, alumno, semaforo, guion_demo)
    render_ficha_alumno(alumno, ramos_alumno)
    render_prerrequisitos_alumno(prerrequisitos_carrera, prerrequisitos_alumno)
    render_mapa_prerrequisitos(
        mapa_prerrequisitos, prerrequisitos_carrera, metricas_prerrequisitos
    )
    render_datos_expandibles(historial_alumno, malla_carrera, chunks_carrera)


if __name__ == "__main__":
    main()
