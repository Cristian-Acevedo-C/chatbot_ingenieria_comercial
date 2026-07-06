"""Capa conversacional básica: saludos, ayuda, identidad; nunca RAG/académico."""

import pytest

from chatbot.contratos import RespuestaChatbot
from chatbot.respuestas.basicas import (
    cargar_respuestas_basicas,
    es_consulta_academica_o_documental,
    responder_basica,
)

CONTEXTO_DEMO = {
    "carrera": "Ingeniería Civil Industrial",
    "carreras_disponibles": ["Ingeniería Comercial", "Ingeniería Civil Industrial"],
    "perfiles_disponibles": ["Estudiante", "Coordinación demo", "Admin demo"],
}


@pytest.mark.parametrize(
    ("mensaje", "tipo_esperado"),
    [
        ("hola", "saludo"),
        ("hola como estas", "saludo"),
        ("buenas tardes", "saludo"),
        ("gracias", "agradecimiento"),
        ("muchas gracias", "agradecimiento"),
        ("ayuda", "ayuda"),
        ("no se que preguntar", "ayuda"),
        ("quien eres", "identidad"),
        ("que puedes hacer", "capacidades"),
        ("que carreras tienes", "carreras_disponibles"),
        ("que perfiles hay", "perfiles_disponibles"),
        ("que significa el semaforo", "semaforo_explicacion"),
    ],
)
def test_responde_desde_capa_basica(mensaje, tipo_esperado):
    respuesta = responder_basica(mensaje, contexto=CONTEXTO_DEMO)
    assert isinstance(respuesta, RespuestaChatbot)
    assert respuesta.tipo == tipo_esperado
    assert respuesta.resumen


def test_saludo_usa_carrera_del_contexto():
    respuesta = responder_basica("hola", contexto=CONTEXTO_DEMO)
    assert "Ingeniería Civil Industrial" in respuesta.resumen


def test_carreras_disponibles_no_hardcodea_lista():
    """La respuesta debe reflejar el contexto recibido, no un texto fijo."""
    contexto_una_carrera = {**CONTEXTO_DEMO, "carreras_disponibles": ["Ingeniería Comercial"]}
    respuesta = responder_basica("que carreras tienes", contexto=contexto_una_carrera)
    assert "Ingeniería Comercial" in respuesta.resumen
    assert "Ingeniería Civil Industrial" not in respuesta.resumen


def test_perfiles_disponibles_usa_lista_del_contexto():
    contexto_perfiles = {**CONTEXTO_DEMO, "perfiles_disponibles": ["Solo Rol Demo"]}
    respuesta = responder_basica("que perfiles hay", contexto=contexto_perfiles)
    assert "Solo Rol Demo" in respuesta.resumen


@pytest.mark.parametrize(
    "mensaje",
    [
        "que contenidos tiene EIN908",
        "que contenidos tiene ein908",
        "EIN908",
        "que bibliografia tiene AEA315",
    ],
)
def test_pregunta_documental_retorna_none(mensaje):
    assert responder_basica(mensaje, contexto=CONTEXTO_DEMO) is None


@pytest.mark.parametrize(
    "mensaje",
    [
        "que avance tiene Martín Sepúlveda",
        "que avance tiene martin sepulveda",
        "tengo alguna alerta academica",
        "cuales son mis prerrequisitos pendientes",
    ],
)
def test_pregunta_academica_retorna_none(mensaje):
    assert responder_basica(mensaje, contexto=CONTEXTO_DEMO) is None


def test_mensaje_vacio_retorna_none():
    assert responder_basica("", contexto=CONTEXTO_DEMO) is None
    assert responder_basica("   ", contexto=CONTEXTO_DEMO) is None


def test_es_consulta_academica_detecta_codigo_de_ramo_sin_palabra_clave():
    assert es_consulta_academica_o_documental("FIS504")
    assert not es_consulta_academica_o_documental("hola como estas")


def test_csv_filas_marcadas_pasar_a_rag_nunca_responden():
    """Las filas negativas del CSV documentan ejemplos que deben ir al RAG."""
    tabla = cargar_respuestas_basicas()
    negativas = tabla[tabla["pasar_a_rag"].astype(str).str.lower().eq("si")]
    assert not negativas.empty
    for _, fila in negativas.iterrows():
        for ejemplo in str(fila["ejemplos_usuario"]).split("|"):
            assert responder_basica(ejemplo, contexto=CONTEXTO_DEMO) is None


def test_cargar_respuestas_basicas_devuelve_columnas_esperadas():
    tabla = cargar_respuestas_basicas()
    assert not tabla.empty
    assert {
        "intencion", "ejemplos_usuario", "respuesta",
        "prioridad", "usar_carrera", "pasar_a_rag",
    }.issubset(tabla.columns)


def test_ruta_csv_inexistente_devuelve_vacio_sin_romper(tmp_path):
    tabla = cargar_respuestas_basicas(ruta=tmp_path / "no_existe.csv")
    assert tabla.empty
    # responder_basica() sin ``ruta`` explícita sigue usando el CSV real del proyecto.
    assert responder_basica("hola", contexto=CONTEXTO_DEMO) is not None
