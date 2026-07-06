"""Manejo profesional de 'sin evidencia suficiente': no inventa, explica por qué."""

import pandas as pd
import pytest

from chatbot.respuestas.documental import respuesta_documental, respuesta_sin_evidencia


def test_sin_contexto_conserva_mensaje_generico():
    respuesta = respuesta_sin_evidencia()
    assert respuesta.resumen == (
        "No encontré evidencia suficiente en los documentos cargados. "
        "Verifica esta información en la fuente oficial UDLA o con coordinación "
        "académica."
    )
    assert not respuesta.secciones
    assert not respuesta.fuentes


def test_ramo_pendiente_lo_dice_explicitamente(tmp_path, monkeypatch):
    """Usa un manifiesto de metadata sintético con un ramo pendiente real."""
    from services import datos as datos_module

    carreras_dir = tmp_path / "carreras" / "demo" / "metadata"
    carreras_dir.mkdir(parents=True)
    (carreras_dir / "metadata_programas.csv").write_text(
        "carrera,codigo_asignatura,nombre_archivo,ruta_archivo,tipo_documento,estado\n"
        "Demo,ZZZ999,ZZZ999.pdf,pdf/ZZZ999.pdf,programa_asignatura,pendiente\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(datos_module, "CARRERAS_DIR", tmp_path / "carreras")

    respuesta = respuesta_sin_evidencia("Ramo Fantasma", codigo_ramo="ZZZ999", carrera="Demo")
    assert "pendiente" in respuesta.resumen.lower()
    assert "ZZZ999" in respuesta.resumen
    assert not respuesta.fuentes
    assert respuesta.secciones[0].titulo == "Esto puede ocurrir porque"
    assert respuesta.recomendacion


def test_ramo_no_pendiente_no_afirma_falsamente_pendiente(tmp_path, monkeypatch):
    from services import datos as datos_module

    carreras_dir = tmp_path / "carreras" / "demo" / "metadata"
    carreras_dir.mkdir(parents=True)
    (carreras_dir / "metadata_programas.csv").write_text(
        "carrera,codigo_asignatura,nombre_archivo,ruta_archivo,tipo_documento,estado\n"
        "Demo,ZZZ999,ZZZ999.pdf,pdf/ZZZ999.pdf,programa_asignatura,pendiente\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(datos_module, "CARRERAS_DIR", tmp_path / "carreras")

    # AAA111 no aparece en el manifiesto: no debe marcarse como pendiente.
    respuesta = respuesta_sin_evidencia("Otro ramo", codigo_ramo="AAA111", carrera="Demo")
    assert "pendiente" not in respuesta.resumen.lower()
    assert "AAA111" in respuesta.resumen
    assert not respuesta.fuentes


def test_respuesta_documental_sin_resultados_no_cita_fuente_falsa():
    respuesta = respuesta_documental(pd.DataFrame(), nombre_ramo="Ramo X", codigo_ramo="XYZ123")
    assert not respuesta.fuentes
    assert not respuesta.evidencias
    assert "XYZ123" in respuesta.resumen


def test_respuesta_documental_no_mezcla_pendiente_de_otra_carrera(tmp_path, monkeypatch):
    """Un código pendiente en Carrera A no debe marcarse pendiente al consultarlo en Carrera B."""
    from services import datos as datos_module

    carreras_dir = tmp_path / "carreras" / "demo" / "metadata"
    carreras_dir.mkdir(parents=True)
    (carreras_dir / "metadata_programas.csv").write_text(
        "carrera,codigo_asignatura,nombre_archivo,ruta_archivo,tipo_documento,estado\n"
        "Carrera A,ZZZ999,ZZZ999.pdf,pdf/ZZZ999.pdf,programa_asignatura,pendiente\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(datos_module, "CARRERAS_DIR", tmp_path / "carreras")

    respuesta = respuesta_sin_evidencia("Ramo", codigo_ramo="ZZZ999", carrera="Carrera B")
    assert "pendiente" not in respuesta.resumen.lower()
