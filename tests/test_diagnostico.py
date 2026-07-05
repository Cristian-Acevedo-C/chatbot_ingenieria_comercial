"""Diagnóstico de archivos de datos (vista Admin demo)."""

from services.diagnostico import diagnosticar_datos


def test_diagnostico_detecta_archivo_faltante(tmp_path):
    filas = diagnosticar_datos(data_dir=tmp_path, esquemas={"x.csv": {"a", "b"}})
    assert filas[0]["archivo"] == "x.csv"
    assert filas[0]["existe"] is False
    assert filas[0]["filas"] == 0


def test_diagnostico_detecta_columnas_faltantes(tmp_path):
    (tmp_path / "x.csv").write_text("a\n1\n2\n", encoding="utf-8")
    filas = diagnosticar_datos(data_dir=tmp_path, esquemas={"x.csv": {"a", "b"}})
    assert filas[0]["existe"] is True
    assert filas[0]["filas"] == 2
    assert filas[0]["columnas_faltantes"] == ["b"]


def test_diagnostico_archivo_completo_sin_faltantes(tmp_path):
    (tmp_path / "ok.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    filas = diagnosticar_datos(data_dir=tmp_path, esquemas={"ok.csv": {"a", "b"}})
    assert filas[0]["existe"] is True
    assert filas[0]["columnas_faltantes"] == []
