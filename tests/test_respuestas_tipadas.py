import pandas as pd
import pytest

from chatbot.contratos import RespuestaChatbot, SeccionRespuesta
from chatbot.respuestas import (
    construir_respuesta_academica,
    respuesta_alertas,
    respuesta_datos_alumno,
    respuesta_documental,
    respuesta_pedir_ramo,
    respuesta_prerrequisitos_no_cargados,
    respuesta_prerrequisitos_ramo,
    respuesta_recomendacion,
    respuesta_ramos,
    respuesta_sin_evidencia,
)
from chatbot.respuestas.render_contract import construir_bloques_render


def afirmar_contrato(respuesta, tipo):
    assert isinstance(respuesta, RespuestaChatbot)
    assert respuesta.tipo == tipo
    assert respuesta.resumen
    assert construir_bloques_render(respuesta)


def test_respuesta_ramos_es_contrato():
    ramos = pd.DataFrame([
        {"codigo_ramo": "AEA100", "nombre_ramo": "Introducción", "estado": "Inscrito"}
    ])
    respuesta = respuesta_ramos(ramos)
    afirmar_contrato(respuesta, "ramos_inscritos")
    assert respuesta.fuentes


def test_respuesta_datos_alumno_es_contrato():
    respuesta = respuesta_datos_alumno({
        "nombre": "Ana",
        "sede": "Santiago",
        "jornada": "Diurna",
        "semestre_actual": 2,
        "carrera": "Ingeniería Comercial",
    })
    afirmar_contrato(respuesta, "datos_alumno")
    assert "Santiago" in respuesta.resumen


def test_respuesta_documental_sin_evidencia_es_contrato():
    respuesta = respuesta_sin_evidencia("Econometría")
    afirmar_contrato(respuesta, "documental")
    assert not respuesta.evidencias
    assert respuesta.resumen == (
        "No encontré evidencia suficiente en los documentos cargados. "
        "Verifica esta información en la fuente oficial UDLA o con coordinación "
        "académica."
    )
    assert not respuesta.fuentes


def test_respuesta_documental_tipifica_evidencia_score_y_pagina():
    resultados = pd.DataFrame([{
        "texto": "[Página 4] Contenido sobre regresión lineal.",
        "nombre_ramo": "Econometría",
        "ruta_archivo": "documentos/econometria.pdf",
        "fuente_legible": "Programa de Econometría",
        "pagina_aproximada": 4,
        "score": 0.72,
    }])
    respuesta = respuesta_documental(resultados, "Econometría")
    afirmar_contrato(respuesta, "documental")
    assert respuesta.evidencias[0].score == pytest.approx(0.72)
    assert respuesta.evidencias[0].pagina == "4"
    assert respuesta.evidencias[0].fuente.startswith("Fuente: econometria.pdf")


def _prerrequisito(tipo="Prerrequisito"):
    return pd.DataFrame([{
        "codigo_ramo": "AEA200",
        "nombre_ramo": "Microeconomía II",
        "codigo_prerrequisito": "AEA100" if tipo == "Prerrequisito" else "",
        "nombre_prerrequisito": "Microeconomía I" if tipo == "Prerrequisito" else "",
        "tipo": tipo,
        "fuente_archivo": "programa_microeconomia_ii.pdf",
        "evidencia_textual": "Requisito: Microeconomía I.",
        "confianza": "Alta",
    }])


def test_prerrequisitos_no_cargados_es_contrato():
    respuesta = respuesta_prerrequisitos_no_cargados()
    afirmar_contrato(respuesta, "prerrequisitos")
    assert respuesta.fuentes


def test_ramo_sin_prerrequisito_es_contrato():
    respuesta = respuesta_prerrequisitos_ramo(
        _prerrequisito("Sin prerrequisito"),
        "AEA200",
        "Microeconomía II",
        pd.DataFrame(),
    )
    afirmar_contrato(respuesta, "prerrequisitos")
    assert "sin prerrequisito" in respuesta.resumen.lower()


@pytest.mark.parametrize(("historial", "estado"), [
    (
        pd.DataFrame([{"codigo_ramo": "AEA100", "estado": "Aprobado"}]),
        "Aprobado",
    ),
    (
        pd.DataFrame(columns=["codigo_ramo", "estado"]),
        "Pendiente",
    ),
])
def test_ramo_con_prerrequisito_conserva_estado(historial, estado):
    respuesta = respuesta_prerrequisitos_ramo(
        _prerrequisito(),
        "AEA200",
        "Microeconomía II",
        historial,
    )
    afirmar_contrato(respuesta, "prerrequisitos")
    assert estado in respuesta.secciones[0].contenido
    assert respuesta.fuentes


def test_alerta_sin_historial_es_contrato():
    respuesta = respuesta_alertas(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    afirmar_contrato(respuesta, "alertas")
    assert "No existe historial suficiente" in respuesta.resumen


def test_alerta_con_reprobado_es_contrato():
    historial = pd.DataFrame([{
        "codigo_ramo": "AEA100",
        "nombre_ramo": "Microeconomía I",
        "estado": "Reprobado",
        "nota": 3.2,
    }])
    respuesta = respuesta_alertas(historial, pd.DataFrame(), pd.DataFrame())
    afirmar_contrato(respuesta, "alertas")
    assert "1 ramos reprobados" in respuesta.resumen


def test_alerta_con_prerrequisito_en_riesgo():
    historial = pd.DataFrame([{
        "codigo_ramo": "AEA100",
        "nombre_ramo": "Microeconomía I",
        "estado": "Cursando",
        "nota": 4.0,
    }])
    vista = pd.DataFrame([{
        "codigo_ramo": "AEA200",
        "codigo_prerrequisito": "AEA100",
        "tipo": "Prerrequisito",
        "estado_prerrequisito": "Cursando",
        "alerta": "Riesgo medio",
    }])
    respuesta = respuesta_alertas(historial, vista, _prerrequisito())
    afirmar_contrato(respuesta, "alertas")
    assert "Riesgo medio" in respuesta.secciones[0].contenido


def test_pedir_ramo_es_contrato():
    respuesta = respuesta_pedir_ramo(
        {
            "Todos los ramos": None,
            "AEA100 — Microeconomía I": {"codigo_ramo": "AEA100"},
        }
    )
    afirmar_contrato(respuesta, "pedir_ramo")
    assert "Microeconomía I" in respuesta.secciones[0].contenido


def test_recomendacion_es_contrato():
    ramos = pd.DataFrame([
        {"codigo_ramo": "AEA100", "nombre_ramo": "Microeconomía I"}
    ])
    respuesta = respuesta_recomendacion(
        ramos,
        pd.DataFrame(),
        pd.DataFrame(columns=["tipo", "alerta"]),
    )
    afirmar_contrato(respuesta, "recomendacion")
    assert respuesta.fuentes


@pytest.fixture
def programa_academico():
    texto = (
        "[Página 1] 5. CONTENIDOS N° Unidad Tema "
        "1 Microeconomía • Oferta y demanda • Elasticidad "
        "6. ESTRATEGIAS METODOLÓGICAS "
        "7. EVALUACIÓN La evaluación de la asignatura considera 2 cátedras, "
        "3 ejercicios y un examen final. "
        "8. RECURSOS DE APRENDIZAJE "
        "8.1 BIBLIOGRAFÍA BÁSICA MANKIW, Gregory 2020 Principios de economía PEARSON "
        "8.2 BIBLIOGRAFÍA COMPLEMENTARIA "
        "8.3 RECURSOS INFORMÁTICOS"
    )
    return pd.DataFrame([{
        "chunk_id": "AEA100_programa_0",
        "codigo_ramo": "AEA100",
        "nombre_ramo": "Microeconomía I",
        "ruta_archivo": "documentos/microeconomia_i.pdf",
        "fuente_legible": "Programa de Microeconomía I",
        "pagina_aproximada": 1,
        "texto": texto,
    }])


@pytest.mark.parametrize("tipo", ["estudio", "contenidos", "bibliografia", "evaluaciones"])
def test_respuesta_academica_es_contrato_renderizable(programa_academico, tipo):
    respuesta = construir_respuesta_academica(
        tipo,
        "AEA100",
        "Microeconomía I",
        programa_academico,
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    afirmar_contrato(respuesta, tipo)
    assert respuesta.metadata["formato_original"] == "academico"
    assert all(seccion.formato == "tabla" for seccion in respuesta.secciones)
    # El flujo académico activo ya no arrastra el dict legacy duplicado.
    assert "payload_original" not in respuesta.metadata


def test_respuesta_estudio_arma_secciones_tipadas(programa_academico):
    respuesta = construir_respuesta_academica(
        "estudio",
        "AEA100",
        "Microeconomía I",
        programa_academico,
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    titulos = [seccion.titulo for seccion in respuesta.secciones]
    assert "Qué estudiar" in titulos
    assert respuesta.secciones
    assert all(isinstance(seccion, SeccionRespuesta) for seccion in respuesta.secciones)


def test_renderer_no_depende_de_metadata_legacy(programa_academico):
    respuesta = construir_respuesta_academica(
        "contenidos",
        "AEA100",
        "Microeconomía I",
        programa_academico,
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    # Vaciar metadata simula un contrato sin rastros legacy: aún debe renderizar.
    respuesta.metadata = {}
    bloques = construir_bloques_render(respuesta)
    tipos = [bloque["tipo"] for bloque in bloques]
    assert "resumen" in tipos
    assert "tabla" in tipos
