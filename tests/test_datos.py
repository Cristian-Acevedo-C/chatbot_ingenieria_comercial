"""Carga de CSV: mensajes de error accionables y validación de columnas."""

import pytest

from services import datos


def test_cargar_csv_archivo_faltante_mensaje_accionable(tmp_path, monkeypatch):
    monkeypatch.setattr(datos, "DATA_DIR", tmp_path)
    with pytest.raises(FileNotFoundError) as exc:
        datos.cargar_csv("inexistente.csv")
    mensaje = str(exc.value)
    assert "inexistente.csv" in mensaje
    assert "data" in mensaje


def test_cargar_csv_faltante_con_permitir_vacio_devuelve_df_vacio(tmp_path, monkeypatch):
    monkeypatch.setattr(datos, "DATA_DIR", tmp_path)
    df = datos.cargar_csv("opcional.csv", permitir_vacio=True)
    assert df.empty


def test_cargar_csv_archivo_vacio_es_error(tmp_path, monkeypatch):
    monkeypatch.setattr(datos, "DATA_DIR", tmp_path)
    (tmp_path / "vacio.csv").write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        datos.cargar_csv("vacio.csv")


def test_cargar_csv_columnas_faltantes_lista_columnas(tmp_path, monkeypatch):
    monkeypatch.setattr(datos, "DATA_DIR", tmp_path)
    (tmp_path / "datos.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        datos.cargar_csv("datos.csv", columnas_requeridas={"a", "c"})
    mensaje = str(exc.value)
    assert "c" in mensaje
    assert "datos.csv" in mensaje


def test_cargar_csv_ok_devuelve_registros(tmp_path, monkeypatch):
    monkeypatch.setattr(datos, "DATA_DIR", tmp_path)
    (tmp_path / "ok.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    df = datos.cargar_csv("ok.csv", columnas_requeridas={"a", "b"})
    assert len(df) == 1
    assert list(df.columns) == ["a", "b"]
