import pandas as pd
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

import app


@pytest.fixture(scope="module")
def malla_minima():
    return pd.DataFrame(
        [
            {"codigo_ramo": "AEA315", "nombre_ramo": "Microeconomía II"},
            {"codigo_ramo": "AEA425", "nombre_ramo": "Econometría"},
            {"codigo_ramo": "AEA503", "nombre_ramo": "Marketing Estratégico"},
        ]
    )


@pytest.mark.parametrize(
    ("pregunta", "esperada"),
    [
        ("hola", "saludo"),
        ("muchas gracias", "agradecimiento"),
        ("estoy perdido", "confusion"),
        ("q ramos tengo", "ramos_inscritos"),
        ("¿cuál es mi sede?", "datos_alumno"),
        ("voy atrasado", "alertas"),
        ("riesgo académico", "alertas"),
        ("muéstrame mi avance curricular", "avance_curricular"),
    ],
)
def test_clasificacion_general(malla_minima, pregunta, esperada):
    resultado = app.clasificar_consulta(pregunta, malla=malla_minima)
    assert resultado.intencion == esperada


@pytest.mark.parametrize(
    "variante",
    [
        "prerequisito",
        "pre requisito",
        "pre-requisito",
        "prerrequisito",
    ],
)
def test_variantes_prerrequisito(malla_minima, variante):
    resultado = app.clasificar_consulta(
        f"¿Qué {variante} tiene AEA315?", malla=malla_minima
    )
    assert resultado.intencion == "prerrequisitos"
    assert resultado.codigo_ramo == "AEA315"


@pytest.mark.parametrize(
    "variante",
    [
        "¿cómo evalúan AEA315?",
        "¿cuánto vale AEA315?",
        "¿qué porcentaje vale AEA315?",
        "¿cuál es la ponderación de AEA315?",
        "¿tiene pruebas AEA315?",
        "¿hay controles en AEA315?",
        "¿tiene examen AEA315?",
        "¿cómo es la cátedra de AEA315?",
    ],
)
def test_variantes_evaluacion(malla_minima, variante):
    resultado = app.clasificar_consulta(variante, malla=malla_minima)
    assert resultado.intencion == "evaluaciones"
    assert resultado.codigo_ramo == "AEA315"


def test_deteccion_de_ramo_por_codigo_y_nombre(malla_minima):
    assert app.detectar_ramo(malla_minima, "Revisa AEA425")[0] == "AEA425"
    assert (
        app.detectar_ramo(malla_minima, "qué contiene microeconomia ii")[0]
        == "AEA315"
    )


def test_seguimiento_reutiliza_ramo_anterior(malla_minima):
    contexto = {
        "codigo_ramo": "AEA315",
        "nombre_ramo": "Microeconomía II",
    }
    resultado = app.clasificar_consulta(
        "¿y la bibliografía?", malla=malla_minima, ramo_contexto=contexto
    )
    assert resultado.intencion == "bibliografia"
    assert resultado.codigo_ramo == "AEA315"
    assert resultado.es_seguimiento is True
    assert resultado.confianza == "media"


def test_cadena_de_seguimiento_mantiene_el_mismo_ramo(malla_minima):
    contexto = {
        "codigo_ramo": "AEA315",
        "nombre_ramo": "Microeconomía II",
    }
    casos = [
        ("¿y la bibliografía?", "bibliografia"),
        ("¿cómo se evalúa?", "evaluaciones"),
        ("¿tiene prerrequisitos?", "prerrequisitos"),
    ]
    for pregunta, intencion in casos:
        resultado = app.clasificar_consulta(
            pregunta, malla=malla_minima, ramo_contexto=contexto
        )
        assert resultado.intencion == intencion
        assert resultado.codigo_ramo == "AEA315"
        assert resultado.es_seguimiento is True


def test_ramo_explicito_reemplaza_contexto(malla_minima):
    contexto = {
        "codigo_ramo": "AEA315",
        "nombre_ramo": "Microeconomía II",
    }
    resultado = app.clasificar_consulta(
        "¿cómo se evalúa Econometría?",
        malla=malla_minima,
        ramo_contexto=contexto,
    )
    assert resultado.intencion == "evaluaciones"
    assert resultado.codigo_ramo == "AEA425"
    assert resultado.confianza == "alta"


def test_seguimiento_sin_contexto_pide_ramo(malla_minima):
    resultado = app.clasificar_consulta(
        "¿cómo se evalúa?", malla=malla_minima
    )
    assert resultado.intencion == "pedir_ramo"
    assert resultado.requiere_ramo is True


def test_busqueda_documental_usa_posiciones_con_indice_sucio():
    chunks = pd.DataFrame(
        [
            {"codigo_ramo": "AAA100", "texto": "marketing ventas estrategia"},
            {"codigo_ramo": "BBB200", "texto": "costos fijos variables presupuesto"},
            {"codigo_ramo": "BBB200", "texto": "presupuesto costos control"},
        ],
        index=[101, 205, 999],
    )
    vectorizador = TfidfVectorizer()
    matriz = vectorizador.fit_transform(chunks["texto"])

    resultados = app.buscar_documentos(
        chunks,
        "costos presupuesto",
        vectorizador,
        matriz,
        codigo_ramo="BBB200",
        top_k=2,
        umbral=0.0,
    )

    assert len(resultados) == 2
    assert set(resultados["codigo_ramo"]) == {"BBB200"}
    assert resultados["score"].is_monotonic_decreasing


def test_preguntas_rapidas_se_adaptan_al_alumno():
    ramos = pd.DataFrame(
        [{"codigo_ramo": "AEA315", "nombre_ramo": "Microeconomía II"}]
    )
    preguntas = app.construir_preguntas_rapidas(ramos)
    assert len(preguntas) <= 7
    assert any("Microeconomía II" in pregunta for pregunta in preguntas)
    assert any("Cómo se evalúa" in pregunta for pregunta in preguntas)
