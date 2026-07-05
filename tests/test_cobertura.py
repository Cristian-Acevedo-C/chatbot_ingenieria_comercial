"""Métricas de cobertura documental."""

import pandas as pd

from services.cobertura import calcular_cobertura_documental


def _chunks():
    return pd.DataFrame([
        {"codigo_ramo": "AAA100", "nombre_ramo": "Uno", "ruta_archivo": "a.pdf", "texto": "x"},
        {"codigo_ramo": "AAA100", "nombre_ramo": "Uno", "ruta_archivo": "a.pdf", "texto": "y"},
        {"codigo_ramo": "BBB200", "nombre_ramo": "Dos", "ruta_archivo": "b.pdf", "texto": "z"},
    ])


def test_cobertura_totales():
    cobertura = calcular_cobertura_documental(_chunks())
    assert cobertura["total_chunks"] == 3
    assert cobertura["ramos_con_documentos"] == 2
    assert cobertura["fuentes_distintas"] == 2


def test_cobertura_chunks_por_ramo():
    cobertura = calcular_cobertura_documental(_chunks())
    tabla = cobertura["chunks_por_ramo"]
    fila = tabla[tabla["codigo_ramo"] == "AAA100"].iloc[0]
    assert int(fila["chunks"]) == 2


def test_cobertura_ramos_inscritos_sin_evidencia():
    inscritos = pd.DataFrame([
        {"codigo_ramo": "AAA100", "nombre_ramo": "Uno"},
        {"codigo_ramo": "ZZZ999", "nombre_ramo": "Sin documento"},
    ])
    cobertura = calcular_cobertura_documental(_chunks(), inscritos)
    faltantes = [item["codigo_ramo"] for item in cobertura["ramos_inscritos_sin_evidencia"]]
    assert faltantes == ["ZZZ999"]


def test_cobertura_chunks_vacio_es_seguro():
    cobertura = calcular_cobertura_documental(pd.DataFrame())
    assert cobertura["total_chunks"] == 0
    assert cobertura["ramos_con_documentos"] == 0
    assert cobertura["fuentes_distintas"] == 0
    assert cobertura["ramos_inscritos_sin_evidencia"] == []
    assert cobertura["chunks_por_ramo"].empty
