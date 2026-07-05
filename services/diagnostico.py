"""Diagnóstico de solo lectura de los archivos de datos y assets."""

import pandas as pd

from config.settings import DATA_DIR, ESQUEMAS, LOGO_UDLA, LOGO_UDLA_FINE


def diagnosticar_datos(data_dir=None, esquemas=None):
    """Revisa cada CSV esperado: presencia, filas y columnas faltantes.

    No modifica archivos. Devuelve una lista de dicts, uno por archivo esperado.
    """
    data_dir = data_dir or DATA_DIR
    esquemas = esquemas if esquemas is not None else ESQUEMAS
    filas = []
    for nombre, columnas in esquemas.items():
        ruta = data_dir / nombre
        existe = ruta.exists() and ruta.stat().st_size > 0
        columnas_faltantes = []
        n_filas = 0
        if existe:
            try:
                df = pd.read_csv(ruta)
                n_filas = len(df)
                columnas_faltantes = sorted(set(columnas) - set(df.columns))
            except Exception:
                existe = False
        filas.append(
            {
                "archivo": nombre,
                "existe": bool(existe),
                "filas": int(n_filas),
                "columnas_faltantes": columnas_faltantes,
            }
        )
    return filas


def diagnosticar_assets(assets=None):
    """Revisa la presencia de los assets institucionales (logos)."""
    assets = assets if assets is not None else (LOGO_UDLA, LOGO_UDLA_FINE)
    return [{"asset": ruta.name, "existe": ruta.exists()} for ruta in assets]
