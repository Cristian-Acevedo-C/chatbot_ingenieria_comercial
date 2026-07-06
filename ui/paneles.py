"""Paneles principales de la interfaz Streamlit."""

import html

import pandas as pd
import streamlit as st

from chatbot.conversacion import limpiar_estado_conversacional
from config.settings import LOGO_UDLA, LOGO_UDLA_FINE, MENSAJES_SOCIALES, ROLES_DEMO
from services.cobertura import calcular_cobertura_documental
from services.datos import buscar_alumno, filtrar_por_alumno, listar_carreras_disponibles
from services.diagnostico import diagnosticar_assets, diagnosticar_datos
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
                <h1>Asistente Académico Multicarrera</h1>
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


def seleccionar_carrera_documental(chunks):
    """Mantiene la carrera documental activa en la clave exigida de sesión."""
    carreras = listar_carreras_disponibles(chunks)

    if st.session_state.get("carrera") not in carreras:
        st.session_state["carrera"] = carreras[0]
    anterior = st.session_state.get("_carrera_documental_activa")
    st.sidebar.markdown("#### 🏫 Selecciona tu carrera")
    carrera = st.sidebar.selectbox(
        "Carrera documental",
        carreras,
        key="carrera",
        help="La búsqueda consulta únicamente los documentos de esta carrera.",
        label_visibility="collapsed",
    )
    if anterior is not None and anterior != carrera:
        limpiar_estado_conversacional()
    st.session_state["_carrera_documental_activa"] = carrera
    return carrera


def render_panel_resumen(carrera, rol, alumno, resumen_documental, semaforo):
    """Tarjetas visuales con el estado de la sesión: carrera, perfil, alumno,
    estado académico y cobertura documental. Solo presenta cifras ya calculadas
    por ``services.resumen``; no agrega ni infiere datos nuevos."""
    st.markdown(
        '<div class="udla-resumen-titulo">Resumen de tu sesión</div>',
        unsafe_allow_html=True,
    )

    pendientes = resumen_documental["programas_pendientes"]
    if pendientes:
        doc_valor = (
            f"{resumen_documental['programas_disponibles']} de "
            f"{resumen_documental['total_programas']}"
        )
        doc_extra = f"Pendiente(s): {', '.join(pendientes)}"
    else:
        doc_valor = f"{resumen_documental['programas_disponibles']}"
        doc_extra = "Todos los programas están disponibles"

    tarjetas = [
        ("🏫", "Carrera", carrera, None, ""),
        ("🧭", "Perfil", rol, None, ""),
        ("🧑‍🎓", "Alumno demo", str(alumno["nombre"]), f"ID {alumno['id_alumno']}", ""),
        ("📊", "Estado académico", semaforo["etiqueta"], semaforo["detalle"], semaforo["nivel"]),
        ("📄", "Documentos disponibles", doc_valor, doc_extra, ""),
    ]
    columnas = st.columns(len(tarjetas))
    for columna, (icono, titulo, valor, extra, variante) in zip(columnas, tarjetas):
        clase = f"udla-card udla-card--{variante}" if variante else "udla-card"
        extra_html = (
            f'<div class="udla-card__extra">{html.escape(extra)}</div>' if extra else ""
        )
        with columna:
            st.markdown(
                f"""
                <div class="{clase}">
                    <div class="udla-card__icon">{icono}</div>
                    <div class="udla-card__titulo">{html.escape(titulo)}</div>
                    <div class="udla-card__valor">{html.escape(str(valor))}</div>
                    {extra_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        f"""
        <div class="udla-semaforo udla-semaforo--{semaforo['nivel']}">
            <span class="udla-semaforo__dot"></span>
            <span>{html.escape(semaforo['etiqueta'])}</span>
            <span class="udla-semaforo__detalle">— {html.escape(semaforo['detalle'])}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(alumnos, malla, inscritos, historial, chunks, prerrequisitos,
                   vectorizador, metricas_prerrequisitos, construir_preguntas_rapidas,
                   etiqueta_motor=None, carrera=None):
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
        st.markdown("#### 🧭 Selecciona tu perfil")
        rol = st.selectbox(
            "Vista (rol simulado)",
            ROLES_DEMO,
            help="Roles simulados para la demostración; no hay autenticación real.",
            label_visibility="collapsed",
        )
        st.markdown("#### 🧑‍🎓 Selecciona el alumno demo")
        id_alumno = st.selectbox(
            "Alumno",
            alumnos["id_alumno"].astype(str).tolist(),
            help="Los registros utilizados en este MVP son sintéticos.",
            label_visibility="collapsed",
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
        preguntas_rapidas = construir_preguntas_rapidas(ramos_alumno, carrera=carrera)
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

        with st.expander("Cobertura documental", expanded=False):
            cobertura = calcular_cobertura_documental(chunks, ramos_alumno)
            col_c1, col_c2, col_c3 = st.columns(3)
            col_c1.metric("Chunks", cobertura["total_chunks"])
            col_c2.metric("Ramos con doc.", cobertura["ramos_con_documentos"])
            col_c3.metric("Fuentes", cobertura["fuentes_distintas"])
            sin_evidencia = cobertura["ramos_inscritos_sin_evidencia"]
            if sin_evidencia:
                st.warning(
                    "Ramos inscritos sin evidencia documental: "
                    + ", ".join(item["codigo_ramo"] for item in sin_evidencia)
                )
            else:
                st.caption("Todos los ramos inscritos tienen evidencia documental.")
            if not cobertura["chunks_por_ramo"].empty:
                st.dataframe(
                    cobertura["chunks_por_ramo"].head(15),
                    width="stretch",
                    hide_index=True,
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
        "rol": rol,
        "alumno": alumno,
        "ramos": ramos_alumno,
        "historial": historial_alumno,
        "preguntas_rapidas": preguntas_rapidas,
        "opciones_ramos": opciones_ramos,
        "ramo_contexto": opciones_ramos[etiqueta_ramo],
    }


def render_vista_coordinacion(alumnos, malla, inscritos, historial, chunks,
                              prerrequisitos, metricas_prerrequisitos):
    st.info(
        "Vista **Coordinación demo** · rol simulado, solo lectura, datos sintéticos. "
        "No reemplaza sistemas oficiales de coordinación o registro académico."
    )
    st.subheader("Métricas agregadas de la demostración")
    cobertura = calcular_cobertura_documental(chunks)
    alertas = 0
    if not historial.empty and "estado" in historial.columns:
        alertas = int(
            historial["estado"].astype(str).str.lower().eq("reprobado").sum()
        )
    fila_a = st.columns(3)
    fila_a[0].metric("Alumnos disponibles", len(alumnos))
    fila_a[1].metric("Ramos en malla", len(malla))
    fila_a[2].metric("Inscripciones", len(inscritos))
    fila_b = st.columns(3)
    fila_b[0].metric("Relaciones prerrequisito", metricas_prerrequisitos["relaciones"])
    fila_b[1].metric("Alertas (reprobados)", alertas)
    fila_b[2].metric("Chunks documentales", cobertura["total_chunks"])
    st.caption("Cifras agregadas de la demostración; no representan datos reales.")
    if not cobertura["chunks_por_ramo"].empty:
        with st.expander("Cobertura documental por ramo", expanded=False):
            st.dataframe(
                cobertura["chunks_por_ramo"], width="stretch", hide_index=True
            )


def render_metricas_sistema(metricas):
    """Tarjetas con métricas reales del sistema para la carrera activa.

    Todas las cifras vienen ya calculadas por ``services.resumen``; esta
    función solo las presenta (nada se calcula ni se inventa aquí).
    """
    st.subheader("Métricas del sistema")
    tarjetas = [
        ("🏫", "Carrera", metricas["carrera"]),
        ("📄", "Documentos disponibles", metricas["documentos_disponibles"]),
        ("⏳", "Programas pendientes", metricas["programas_pendientes"]),
        ("📘", "Ramos en malla", metricas["ramos_en_malla"]),
        ("🔗", "Prerrequisitos cargados", metricas["prerrequisitos_cargados"]),
        ("🧩", "Fragmentos indexados", metricas["fragmentos_indexados"]),
        ("🧑‍🎓", "Alumnos demo", metricas["alumnos_demo"]),
        ("🗂️", "Registros de historial", metricas["registros_historial"]),
    ]
    columnas = st.columns(4)
    for indice, (icono, titulo, valor) in enumerate(tarjetas):
        with columnas[indice % 4]:
            st.markdown(
                f"""
                <div class="udla-card">
                    <div class="udla-card__icon">{icono}</div>
                    <div class="udla-card__titulo">{html.escape(titulo)}</div>
                    <div class="udla-card__valor">{html.escape(str(valor))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.caption(
        f"Última actualización de metadata: {metricas['ultima_actualizacion_metadata']} · "
        f"Motor de búsqueda: {metricas['motor_busqueda']} · Estado: {metricas['estado_general']}"
    )


def render_vista_admin(etiqueta_motor=None, metricas_sistema=None):
    st.info(
        "Vista **Admin demo** · rol simulado, solo diagnóstico. La edición y la "
        "carga de archivos no están habilitadas en la demostración."
    )
    if metricas_sistema is not None:
        render_metricas_sistema(metricas_sistema)
    st.subheader("Diagnóstico de archivos de datos")
    diagnostico = diagnosticar_datos()
    tabla = pd.DataFrame(
        [
            {
                "Archivo": item["archivo"],
                "Presente": "✅" if item["existe"] else "❌",
                "Filas": item["filas"],
                "Columnas faltantes": ", ".join(item["columnas_faltantes"]) or "—",
            }
            for item in diagnostico
        ]
    )
    st.dataframe(tabla, width="stretch", hide_index=True)

    st.subheader("Assets institucionales")
    for asset in diagnosticar_assets():
        mensaje = f"{asset['asset']}: {'encontrado' if asset['existe'] else 'no encontrado'}"
        (st.success if asset["existe"] else st.warning)(mensaje)

    st.subheader("Motor de búsqueda activo")
    st.write(etiqueta_motor or "—")


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


def render_chat(preguntas_rapidas, carrera=None):
    """Chat unificado: historial, sugerencias e input en un solo contenedor.

    Todo vive dentro de ``st.container(key="udla_chat_shell")`` para que se
    vea y se sienta como un único bloque continuo (una "carcasa" de chat),
    sin líneas divisorias ni paneles intermedios entre la respuesta, las
    fuentes, las sugerencias y la caja de texto.
    """
    for clave, valor in (
        ("historial_conversacion", []), ("ultimo_ramo_codigo", None),
        ("ultimo_ramo_nombre", None), ("ultima_intencion", None),
        ("pregunta_pendiente", None),
    ):
        st.session_state.setdefault(clave, valor)

    historial = st.session_state["historial_conversacion"]
    ultimo_indice = len(historial) - 1

    with st.container(key="udla_chat_shell"):
        st.markdown(
            '<div class="udla-chat-heading">💬 Conversa con tu asistente académico</div>',
            unsafe_allow_html=True,
        )

        with st.container(key="udla_chat_history"):
            if not historial:
                with st.chat_message("assistant", avatar="🎓"):
                    st.markdown(
                        f'<div class="udla-assistant-message udla-apertura">{MENSAJES_SOCIALES["saludo"]}</div>',
                        unsafe_allow_html=True,
                    )
            for indice, mensaje in enumerate(historial):
                render_mensaje(mensaje, indice=indice, interactivo=(indice == ultimo_indice))

        etiqueta_sugerencias = (
            f"Sugerencias para empezar en {carrera}:" if carrera else "Sugerencias para empezar:"
        )
        st.markdown(
            f'<div class="udla-suggestions-label">{etiqueta_sugerencias}</div>',
            unsafe_allow_html=True,
        )
        columnas = st.columns(3)
        for indice, pregunta in enumerate(preguntas_rapidas):
            if columnas[indice % 3].button(pregunta, key=f"rapida_{indice}", width="stretch"):
                st.session_state["pregunta_pendiente"] = pregunta

        with st.container(key="udla_chat_input_zone"):
            entrada = st.chat_input("Escribe tu consulta académica...")

    return entrada or st.session_state.pop("pregunta_pendiente", None)


def render_demo_guiada(carrera, alumno, semaforo, guion):
    """Guion de preguntas listas para mostrar el asistente a un evaluador,
    sin improvisar. Cada pregunta explica qué capacidad demuestra; el botón
    "Probar" la inserta directamente en el chat (mismo mecanismo que las
    preguntas rápidas)."""
    st.caption(
        f"Carrera activa: **{carrera}** · Alumno demo: **{alumno['nombre']}** · "
        f"Estado académico: **{semaforo['etiqueta']}**."
    )
    st.write(
        "Usa estas preguntas para presentar el asistente a un profesor o coordinación. "
        "Cada una explica qué capacidad demuestra."
    )
    for indice, (pregunta, explicacion) in enumerate(guion):
        accionable = not pregunta.startswith("(")
        col_pregunta, col_boton = st.columns([3, 1])
        with col_pregunta:
            st.markdown(f"**{pregunta}**")
            st.caption(explicacion)
        with col_boton:
            if accionable and st.button("Probar", key=f"demo_{indice}", width="stretch"):
                st.session_state["pregunta_pendiente"] = pregunta
                st.rerun()


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
