"""services.resumen: resumen documental, semáforo, métricas del sistema y demo guiada."""

import pandas as pd
import pytest

from services.datos import cargar_datos, filtrar_chunks_por_carrera, filtrar_por_carrera
from services.resumen import calcular_metricas_sistema, construir_guion_demo


@pytest.fixture(scope="module")
def datos_reales():
    return cargar_datos()


def _cargar_carrera(datos_reales, carrera):
    alumnos, malla, inscritos, historial, chunks, prerrequisitos = datos_reales
    return {
        "alumnos": filtrar_por_carrera(alumnos, carrera),
        "malla": filtrar_por_carrera(malla, carrera),
        "historial": filtrar_por_carrera(historial, carrera),
        "prerrequisitos": filtrar_por_carrera(prerrequisitos, carrera),
        "chunks": filtrar_chunks_por_carrera(chunks, carrera),
    }


def test_metricas_sistema_ici_se_calculan_desde_data(datos_reales):
    carrera = "Ingeniería Civil Industrial"
    datos = _cargar_carrera(datos_reales, carrera)
    metricas = calcular_metricas_sistema(
        carrera, datos["alumnos"], datos["historial"], datos["chunks"],
        datos["malla"], datos["prerrequisitos"], etiqueta_motor="TF-IDF",
    )
    assert metricas["carrera"] == carrera
    assert metricas["documentos_disponibles"] == 51
    assert metricas["programas_pendientes"] == 1
    assert metricas["ramos_en_malla"] == 52
    assert metricas["prerrequisitos_cargados"] == 79
    assert metricas["alumnos_demo"] == 10
    assert metricas["registros_historial"] == 283
    assert metricas["ultima_actualizacion_metadata"] != "No disponible"
    assert metricas["motor_busqueda"] == "TF-IDF"
    assert metricas["estado_general"] == "Operativo demo"


def test_metricas_sistema_comercial_se_calculan_desde_data(datos_reales):
    carrera = "Ingeniería Comercial"
    datos = _cargar_carrera(datos_reales, carrera)
    metricas = calcular_metricas_sistema(
        carrera, datos["alumnos"], datos["historial"], datos["chunks"],
        datos["malla"], datos["prerrequisitos"],
    )
    assert metricas["carrera"] == carrera
    assert metricas["documentos_disponibles"] == 53
    assert metricas["programas_pendientes"] == 0
    assert metricas["alumnos_demo"] == 8
    # Comercial no tiene manifiesto de metadata propio: debe declararlo, no inventar fecha.
    assert metricas["ultima_actualizacion_metadata"] == "No disponible"
    assert metricas["motor_busqueda"] == "No disponible"


def test_metricas_sistema_no_mezcla_carreras(datos_reales):
    ici = calcular_metricas_sistema(
        "Ingeniería Civil Industrial",
        *[_cargar_carrera(datos_reales, "Ingeniería Civil Industrial")[clave]
          for clave in ("alumnos", "historial", "chunks", "malla", "prerrequisitos")],
    )
    comercial = calcular_metricas_sistema(
        "Ingeniería Comercial",
        *[_cargar_carrera(datos_reales, "Ingeniería Comercial")[clave]
          for clave in ("alumnos", "historial", "chunks", "malla", "prerrequisitos")],
    )
    assert ici["documentos_disponibles"] != comercial["documentos_disponibles"]
    assert ici["alumnos_demo"] != comercial["alumnos_demo"]


def test_metricas_sistema_con_dataframes_vacios_no_explota():
    vacio = pd.DataFrame()
    metricas = calcular_metricas_sistema(
        "Carrera Inexistente", vacio, vacio, vacio, vacio, vacio,
    )
    assert metricas["documentos_disponibles"] == 0
    assert metricas["programas_pendientes"] == 0
    assert metricas["alumnos_demo"] == 0
    assert metricas["registros_historial"] == 0
    assert metricas["ultima_actualizacion_metadata"] == "No disponible"


def test_metricas_sistema_con_none_no_explota():
    metricas = calcular_metricas_sistema(
        "Carrera X", None, None, None, pd.DataFrame(), pd.DataFrame(),
    )
    assert metricas["alumnos_demo"] == 0
    assert metricas["fragmentos_indexados"] == 0
    assert metricas["registros_historial"] == 0


def test_construir_guion_demo_es_dinamico_y_no_hardcodea(datos_reales):
    carrera = "Ingeniería Civil Industrial"
    datos = _cargar_carrera(datos_reales, carrera)
    alumno = datos["alumnos"].iloc[0]
    from services.resumen import calcular_resumen_documental

    resumen_doc = calcular_resumen_documental(
        carrera, datos["chunks"], datos["malla"], datos["prerrequisitos"]
    )
    guion = construir_guion_demo(
        carrera, alumno, datos["chunks"], resumen_doc,
        ["Ingeniería Comercial", "Ingeniería Civil Industrial"],
    )
    preguntas = [pregunta for pregunta, _ in guion]
    assert any("hola" in pregunta.lower() for pregunta in preguntas)
    assert any(str(alumno["nombre"]) in explicacion for _, explicacion in guion)
    # El código de ramo usado en el guion debe ser uno real de esta carrera.
    codigo_real = datos["chunks"]["codigo_ramo"].dropna().astype(str).iloc[0]
    assert any(codigo_real in pregunta for pregunta in preguntas)
    # FIS504 (pendiente) debe aparecer como caso "no inventar".
    assert any("FIS504" in pregunta for pregunta in preguntas)
    assert any("aislamiento multicarrera" in explicacion for _, explicacion in guion)


def test_construir_guion_demo_sin_alumno_ni_chunks_no_explota():
    guion = construir_guion_demo(
        "Carrera Vacía", None, pd.DataFrame(),
        {"programas_pendientes": []}, ["Carrera Vacía"],
    )
    assert len(guion) >= 2
