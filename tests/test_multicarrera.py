"""Integridad del corpus multicarrera y del programa pendiente."""

from pathlib import Path

import pandas as pd

from services.datos import cargar_datos, filtrar_por_carrera


ROOT = Path(__file__).resolve().parents[1]
BASE_ICI = ROOT / "data" / "carreras" / "ingenieria_civil_industrial"
METADATA = BASE_ICI / "metadata" / "metadata_programas_ici.csv"
INDICE = BASE_ICI / "indice" / "document_chunks.csv"
ACADEMICO = BASE_ICI / "academico"


def test_metadata_ici_registra_51_disponibles_y_un_pendiente():
    metadata = pd.read_csv(METADATA)
    assert list(metadata.columns) == [
        "carrera",
        "codigo_asignatura",
        "nombre_archivo",
        "ruta_archivo",
        "tipo_documento",
        "estado",
    ]
    assert len(metadata) == 52
    assert metadata["estado"].value_counts().to_dict() == {
        "disponible": 51,
        "pendiente": 1,
    }
    pendiente = metadata.loc[metadata["estado"].eq("pendiente")].iloc[0]
    assert pendiente["codigo_asignatura"] == "FIS504"
    assert not (ROOT / pendiente["ruta_archivo"]).exists()


def test_todos_los_programas_disponibles_existen_y_coinciden_con_metadata():
    metadata = pd.read_csv(METADATA)
    disponibles = metadata[metadata["estado"].eq("disponible")]
    for _, fila in disponibles.iterrows():
        ruta = ROOT / fila["ruta_archivo"]
        assert ruta.is_file()
        assert ruta.name == fila["nombre_archivo"]
        assert fila["tipo_documento"] == "programa_asignatura"


def test_indice_ici_no_contiene_el_programa_pendiente():
    indice = pd.read_csv(INDICE)
    assert set(indice["carrera"]) == {"Ingeniería Civil Industrial"}
    assert indice["ruta_archivo"].nunique() == 51
    assert "FIS504" not in set(indice["codigo_ramo"].astype(str))
    assert "EIN908" in set(indice["codigo_ramo"].astype(str))
    assert "EIN971" in set(indice["codigo_ramo"].astype(str))


def test_capa_academica_ici_tiene_malla_y_alumnos_sinteticos_separados():
    malla = pd.read_csv(ACADEMICO / "malla.csv")
    alumnos = pd.read_csv(ACADEMICO / "alumnos.csv")
    inscritos = pd.read_csv(ACADEMICO / "ramos_inscritos.csv")

    assert len(malla) == 52
    assert malla["codigo_ramo"].nunique() == 52
    assert set(malla["semestre"].astype(int)) == set(range(1, 11))
    fis504 = malla.loc[malla["codigo_ramo"].eq("FIS504")].iloc[0]
    assert int(fis504["semestre"]) == 5
    assert pd.isna(fis504["creditos"])

    assert len(alumnos) == 10
    assert alumnos["id_alumno"].nunique() == 10
    assert set(alumnos["origen_datos"]) == {"sintético"}
    assert set(alumnos["carrera"]) == {"Ingeniería Civil Industrial"}

    semestres = alumnos.set_index("id_alumno")["semestre_actual"].astype(int)
    malla_por_codigo = malla.set_index("codigo_ramo")["semestre"].astype(int)
    for _, fila in inscritos.iterrows():
        assert malla_por_codigo.loc[fila["codigo_ramo"]] == semestres.loc[
            int(fila["id_alumno"])
        ]


def test_prerrequisitos_ici_provienen_de_programas_y_conservan_pendiente():
    prerrequisitos = pd.read_csv(ACADEMICO / "prerrequisitos.csv")
    assert set(prerrequisitos["carrera"]) == {"Ingeniería Civil Industrial"}
    assert prerrequisitos["codigo_ramo"].nunique() == 52
    pendiente = prerrequisitos.loc[
        prerrequisitos["codigo_ramo"].eq("FIS504")
    ].iloc[0]
    assert pendiente["tipo"] == "No detectado"
    assert "No hay fragmentos" in pendiente["evidencia_textual"]
    relaciones = prerrequisitos[prerrequisitos["tipo"].eq("Prerrequisito")]
    assert relaciones["fuente_archivo"].str.endswith(".pdf").all()


def test_carga_multicarrera_combina_y_filtra_la_capa_academica():
    alumnos, malla, inscritos, historial, _chunks, prerrequisitos = cargar_datos()
    carrera = "Ingeniería Civil Industrial"

    assert len(filtrar_por_carrera(alumnos, carrera)) == 10
    assert len(filtrar_por_carrera(malla, carrera)) == 52
    assert len(filtrar_por_carrera(inscritos, carrera)) == 52
    assert len(filtrar_por_carrera(historial, carrera)) == 283
    assert len(filtrar_por_carrera(prerrequisitos, carrera)) == 79
