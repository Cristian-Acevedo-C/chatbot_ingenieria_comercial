"""Carga y consulta de los CSV locales."""

import pandas as pd
import streamlit as st

from config.settings import DATA_DIR, ESQUEMAS


def cargar_csv(nombre, columnas_requeridas=(), permitir_vacio=False):
    ruta = DATA_DIR / nombre
    if not ruta.exists():
        if permitir_vacio:
            return pd.DataFrame()
        raise FileNotFoundError(f"No se encontró {ruta}")

    if ruta.stat().st_size == 0:
        if permitir_vacio:
            return pd.DataFrame()
        raise ValueError(f"El archivo {nombre} está vacío.")

    try:
        df = pd.read_csv(ruta)
    except pd.errors.EmptyDataError:
        if permitir_vacio:
            return pd.DataFrame()
        raise ValueError(f"El archivo {nombre} no contiene columnas ni registros.")
    except Exception as exc:
        raise ValueError(f"No se pudo leer {nombre}: {exc}") from exc

    faltantes = sorted(set(columnas_requeridas) - set(df.columns))
    if faltantes:
        raise ValueError(f"{nombre} no contiene las columnas: {', '.join(faltantes)}")
    return df


@st.cache_data(show_spinner=False)
def cargar_datos():
    alumnos = cargar_csv("alumnos.csv", ESQUEMAS["alumnos.csv"])
    malla = cargar_csv("malla.csv", ESQUEMAS["malla.csv"])
    inscritos = cargar_csv("ramos_inscritos.csv", ESQUEMAS["ramos_inscritos.csv"])
    historial = cargar_csv("historial_academico.csv", ESQUEMAS["historial_academico.csv"])
    chunks = cargar_csv("document_chunks.csv", ESQUEMAS["document_chunks.csv"])
    prerrequisitos = cargar_csv(
        "prerrequisitos.csv",
        ESQUEMAS["prerrequisitos.csv"],
        permitir_vacio=True,
    )
    return alumnos, malla, inscritos, historial, chunks, prerrequisitos



def buscar_alumno(alumnos, id_alumno):
    coincidencias = alumnos[alumnos["id_alumno"].astype(str) == str(id_alumno)]
    return None if coincidencias.empty else coincidencias.iloc[0]


def filtrar_por_alumno(df, id_alumno):
    if df.empty:
        return pd.DataFrame(columns=df.columns)
    return df[df["id_alumno"].astype(str) == str(id_alumno)].copy()


def valor_texto(valor):
    return "" if pd.isna(valor) else str(valor).strip()


