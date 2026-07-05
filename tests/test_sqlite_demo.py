"""Script de propuesta SQLite demo (no toca el backend activo CSV)."""

import sqlite3

from scripts.crear_sqlite_demo import crear_base


def test_crear_base_importa_csv_y_crea_auxiliares(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "alumnos.csv").write_text(
        "id_alumno,nombre\n1,Ana\n2,Luis\n", encoding="utf-8"
    )
    db_path = tmp_path / "demo.db"

    crear_base(db_path=db_path, data_dir=data_dir)

    assert db_path.exists()
    conexion = sqlite3.connect(db_path)
    try:
        tablas = {
            fila[0]
            for fila in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "alumnos" in tablas
        assert "consultas_log" in tablas
        assert "carreras" in tablas
        total = conexion.execute("SELECT COUNT(*) FROM alumnos").fetchone()[0]
        assert total == 2
    finally:
        conexion.close()
