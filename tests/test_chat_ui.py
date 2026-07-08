"""Pruebas de UI del chat unificado usando streamlit.testing.v1.AppTest.

No hay navegador disponible en este entorno de CI, así que estas pruebas
ejercitan el motor real de Streamlit (sin renderizar píxeles) para verificar
que el chat se arma como un único flujo: historial, fuentes y evidencia
quedan dentro del mismo mensaje del asistente, y el input no se separa de la
conversación por paneles intermedios.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _iniciar():
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception
    return at


def _seleccionar_carrera(at, carrera):
    at.sidebar.selectbox(key="carrera").set_value(carrera).run()
    assert not at.exception
    return at


def test_chat_renderiza_sin_excepciones():
    at = _iniciar()
    assert not at.exception
    assert len(at.chat_input) == 1
    assert len(at.chat_message) == 1  # saludo inicial


def test_chat_renderiza_sin_excepciones_para_ambas_carreras():
    for carrera in ("Ingeniería Comercial", "Ingeniería Civil Industrial"):
        at = _iniciar()
        _seleccionar_carrera(at, carrera)
        assert not at.exception


def test_input_no_queda_separado_por_paneles_intermedios():
    """El chat_input debe ir antes de cualquier panel complementario (tablas/expanders)."""
    at = _iniciar()
    nodos = list(at.main)
    indice_input = next(i for i, n in enumerate(nodos) if n.type == "chat_input")
    indices_paneles = [
        i for i, n in enumerate(nodos) if n.type in ("dataframe", "expander")
    ]
    assert indices_paneles, "se esperaban paneles complementarios (ficha, mapa, datos)"
    assert indice_input < min(indices_paneles), (
        "el chat_input debe renderizarse antes que los paneles complementarios, "
        "no intercalado entre ellos"
    )
    indice_ultimo_chat_message = max(
        i for i, n in enumerate(nodos) if n.type == "chat_message"
    )
    assert not any(
        indice_ultimo_chat_message < i < indice_input for i in indices_paneles
    ), "no debe haber tablas/expanders entre el último mensaje y el input"


def test_fuentes_se_renderizan_dentro_del_mensaje_del_chat():
    at = _iniciar()
    _seleccionar_carrera(at, "Ingeniería Civil Industrial")
    at.chat_input[0].set_value("qué contenidos tiene EIN908").run()
    assert not at.exception

    ultimo = at.chat_message[-1]
    contenido = "\n".join(md.value for md in ultimo.markdown)
    assert "udla-source-chip" in contenido
    assert "udla-sources-row" in contenido


def test_evidencias_se_renderizan_como_expander_de_la_respuesta():
    at = _iniciar()
    _seleccionar_carrera(at, "Ingeniería Civil Industrial")
    at.chat_input[0].set_value("qué contenidos tiene EIN908").run()
    assert not at.exception

    ultimo = at.chat_message[-1]
    etiquetas = [expander.label for expander in ultimo.expander]
    assert any("Ver evidencia documental" in etiqueta for etiqueta in etiquetas)


def test_carrera_en_session_state_filtra_la_busqueda_documental():
    at = _iniciar()
    assert at.session_state["carrera"] == "Ingeniería Comercial"
    _seleccionar_carrera(at, "Ingeniería Civil Industrial")
    assert at.session_state["carrera"] == "Ingeniería Civil Industrial"


def test_comercial_no_ve_documentos_de_ici():
    """EIN908 es exclusivo de ICI: en Comercial no debe reconocerse ni citarse."""
    at = _iniciar()
    assert at.session_state["carrera"] == "Ingeniería Comercial"
    at.chat_input[0].set_value("qué contenidos tiene EIN908").run()
    assert not at.exception

    ultimo = at.chat_message[-1]
    assert not ultimo.expander
    contenido = "\n".join(md.value for md in ultimo.markdown)
    # Sin malla ni chunks para EIN908 en Comercial, el clasificador no detecta
    # el ramo y pide precisarlo; no debe citarse ningún PDF de programa.
    assert "EIN908" not in contenido.upper()
    assert ".pdf" not in contenido.lower()
    assert "¿Sobre qué ramo quieres que revise esa información?" in contenido


def test_fis504_no_inventa_informacion():
    """FIS504 (ICI) está pendiente: nunca debe fabricarse evidencia para él."""
    at = _iniciar()
    _seleccionar_carrera(at, "Ingeniería Civil Industrial")
    at.chat_input[0].set_value("qué contenidos tiene FIS504").run()
    assert not at.exception

    ultimo = at.chat_message[-1]
    assert not ultimo.expander
    contenido = "\n".join(md.value for md in ultimo.markdown)
    assert "udla-source-chip" not in contenido
    assert "No encontré evidencia suficiente" in contenido
    assert "FIS504" in contenido
    assert "pendiente" in contenido.lower()


def test_saludo_responde_de_inmediato_sin_evidencia():
    at = _iniciar()
    _seleccionar_carrera(at, "Ingeniería Civil Industrial")
    at.chat_input[0].set_value("hola como estas").run()
    assert not at.exception

    ultimo = at.chat_message[-1]
    contenido = "\n".join(md.value for md in ultimo.markdown)
    assert "Todo bien por acá" in contenido
    assert not ultimo.expander
    assert "udla-source-chip" not in contenido


def test_chips_explorar_por_categoria_presentes_y_funcionan():
    at = _iniciar()
    _seleccionar_carrera(at, "Ingeniería Civil Industrial")
    etiquetas = [b.label for b in at.button]
    assert "Soy estudiante nuevo" in etiquetas
    assert "Diferencia entre carreras" in etiquetas
    assert "Apoyo y bienestar" in etiquetas
    assert "Tramites y certificados" in etiquetas
    assert "¿Cuándo consultar con coordinación?" in etiquetas

    boton = next(b for b in at.button if b.label == "Soy estudiante nuevo")
    boton.click().run()
    assert not at.exception

    ultimo = at.chat_message[-1]
    contenido = "\n".join(md.value for md in ultimo.markdown)
    assert "estudiante" in contenido.lower() or "bienvenido" in contenido.lower()


def test_pregunta_rara_no_rompe_y_usa_fallback_responsable():
    at = _iniciar()
    _seleccionar_carrera(at, "Ingeniería Civil Industrial")
    at.chat_input[0].set_value("asdf qwerty zxcvb lorem ipsum").run()
    assert not at.exception

    ultimo = at.chat_message[-1]
    contenido = "\n".join(md.value for md in ultimo.markdown)
    assert "No tengo información validada" in contenido
    assert "coordinación" in contenido.lower()


def test_nota_demo_visible_junto_al_input():
    at = _iniciar()
    captions = [c.value for c in at.caption]
    assert any("Demo académico en desarrollo" in texto for texto in captions)


def _cambiar_rol(at, rol):
    for selectbox in at.sidebar.selectbox:
        if selectbox.label == "Vista (rol simulado)":
            selectbox.set_value(rol).run()
            return
    raise AssertionError("No se encontró el selector de rol en la barra lateral")


def test_demo_guiada_renderiza_sin_excepciones_y_tiene_preguntas_accionables():
    at = _iniciar()
    _seleccionar_carrera(at, "Ingeniería Civil Industrial")
    demo = next(e for e in at.expander if "Demo guiada" in e.label)
    assert not at.exception
    assert len(demo.button) >= 5
    preguntas = [md.value for md in demo.markdown if md.value.startswith("**")]
    assert any("hola" in pregunta.lower() for pregunta in preguntas)
    assert any("FIS504" in pregunta for pregunta in preguntas)


def test_demo_guiada_boton_inserta_la_pregunta_en_el_chat():
    at = _iniciar()
    _seleccionar_carrera(at, "Ingeniería Civil Industrial")
    demo = next(e for e in at.expander if "Demo guiada" in e.label)
    demo.button[0].click().run()
    assert not at.exception
    # El primer botón corresponde a "hola cómo estás": debe generar un turno de chat.
    assert len(at.chat_message) >= 2


def test_demo_guiada_no_aparece_ni_rompe_vista_coordinacion():
    at = _iniciar()
    _seleccionar_carrera(at, "Ingeniería Civil Industrial")
    _cambiar_rol(at, "Coordinación demo")
    assert not at.exception
    assert not [e for e in at.expander if "Demo guiada" in e.label]


def test_demo_guiada_no_aparece_ni_rompe_vista_admin():
    at = _iniciar()
    _seleccionar_carrera(at, "Ingeniería Civil Industrial")
    _cambiar_rol(at, "Admin demo")
    assert not at.exception
    assert not [e for e in at.expander if "Demo guiada" in e.label]


def test_metricas_sistema_se_muestran_en_admin_demo():
    at = _iniciar()
    _seleccionar_carrera(at, "Ingeniería Civil Industrial")
    _cambiar_rol(at, "Admin demo")
    assert not at.exception
    assert any(sub.value == "Métricas del sistema" for sub in at.subheader)
    assert any("Documentos disponibles" in md.value for md in at.markdown)
    assert any("Ramos en malla" in md.value for md in at.markdown)
    assert any("51" in md.value for md in at.markdown if "Documentos disponibles" in md.value)


def test_nota_privacidad_visible_junto_al_input():
    at = _iniciar()
    captions = [c.value for c in at.caption]
    assert any("No ingreses datos personales sensibles" in texto for texto in captions)


def test_feedback_aparece_tras_una_respuesta():
    at = _iniciar()
    _seleccionar_carrera(at, "Ingeniería Civil Industrial")
    at.chat_input[0].set_value("hola como estas").run()
    assert not at.exception

    ultimo = at.chat_message[-1]
    etiquetas = [b.label for b in ultimo.button]
    assert "👍 Sí" in etiquetas
    assert "👎 No" in etiquetas


def test_feedback_positivo_se_registra_y_agradece():
    at = _iniciar()
    _seleccionar_carrera(at, "Ingeniería Civil Industrial")
    at.chat_input[0].set_value("hola como estas").run()

    boton_si = next(b for b in at.chat_message[-1].button if b.label == "👍 Sí")
    boton_si.click().run()
    assert not at.exception

    contenido = "\n".join(c.value for c in at.chat_message[-1].caption)
    assert "Gracias por tu feedback" in contenido


def test_panel_interacciones_visible_en_coordinacion_demo():
    at = _iniciar()
    _seleccionar_carrera(at, "Ingeniería Civil Industrial")
    # Genera una interacción antes de cambiar de vista.
    at.chat_input[0].set_value("hola como estas").run()
    _cambiar_rol(at, "Coordinación demo")
    assert not at.exception
    assert any(
        sub.value == "Registro de interacciones (demo)" for sub in at.subheader
    )
    etiquetas_metrica = [m.label for m in at.metric]
    assert "Total interacciones" in etiquetas_metrica
    total = next(m for m in at.metric if m.label == "Total interacciones")
    assert int(total.value) >= 1
