"""Genera una base SQLite demo a partir de los CSV locales (propuesta).

NO cambia el backend de la aplicación (que sigue usando CSV). Sirve como base
para una eventual migración; ver docs/arquitectura_datos.md.

Uso:
    python scripts/crear_sqlite_demo.py
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import DATA_DIR  # noqa: E402

DB_PATH_DEFECTO = DATA_DIR / "asistente_academico_demo.db"

# Mapeo tabla -> archivo CSV de origen.
IMPORTS = {
    "alumnos": "alumnos.csv",
    "ramos": "malla.csv",
    "inscripciones": "ramos_inscritos.csv",
    "historial": "historial_academico.csv",
    "prerrequisitos": "prerrequisitos.csv",
    "document_chunks": "document_chunks.csv",
}

# Tablas auxiliares sin CSV de origen (se crean vacías).
DDL_AUXILIARES = [
    "CREATE TABLE IF NOT EXISTS carreras (id INTEGER PRIMARY KEY, nombre TEXT)",
    (
        "CREATE TABLE IF NOT EXISTS consultas_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, intencion TEXT, "
        "codigo_ramo TEXT, motor TEXT, tuvo_evidencia INTEGER)"
    ),
]


def crear_base(db_path=None, data_dir=None):
    """Crea la base SQLite demo importando los CSV existentes.

    Es idempotente: reemplaza las tablas importadas y crea las auxiliares si no
    existen. Devuelve la ruta de la base generada.
    """
    db_path = Path(db_path) if db_path else DB_PATH_DEFECTO
    data_dir = Path(data_dir) if data_dir else DATA_DIR
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conexion = sqlite3.connect(db_path)
    try:
        for tabla, archivo in IMPORTS.items():
            ruta = data_dir / archivo
            if ruta.exists() and ruta.stat().st_size > 0:
                df = pd.read_csv(ruta)
                df.to_sql(tabla, conexion, if_exists="replace", index=False)
                print(f"[OK] {archivo} -> tabla '{tabla}' ({len(df)} filas)")
            else:
                print(f"[AVISO] {archivo} no encontrado; se omite la tabla '{tabla}'.")

        cursor = conexion.cursor()
        for ddl in DDL_AUXILIARES:
            cursor.execute(ddl)
        conexion.commit()
        print("[OK] Tablas auxiliares listas (carreras, consultas_log).")
    finally:
        conexion.close()

    print(f"Base SQLite demo generada en: {db_path}")
    print("Nota: la aplicación sigue usando los CSV; esta base es solo una propuesta.")
    return db_path


if __name__ == "__main__":
    crear_base()
