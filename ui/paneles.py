"""Paneles principales de la interfaz Streamlit."""

import streamlit as st

from chatbot.conversacion import limpiar_estado_conversacional
from config.settings import LOGO_UDLA, LOGO_UDLA_FINE, MENSAJES_SOCIALES
from services.datos import buscar_alumno, filtrar_por_alumno
from ui.componentes import render_mensaje


def render_encabezado():
    col_logo, col_encabezado = st.columns([1, 3.2], vertical_alignment="center")
    with col_logo:
        with st.container(border=True):
            if LOGO_UDLA.exists():
                st.image(str(LOGO_UDLA), width="stretch")
            else:
                st.markdown("**Universidad de Las Américas**")
    with col_encabezado:
        st.markdown(
            """
            <section class="udla-hero">
                <div class="udla-hero__eyebrow">Facultad de Ingeniería y Negocios</div>
                <h1>Asistente Académico de Ingeniería Comercial</h1>
                <p>
                    Consulta antecedentes académicos sintéticos y encuentra evidencia en programas
                    de asignatura mediante búsqueda documental local con TF-IDF.
                </p>
            </section>
            """,
            unsafe_allow_html=True,
        )
    st.info(
        "Este asistente es un prototipo académico con datos sintéticos o locales. "
        "Sus respuestas son orientativas y no reemplazan la información oficial de "
        "Registro Académico, coordinación de carrera o reglamentos institucionales."
    )


def render_sidebar(alumnos, malla, inscritos, historial, chunks, prerrequisitos,
                   vectorizador, metricas_prerrequisitos, construir_preguntas_rapidas,
                   etiqueta_motor=None):
    with st.sidebar:
        if LOGO_UDLA_FINE.exists():
            st.image(str(LOGO_UDLA_FINE), width="stretch")
        else:
            st.markdown("### Facultad de Ingeniería y Negocios")
        st.header("Panel académico")
        st.caption(
            "🎓 Modo demostración · Datos sintéticos/locales · "
            "No reemplaza información oficial"
        )
        id_alumno = st.selectbox(
            "Alumno",
            alumnos["id_alumno"].astype(str).tolist(),
            help="Los registros utilizados en este MVP son sintéticos.",
        )
        anterior = st.session_state.get("id_alumno_activo")
        if anterior is not None and str(anterior) != str(id_alumno):
            limpiar_estado_conversacional()
        st.session_state["id_alumno_activo"] = str(id_alumno)

        alumno = buscar_alumno(alumnos, id_alumno)
        if alumno is None:
            st.error("El alumno seleccionado no existe en la base.")
            st.stop()
        ramos_alumno = filtrar_por_alumno(inscritos, id_alumno)
        historial_alumno = filtrar_por_alumno(historial, id_alumno)
        preguntas_rapidas = construir_preguntas_rapidas(ramos_alumno)
        opciones_ramos = {"Todos los ramos": None}
        for _, fila in ramos_alumno.iterrows():
            etiqueta = f"{fila['codigo_ramo']} — {fila['nombre_ramo']}"
            opciones_ramos[etiqueta] = {
                "codigo_ramo": str(fila["codigo_ramo"]),
                "nombre_ramo": str(fila["nombre_ramo"]),
            }
        etiqueta_ramo = st.selectbox(
            "Ramo inscrito (opcional)",
            list(opciones_ramos),
            help="Se usa como contexto si la pregunta no menciona un ramo.",
        )

        st.divider()
        st.subheader("Estado de la base")
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Alumnos", len(alumnos))
        col_m2.metric("Ramos", len(malla))
        st.metric("Fragmentos documentales", len(chunks))
        if vectorizador is not None:
            st.success(etiqueta_motor or "Índice documental disponible")
        else:
            st.warning("Índice documental no disponible")
        if prerrequisitos.empty:
            st.info("No hay prerrequisitos cargados")
        else:
            st.success(
                f"Prerrequisitos disponibles: {metricas_prerrequisitos['relaciones']} relaciones"
            )
        st.divider()
        st.subheader("Conversación")
        if st.button("Reiniciar conversación", key="reiniciar_conversacion", width="stretch"):
            limpiar_estado_conversacional()
            st.success("Conversación reiniciada. Puedes comenzar una nueva consulta.")

        with st.expander("Estado de la sesión", expanded=False):
            st.caption("Métricas locales de esta sesión (no se guardan).")
            st.write(
                f"**Consultas realizadas:** "
                f"{st.session_state.get('consultas_realizadas', 0)}"
            )
            st.write(
                f"**Última intención:** "
                f"{st.session_state.get('ultima_intencion') or '—'}"
            )
            st.write(
                f"**Último ramo consultado:** "
                f"{st.session_state.get('ultimo_ramo_nombre') or '—'}"
            )
            st.write(f"**Motor de búsqueda:** {etiqueta_motor or '—'}")
            st.write(
                f"**Consultas sin evidencia:** "
                f"{st.session_state.get('consultas_sin_evidencia', 0)}"
            )

    return {
        "alumno": alumno,
        "ramos": ramos_alumno,
        "historial": historial_alumno,
        "preguntas_rapidas": preguntas_rapidas,
        "opciones_ramos": opciones_ramos,
        "ramo_contexto": opciones_ramos[etiqueta_ramo],
    }


def render_ficha_alumno(alumno, ramos_alumno):
    col_datos, col_ramos = st.columns([1, 1.4])
    with col_datos:
        with st.container(border=True):
            st.subheader("Ficha del alumno")
            st.write(f"**Nombre:** {alumno['nombre']}")
            st.write(f"**Carrera:** {alumno['carrera']}")
            st.write(f"**Sede y jornada:** {alumno['sede']} · {alumno['jornada']}")
            st.write(f"**Semestre actual:** {alumno['semestre_actual']}")
    with col_ramos:
        with st.container(border=True):
            st.subheader("Ramos inscritos")
            if ramos_alumno.empty:
                st.info("No hay ramos inscritos para este alumno.")
            else:
                st.dataframe(
                    ramos_alumno[["codigo_ramo", "nombre_ramo", "estado"]],
                    width="stretch",
                    hide_index=True,
                )


def render_prerrequisitos_alumno(prerrequisitos, vista):
    st.subheader("Prerrequisitos del alumno")
    with st.container(border=True):
        if prerrequisitos.empty:
            st.info("No hay prerrequisitos cargados")
        elif vista.empty:
            st.info("No hay ramos inscritos o relaciones disponibles para este alumno.")
        else:
            columnas = {
                "codigo_ramo": "Código ramo", "nombre_ramo": "Ramo inscrito",
                "codigo_prerrequisito": "Código prerrequisito",
                "nombre_prerrequisito": "Prerrequisito", "tipo": "Tipo",
                "estado_prerrequisito": "Estado", "alerta": "Alerta",
            }
            st.dataframe(vista[list(columnas)].rename(columns=columnas), width="stretch", hide_index=True)
            st.caption(
                "Los estados se calculan únicamente con historial_academico.csv y las "
                "relaciones presentes en prerrequisitos.csv."
            )


def render_chat(preguntas_rapidas):
    st.divider()
    st.subheader("Conversa con tu asistente académico")
    for clave, valor in (
        ("historial_conversacion", []), ("ultimo_ramo_codigo", None),
        ("ultimo_ramo_nombre", None), ("ultima_intencion", None),
        ("pregunta_pendiente", None),
    ):
        st.session_state.setdefault(clave, valor)

    st.caption("Sugerencias para empezar:")
    columnas = st.columns(3)
    for indice, pregunta in enumerate(preguntas_rapidas):
        if columnas[indice % 3].button(pregunta, key=f"rapida_{indice}", width="stretch"):
            st.session_state["pregunta_pendiente"] = pregunta
    if not st.session_state["historial_conversacion"]:
        with st.chat_message("assistant", avatar="🎓"):
            st.markdown(
                f'<div class="udla-apertura">{MENSAJES_SOCIALES["saludo"]}</div>',
                unsafe_allow_html=True,
            )
    for mensaje in st.session_state["historial_conversacion"]:
        render_mensaje(mensaje)
    entrada = st.chat_input("Escribe tu consulta académica...")
    return entrada or st.session_state.pop("pregunta_pendiente", None)


def render_mapa_prerrequisitos(mapa, prerrequisitos, metricas):
    st.divider()
    with st.expander("Mapa de prerrequisitos", expanded=False):
        if prerrequisitos.empty:
            st.info("No hay prerrequisitos cargados")
            return
        cols = st.columns(5)
        for col, etiqueta, clave in zip(cols,
            ("Ramos analizados", "Con prerrequisito", "Sin prerrequisito", "No detectados", "Relaciones"),
            ("analizados", "con_prerrequisito", "sin_prerrequisito", "no_detectados", "relaciones")):
            col.metric(etiqueta, metricas[clave])
        filtro_semestre, filtro_ramo, filtro_tipo = st.columns(3)
        semestres = sorted(mapa["semestre"].dropna().astype(int).unique().tolist())
        semestre = filtro_semestre.selectbox("Semestre del ramo", ["Todos", *semestres], key="filtro_prerrequisitos_semestre")
        etiquetas = {"Todos": None, **{
            f"{fila['codigo_ramo']} — {fila['nombre_ramo']}": str(fila["codigo_ramo"])
            for _, fila in mapa.drop_duplicates("codigo_ramo").iterrows()
        }}
        ramo = filtro_ramo.selectbox("Ramo", list(etiquetas), key="filtro_prerrequisitos_ramo")
        tipo = filtro_tipo.selectbox("Tipo", ["Todos", "Prerrequisito", "Sin prerrequisito", "No detectado"], key="filtro_prerrequisitos_tipo")
        filtrado = mapa.copy()
        if semestre != "Todos":
            filtrado = filtrado[filtrado["semestre"].fillna(-1).astype(int) == semestre]
        if etiquetas[ramo]:
            filtrado = filtrado[filtrado["codigo_ramo"].astype(str) == etiquetas[ramo]]
        if tipo != "Todos":
            filtrado = filtrado[filtrado["tipo"] == tipo]
        columnas = ["semestre", "codigo_ramo", "nombre_ramo", "codigo_prerrequisito",
                    "nombre_prerrequisito", "tipo", "confianza", "fuente_archivo"]
        nombres = {"semestre": "Semestre", "codigo_ramo": "Código ramo", "nombre_ramo": "Ramo",
                   "codigo_prerrequisito": "Código prerrequisito", "nombre_prerrequisito": "Prerrequisito",
                   "tipo": "Tipo", "confianza": "Confianza", "fuente_archivo": "Fuente",
                   "evidencia_textual": "Evidencia textual"}
        if st.checkbox("Mostrar evidencia textual", value=False, key="mostrar_evidencia_prerrequisitos"):
            columnas.append("evidencia_textual")
        st.dataframe(filtrado[columnas].rename(columns=nombres), width="stretch", hide_index=True)
        st.caption(f"Filas mostradas: {len(filtrado)}")


def render_datos_expandibles(historial_alumno, malla, chunks):
    with st.expander("Ver historial académico sintético"):
        st.dataframe(historial_alumno, width="stretch", hide_index=True)
    with st.expander("Ver malla curricular"):
        st.dataframe(malla, width="stretch", hide_index=True)
    with st.expander("Ver muestra de la base documental"):
        columnas = [c for c in ("chunk_id", "codigo_ramo", "nombre_ramo", "fuente_legible", "ruta_archivo") if c in chunks.columns]
        st.dataframe(chunks[columnas].head(20), width="stretch", hide_index=True)
