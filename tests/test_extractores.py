from rag.extractores import (
    extraer_aprendizajes_desde_texto,
    extraer_bibliografia_desde_texto,
    extraer_contenidos_desde_texto,
    extraer_evaluaciones_desde_texto,
    limpiar_texto_programa,
)


def test_limpieza_elimina_cabecera_de_pagina():
    texto = "[Página 1] Publicado por: UDLA Página: 1 de 5 Contenido útil"
    limpio = limpiar_texto_programa(texto)
    assert "Publicado por" not in limpio
    assert "Contenido útil" in limpio


def test_extrae_contenidos_estructurados():
    texto = (
        "5. CONTENIDOS N° Unidad Tema "
        "1 Microeconomía • Oferta y demanda • Elasticidad "
        "6. ESTRATEGIAS METODOLÓGICAS"
    )
    contenidos = extraer_contenidos_desde_texto(texto)
    assert contenidos
    assert contenidos[0]["Unidad"] == "Unidad 1"
    assert "Microeconomía" in contenidos[0]["Tema principal"]


def test_extrae_bibliografia():
    texto = (
        "8.1 BIBLIOGRAFÍA BÁSICA MANKIW, Gregory 2020 Principios de economía PEARSON "
        "8.2 BIBLIOGRAFÍA COMPLEMENTARIA "
        "8.3 RECURSOS INFORMÁTICOS"
    )
    bibliografia = extraer_bibliografia_desde_texto(texto)
    assert bibliografia
    assert bibliografia[0]["Tipo"] == "Básica"


def test_extrae_evaluaciones():
    texto = (
        "7. EVALUACIÓN La evaluación de la asignatura considera 2 cátedras, "
        "3 ejercicios y un examen final. 8. RECURSOS DE APRENDIZAJE"
    )
    componentes = {fila["Componente"] for fila in extraer_evaluaciones_desde_texto(texto)}
    assert {"Cátedras", "Ejercicios", "Examen final"} <= componentes


def test_extrae_resultados_de_aprendizaje_sin_inferir():
    texto = (
        "3. RESULTADOS DE APRENDIZAJE Resultados de Aprendizaje Descripción "
        "RAA1 Aplicar herramientas de análisis de datos. "
        "RAA2 Proponer soluciones sustentables. "
        "4. APORTES AL PERFIL DE EGRESO"
    )

    aprendizajes = extraer_aprendizajes_desde_texto(texto)

    assert aprendizajes == [
        {"Resultado": "RAA1", "Descripción": "Aplicar herramientas de análisis de datos"},
        {"Resultado": "RAA2", "Descripción": "Proponer soluciones sustentables"},
    ]
