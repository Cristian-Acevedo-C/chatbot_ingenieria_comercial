import pandas as pd
import pytest

from services.prerrequisitos import (
    construir_prerrequisitos_alumno,
    obtener_alerta_prerrequisito,
    obtener_estado_prerrequisito,
)


@pytest.mark.parametrize(("estado_historial", "esperado", "alerta"), [
    ("Aprobado", "Aprobado", "OK"),
    ("Cursando", "Cursando", "Riesgo medio"),
    ("Reprobado", "Reprobado", "Riesgo alto"),
])
def test_estado_segun_historial(estado_historial, esperado, alerta):
    historial = pd.DataFrame([{"codigo_ramo": "MAT100", "estado": estado_historial}])
    estado = obtener_estado_prerrequisito(historial, "MAT100", "Prerrequisito")
    assert estado == esperado
    assert obtener_alerta_prerrequisito(estado, "Prerrequisito") == alerta


def test_prerrequisito_ausente_queda_pendiente():
    historial = pd.DataFrame(columns=["codigo_ramo", "estado"])
    assert obtener_estado_prerrequisito(historial, "MAT100", "Prerrequisito") == "Pendiente"


@pytest.mark.parametrize(("tipo", "alerta"), [
    ("Sin prerrequisito", "OK"),
    ("No detectado", "Información incompleta"),
])
def test_tipos_sin_relacion_explicita(tipo, alerta):
    estado = obtener_estado_prerrequisito(pd.DataFrame(), "", tipo)
    assert estado == "No aplica"
    assert obtener_alerta_prerrequisito(estado, tipo) == alerta


def test_ramo_sin_fila_se_marca_no_detectado():
    ramos = pd.DataFrame([{"codigo_ramo": "AEA999", "nombre_ramo": "Ramo nuevo"}])
    vista = construir_prerrequisitos_alumno(ramos, pd.DataFrame(), pd.DataFrame([
        {"codigo_ramo": "OTR100", "tipo": "Sin prerrequisito"}
    ]))
    assert vista.iloc[0]["tipo"] == "No detectado"
    assert vista.iloc[0]["alerta"] == "Información incompleta"

