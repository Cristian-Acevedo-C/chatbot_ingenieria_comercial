"""Carga y consulta de los CSV locales."""

from datetime import datetime

import pandas as pd
import streamlit as st

from config.settings import DATA_DIR, ESQUEMAS

CARRERA_COMERCIAL = "Ingeniería Comercial"
CARRERAS_DIR = DATA_DIR / "carreras"


def cargar_csv(nombre, columnas_requeridas=(), permitir_vacio=False):
    ruta = DATA_DIR / nombre
    if not ruta.exists():
        if permitir_vacio:
            return pd.DataFrame()
        raise FileNotFoundError(
            f"No se encontró el archivo de datos '{nombre}' en {DATA_DIR}. "
            "Verifica que la carpeta data/ esté completa o regenera las bases "
            "locales (ver README: «Regenerar las bases locales»)."
        )

    if ruta.stat().st_size == 0:
        if permitir_vacio:
            return pd.DataFrame()
        raise ValueError(
            f"El archivo '{nombre}' está vacío. Restaura una copia válida o "
            "regenera las bases locales."
        )

    try:
        df = pd.read_csv(ruta)
    except pd.errors.EmptyDataError:
        if permitir_vacio:
            return pd.DataFrame()
        raise ValueError(
            f"El archivo '{nombre}' no contiene columnas ni registros."
        )
    except Exception as exc:
        raise ValueError(f"No se pudo leer '{nombre}': {exc}") from exc

    faltantes = sorted(set(columnas_requeridas) - set(df.columns))
    if faltantes:
        raise ValueError(
            f"El archivo '{nombre}' no contiene las columnas requeridas: "
            f"{', '.join(faltantes)}. Columnas encontradas: "
            f"{', '.join(map(str, df.columns)) or '(ninguna)'}."
        )
    return df


def cargar_chunks_documentales():
    """Combina corpora por carrera conservando sus límites documentales."""
    comercial = cargar_csv("document_chunks.csv", ESQUEMAS["document_chunks.csv"])
    if "carrera" not in comercial.columns:
        comercial = comercial.assign(carrera=CARRERA_COMERCIAL)

    corpora = [comercial]
    for ruta in sorted(CARRERAS_DIR.glob("*/indice/document_chunks.csv")):
        try:
            carrera = pd.read_csv(ruta)
        except Exception as exc:
            raise ValueError(f"No se pudo leer el índice de carrera '{ruta}': {exc}") from exc
        requeridas = set(ESQUEMAS["document_chunks.csv"]) | {"carrera"}
        faltantes = sorted(requeridas - set(carrera.columns))
        if faltantes:
            raise ValueError(
                f"El índice de carrera '{ruta}' no contiene las columnas requeridas: "
                f"{', '.join(faltantes)}."
            )
        corpora.append(carrera)

    return pd.concat(corpora, ignore_index=True, sort=False)


def cargar_dataset_academico(nombre):
    """Combina el dataset histórico de Comercial con archivos separados por carrera."""
    base = cargar_csv(nombre, ESQUEMAS[nombre])
    if "carrera" not in base.columns:
        base = base.assign(carrera=CARRERA_COMERCIAL)

    datasets = [base]
    for ruta in sorted(CARRERAS_DIR.glob(f"*/academico/{nombre}")):
        try:
            carrera = pd.read_csv(ruta)
        except Exception as exc:
            raise ValueError(
                f"No se pudo leer el dataset académico de carrera '{ruta}': {exc}"
            ) from exc
        requeridas = set(ESQUEMAS[nombre]) | {"carrera"}
        faltantes = sorted(requeridas - set(carrera.columns))
        if faltantes:
            raise ValueError(
                f"El dataset académico '{ruta}' no contiene las columnas requeridas: "
                f"{', '.join(faltantes)}."
            )
        datasets.append(carrera)

    return pd.concat(datasets, ignore_index=True, sort=False)


def filtrar_chunks_por_carrera(chunks, carrera):
    """Aplica el límite de seguridad usado antes de indexar y buscar."""
    if chunks.empty or "carrera" not in chunks.columns:
        return pd.DataFrame(columns=chunks.columns)
    return chunks[
        chunks["carrera"].fillna("").astype(str).eq(str(carrera))
    ].reset_index(drop=True)


def filtrar_por_carrera(df, carrera):
    """Filtra cualquier dataset académico usando la carrera seleccionada."""
    if df.empty or "carrera" not in df.columns:
        return pd.DataFrame(columns=df.columns)
    return df[df["carrera"].fillna("").astype(str).eq(str(carrera))].reset_index(
        drop=True
    )


def listar_carreras_disponibles(chunks):
    """Carreras con base documental cargada, Comercial primero.

    Única fuente de verdad para la lista de carreras: la usan tanto el
    selector de la barra lateral como la capa conversacional básica, para no
    duplicar (ni desalinear) la lista en dos lugares distintos.
    """
    carreras = (
        sorted(chunks["carrera"].dropna().astype(str).unique())
        if chunks is not None and not chunks.empty and "carrera" in chunks.columns
        else [CARRERA_COMERCIAL]
    )
    if CARRERA_COMERCIAL in carreras:
        carreras.remove(CARRERA_COMERCIAL)
        carreras.insert(0, CARRERA_COMERCIAL)
    return carreras or [CARRERA_COMERCIAL]


def obtener_programas_pendientes(carrera):
    """Códigos con metadata registrada pero sin PDF/chunks indexados.

    Recorre los mismos manifiestos de ``metadata/*programas*.csv`` que usa
    ``construir_catalogo_documental``. No infiere nada: solo refleja lo que el
    manifiesto de la carrera declara con ``estado == 'pendiente'``.
    """
    pendientes = []
    for ruta in sorted(CARRERAS_DIR.glob("*/metadata/*programas*.csv")):
        try:
            metadata = pd.read_csv(ruta)
        except Exception:
            continue
        requeridas = {"carrera", "codigo_asignatura", "estado"}
        if not requeridas.issubset(metadata.columns):
            continue
        filas = metadata[
            metadata["carrera"].fillna("").astype(str).eq(str(carrera))
            & metadata["estado"].fillna("").astype(str).eq("pendiente")
        ]
        pendientes.extend(filas["codigo_asignatura"].astype(str).tolist())
    return pendientes


def obtener_fecha_metadata(carrera):
    """Fecha de modificación del manifiesto de metadata de la carrera, si existe.

    Es la única fuente real disponible para "última actualización"; si la
    carrera no tiene manifiesto propio (p. ej. Comercial), devuelve ``None`` en
    vez de inventar una fecha.
    """
    for ruta in sorted(CARRERAS_DIR.glob("*/metadata/*programas*.csv")):
        try:
            metadata = pd.read_csv(ruta, usecols=lambda columna: columna == "carrera")
        except Exception:
            continue
        if "carrera" not in metadata.columns:
            continue
        if metadata["carrera"].fillna("").astype(str).eq(str(carrera)).any():
            return datetime.fromtimestamp(ruta.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    return None


def construir_catalogo_documental(malla, chunks, carrera):
    """Catálogo para detectar ramos, incluidos aquellos con PDF pendiente."""
    partes = []
    if not malla.empty:
        partes.append(malla[["codigo_ramo", "nombre_ramo", "semestre"]].copy())

    chunks_carrera = filtrar_chunks_por_carrera(chunks, carrera)
    if not chunks_carrera.empty:
        catalogo_chunks = chunks_carrera[["codigo_ramo", "nombre_ramo"]].drop_duplicates()
        catalogo_chunks = catalogo_chunks.assign(semestre="")
        partes.append(catalogo_chunks)

    for ruta in sorted(CARRERAS_DIR.glob("*/metadata/*programas*.csv")):
        try:
            metadata = pd.read_csv(ruta)
        except Exception:
            continue
        requeridas = {"carrera", "codigo_asignatura", "estado"}
        if not requeridas.issubset(metadata.columns):
            continue
        filas = metadata[
            metadata["carrera"].fillna("").astype(str).eq(str(carrera))
        ]
        if filas.empty:
            continue
        catalogo_metadata = pd.DataFrame(
            {
                "codigo_ramo": filas["codigo_asignatura"].astype(str),
                # Si no hay PDF, el código es la única denominación comprobable.
                "nombre_ramo": filas["codigo_asignatura"].astype(str),
                "semestre": "",
            }
        )
        partes.append(catalogo_metadata)

    if not partes:
        return pd.DataFrame(columns=["codigo_ramo", "nombre_ramo", "semestre"])

    catalogo = pd.concat(partes, ignore_index=True)
    # Los nombres extraídos de los PDF van antes que el fallback basado en código.
    catalogo["_es_fallback"] = catalogo["codigo_ramo"].astype(str).eq(
        catalogo["nombre_ramo"].astype(str)
    )
    return (
        catalogo.sort_values("_es_fallback")
        .drop_duplicates("codigo_ramo", keep="first")
        .drop(columns="_es_fallback")
        .reset_index(drop=True)
    )


@st.cache_data(show_spinner=False)
def cargar_datos():
    alumnos = cargar_dataset_academico("alumnos.csv")
    malla = cargar_dataset_academico("malla.csv")
    inscritos = cargar_dataset_academico("ramos_inscritos.csv")
    historial = cargar_dataset_academico("historial_academico.csv")
    chunks = cargar_chunks_documentales()
    prerrequisitos = cargar_dataset_academico("prerrequisitos.csv")
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


