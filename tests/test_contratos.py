import pandas as pd

from chatbot.contratos import (
    Evidencia,
    RespuestaChatbot,
    SeccionRespuesta,
    normalizar_respuesta,
    respuesta_desde_dict,
    respuesta_desde_markdown,
)
from chatbot.intenciones import ClasificacionConsulta
from chatbot.conversacion import elegir_apertura
from chatbot.respuestas import (
    construir_respuesta_academica,
    responder,
    respuesta_alertas,
    respuesta_documental,
    respuesta_pedir_ramo,
    respuesta_prerrequisitos_ramo,
    respuesta_ramos,
    respuesta_recomendacion,
)
from chatbot.respuestas.render_contract import construir_bloques_render


def test_normaliza_markdown_heredado():
    respuesta = respuesta_desde_markdown("### Respuesta breve\n\nTexto", "legacy")
    assert isinstance(respuesta, RespuestaChatbot)
    assert respuesta.secciones[0].formato == "markdown"
    assert respuesta.secciones[0].contenido.endswith("Texto")


def test_normaliza_diccionario_academico():
    respuesta = respuesta_desde_dict(
        {
            "formato": "academico",
            "tipo": "contenidos",
            "resumen": "Resumen",
            "contenidos": [{"Unidad": "Unidad 1"}],
            "evidencias": [{"texto": "Extracto", "fuente": "programa.pdf"}],
        }
    )
    assert respuesta.tipo == "contenidos"
    assert respuesta.resumen == "Resumen"
    assert respuesta.evidencias == [
        Evidencia(texto="Extracto", fuente="programa.pdf")
    ]
    assert respuesta.metadata["formato_original"] == "academico"


def test_normalizar_contrato_es_idempotente():
    original = RespuestaChatbot(tipo="documental", resumen="Listo")
    assert normalizar_respuesta(original) is original


def test_render_contract_incluye_tabla_evidencia_y_advertencia():
    respuesta = RespuestaChatbot(
        tipo="estudio",
        resumen="Prioriza la primera unidad.",
        secciones=[
            SeccionRespuesta(
                titulo="Qué estudiar",
                contenido=[{"Unidad": "Unidad 1", "Tema": "Oferta"}],
                formato="tabla",
            )
        ],
        evidencias=[Evidencia("Oferta y demanda", "programa.pdf")],
        advertencias=["Información orientativa."],
    )
    bloques = construir_bloques_render(respuesta)
    tipos = [bloque["tipo"] for bloque in bloques]
    assert "tabla" in tipos
    assert "evidencias" in tipos
    assert "advertencia" in tipos


def test_render_contract_legacy_conserva_markdown():
    bloques = construir_bloques_render("### Respuesta breve\n\nContenido")
    assert bloques == [
        {
            "tipo": "markdown",
            "titulo": "",
            "contenido": "### Respuesta breve\n\nContenido",
        }
    ]


def test_imports_publicos_siguen_disponibles():
    funciones = (
        construir_respuesta_academica,
        responder,
        respuesta_alertas,
        respuesta_documental,
        respuesta_pedir_ramo,
        respuesta_prerrequisitos_ramo,
        respuesta_ramos,
        respuesta_recomendacion,
    )
    assert all(callable(funcion) for funcion in funciones)


def test_orquestador_devuelve_respuesta_normalizable():
    ramos = pd.DataFrame(
        [{"codigo_ramo": "AEA100", "nombre_ramo": "Introducción", "estado": "Inscrito"}]
    )
    clasificacion = ClasificacionConsulta(
        intencion="ramos_inscritos",
        codigo_ramo=None,
        nombre_ramo=None,
        confianza="alta",
        requiere_ramo=False,
        es_seguimiento=False,
        pregunta_normalizada="que ramos tengo",
    )
    resultado = responder(
        "¿Qué ramos tengo?",
        {"nombre": "Alumno"},
        ramos,
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        None,
        None,
        clasificacion=clasificacion,
    )
    assert isinstance(resultado, RespuestaChatbot)
    assert normalizar_respuesta(resultado) is resultado


def test_apertura_conversacional_usa_configuracion_cargada():
    assert elegir_apertura()
