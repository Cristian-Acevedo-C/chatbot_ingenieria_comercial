"""Orientación académica: prioridades, ramos críticos, desbloqueo y semáforo."""

import pandas as pd
import pytest

from chatbot.contratos import RespuestaChatbot
from chatbot.intenciones import clasificar_consulta
from chatbot.respuestas import responder
from chatbot.respuestas.orientacion import (
    obtener_ramos_criticos,
    obtener_ramos_desbloqueados,
    recomendar_prioridades_academicas,
    responder_orientacion_academica,
)


@pytest.fixture
def malla():
    return pd.DataFrame(
        [
            {"codigo_ramo": "AEA100", "nombre_ramo": "Microeconomía I"},
            {"codigo_ramo": "AEA200", "nombre_ramo": "Microeconomía II"},
            {"codigo_ramo": "AEA300", "nombre_ramo": "Microeconomía III"},
        ]
    )


@pytest.fixture
def prerrequisitos():
    return pd.DataFrame(
        [
            {
                "codigo_ramo": "AEA200", "nombre_ramo": "Microeconomía II",
                "codigo_prerrequisito": "AEA100", "nombre_prerrequisito": "Microeconomía I",
                "tipo": "Prerrequisito", "fuente_archivo": "AEA200.pdf",
                "evidencia_textual": "Requisito: Microeconomía I.", "confianza": "Alta",
            },
            {
                "codigo_ramo": "AEA300", "nombre_ramo": "Microeconomía III",
                "codigo_prerrequisito": "AEA100", "nombre_prerrequisito": "Microeconomía I",
                "tipo": "Prerrequisito", "fuente_archivo": "AEA300.pdf",
                "evidencia_textual": "Requisito: Microeconomía I.", "confianza": "Alta",
            },
        ]
    )


@pytest.mark.parametrize(
    ("pregunta", "esperada"),
    [
        ("¿Qué ramos debería priorizar?", "orientacion_academica"),
        ("¿Qué ramos son críticos?", "orientacion_academica"),
        ("¿Cuáles son los ramos más importantes para avanzar?", "orientacion_academica"),
        ("¿Qué me recomiendas para mejorar mi avance?", "orientacion_academica"),
        ("¿Qué ramos me pueden atrasar más?", "orientacion_academica"),
        ("¿Qué significa el semáforo de este alumno?", "orientacion_academica"),
        ("¿Qué pasa si repruebo AEA100?", "orientacion_academica"),
        ("¿Qué ramos desbloquea AEA100?", "orientacion_academica"),
        ("¿Qué debería estudiar antes de tomar AEA200?", "orientacion_academica"),
        # No debe interferir con clasificaciones existentes.
        ("muéstrame mi avance curricular", "avance_curricular"),
        ("¿tengo alguna alerta académica?", "alertas"),
    ],
)
def test_clasificacion_orientacion(malla, pregunta, esperada):
    assert clasificar_consulta(pregunta, malla=malla).intencion == esperada


def test_obtener_ramos_criticos_requiere_mas_de_un_uso(prerrequisitos):
    criticos = obtener_ramos_criticos(prerrequisitos)
    assert list(criticos["codigo_prerrequisito"]) == ["AEA100"]
    assert criticos.iloc[0]["veces_requerido"] == 2


def test_obtener_ramos_criticos_vacio_sin_prerrequisitos():
    assert obtener_ramos_criticos(pd.DataFrame()).empty


def test_obtener_ramos_desbloqueados(prerrequisitos):
    desbloqueados = obtener_ramos_desbloqueados(prerrequisitos, "AEA100")
    assert set(desbloqueados["codigo_ramo"]) == {"AEA200", "AEA300"}


def test_obtener_ramos_desbloqueados_sin_codigo_no_falla(prerrequisitos):
    assert obtener_ramos_desbloqueados(prerrequisitos, None).empty


def test_recomendar_prioridades_prioriza_riesgos_del_alumno_primero(prerrequisitos):
    prerrequisitos_alumno = pd.DataFrame(
        [
            {
                "codigo_ramo": "AEA200", "nombre_ramo": "Microeconomía II",
                "codigo_prerrequisito": "AEA100", "tipo": "Prerrequisito",
                "estado_prerrequisito": "Reprobado", "alerta": "Riesgo alto",
            }
        ]
    )
    criticos = obtener_ramos_criticos(prerrequisitos)
    prioridades = recomendar_prioridades_academicas(prerrequisitos, prerrequisitos_alumno, criticos)
    assert prioridades[0]["codigo"] == "AEA200"


def test_responder_orientacion_academica_semaforo_usa_alumno():
    historial = pd.DataFrame(
        [{"codigo_ramo": "AEA100", "estado": "Reprobado", "nota": 3.0}]
    )
    respuesta = responder_orientacion_academica(
        "que significa el semaforo de este alumno",
        {"nombre": "Ana Pérez"},
        historial,
        pd.DataFrame(),
        pd.DataFrame(),
    )
    assert isinstance(respuesta, RespuestaChatbot)
    assert "Ana Pérez" in respuesta.resumen
    assert "Riesgo académico" in respuesta.resumen or "Atención" in respuesta.resumen


def test_responder_orientacion_academica_sin_alumno_no_falla():
    respuesta = responder_orientacion_academica(
        "que significa el semaforo", None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    )
    assert isinstance(respuesta, RespuestaChatbot)
    assert respuesta.resumen


def test_responder_orientacion_academica_desbloquea_sin_codigo_pide_ramo():
    respuesta = responder_orientacion_academica(
        "que ramos desbloquea", None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    )
    assert "Indícame" in respuesta.resumen


def test_orientacion_academica_end_to_end_usa_prerrequisitos_reales(malla, prerrequisitos):
    """'Qué ramos desbloquea AEA100' debe reflejar exactamente prerrequisitos.csv."""
    clasificacion = clasificar_consulta("¿Qué ramos desbloquea AEA100?", malla=malla)
    respuesta = responder(
        "¿Qué ramos desbloquea AEA100?",
        {"nombre": "Ana Pérez"},
        pd.DataFrame(), pd.DataFrame(), prerrequisitos, malla, pd.DataFrame(),
        None, None, None, clasificacion, "Ingeniería Comercial",
    )
    assert respuesta.tipo == "orientacion_academica"
    codigos = {fila["Código"] for fila in respuesta.secciones[0].contenido}
    assert codigos == {"AEA200", "AEA300"}


def test_orientacion_no_inventa_para_ramo_sin_datos(malla):
    """FIS504-like: ramo sin relaciones registradas no debe inventar desbloqueo."""
    clasificacion = clasificar_consulta("¿Qué ramos desbloquea AEA300?", malla=malla)
    respuesta = responder(
        "¿Qué ramos desbloquea AEA300?",
        {"nombre": "Ana Pérez"},
        pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), malla, pd.DataFrame(),
        None, None, None, clasificacion, "Ingeniería Comercial",
    )
    assert not respuesta.secciones
    assert "No encontré ramos" in respuesta.resumen
