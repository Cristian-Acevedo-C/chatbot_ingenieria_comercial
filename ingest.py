"""Ingesta local de programas UDLA, separada por carrera."""

import argparse
import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent
DOCS_PATH = BASE_DIR / "data" / "documentos_ramos.csv"
MALLAS_PATH = BASE_DIR / "data" / "documentos_malla.csv"
OUTPUT_PATH = BASE_DIR / "data" / "document_chunks.csv"
CARRERAS_PATH = BASE_DIR / "data" / "carreras"
CARRERA_COMERCIAL = "Ingeniería Comercial"

COLUMNAS_RAMOS = {
    "codigo_ramo",
    "nombre_ramo",
    "semestre",
    "tipo_documento",
    "ruta_archivo",
}
COLUMNAS_MALLAS = {"tipo_documento", "nombre_documento", "ruta_archivo"}
COLUMNAS_METADATA_CARRERA = {
    "carrera",
    "codigo_asignatura",
    "nombre_archivo",
    "ruta_archivo",
    "tipo_documento",
    "estado",
}


def leer_csv_validado(ruta, columnas_requeridas, descripcion):
    """Lee un manifiesto y entrega errores accionables si está incompleto."""
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el archivo de {descripcion}: {ruta}")

    try:
        df = pd.read_csv(ruta)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"El archivo de {descripcion} está vacío: {ruta}") from exc
    except Exception as exc:
        raise ValueError(
            f"No se pudo leer el archivo de {descripcion}: {ruta}. {exc}"
        ) from exc

    faltantes = sorted(columnas_requeridas - set(df.columns))
    if faltantes:
        raise ValueError(
            f"El archivo de {descripcion} no contiene las columnas requeridas: "
            f"{', '.join(faltantes)}"
        )
    if df.empty:
        raise ValueError(f"El archivo de {descripcion} no contiene registros: {ruta}")

    return df


def extraer_texto_pdf(ruta_pdf):
    try:
        reader = PdfReader(ruta_pdf)
    except Exception as exc:
        print(f"ERROR | No se pudo abrir el PDF: {ruta_pdf}")
        print(f"        {type(exc).__name__}: {exc}")
        return ""

    paginas = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text()
        except Exception as exc:
            print(f"ADVERTENCIA | No se pudo extraer la página {i} de {ruta_pdf}: {exc}")
            continue

        if page_text and page_text.strip():
            paginas.append(f"[Página {i}]\n{page_text.strip()}")

    return "\n\n".join(paginas).strip()


def dividir_texto(texto, tamano=1500, solapamiento=250):
    return [
        item["texto"]
        for item in dividir_texto_con_metadata(texto, tamano, solapamiento)
    ]


def dividir_texto_con_metadata(texto, tamano=1500, solapamiento=250):
    """Divide por caracteres y conserva una página aproximada por fragmento."""
    if tamano <= 0 or solapamiento < 0 or solapamiento >= tamano:
        raise ValueError("El tamaño debe ser positivo y el solapamiento menor al tamaño.")

    texto = texto.replace("\x00", " ").strip()
    marcadores = [
        (coincidencia.start(), int(coincidencia.group(1)))
        for coincidencia in re.finditer(r"\[Página\s+(\d+)\]", texto)
    ]
    chunks = []
    inicio = 0

    while inicio < len(texto):
        fin = min(inicio + tamano, len(texto))
        chunk = texto[inicio:fin].strip()
        pagina = None

        for posicion, numero_pagina in marcadores:
            if posicion > inicio:
                break
            pagina = numero_pagina

        if pagina is None:
            pagina = next(
                (numero for posicion, numero in marcadores if inicio < posicion < fin),
                None,
            )

        if chunk:
            chunks.append({"texto": chunk, "pagina_aproximada": pagina})

        inicio += tamano - solapamiento

    return chunks


def cargar_documentos_ramos():
    df = leer_csv_validado(DOCS_PATH, COLUMNAS_RAMOS, "documentos de ramos")
    print(f"Documentos de ramos cargados desde CSV: {len(df)}")
    columnas_ordenadas = [
        "codigo_ramo",
        "nombre_ramo",
        "semestre",
        "tipo_documento",
        "ruta_archivo",
    ]
    documentos = df[columnas_ordenadas].to_dict("records")
    for documento in documentos:
        documento["carrera"] = CARRERA_COMERCIAL
    return documentos


def cargar_documentos_malla():
    df = leer_csv_validado(MALLAS_PATH, COLUMNAS_MALLAS, "documentos de malla")
    print(f"Documentos de malla cargados desde CSV: {len(df)}")
    documentos = []
    for row in df.to_dict("records"):
        documentos.append(
            {
                "carrera": CARRERA_COMERCIAL,
                "codigo_ramo": "MALLA",
                "nombre_ramo": row["nombre_documento"],
                "semestre": 0,
                "tipo_documento": row["tipo_documento"],
                "ruta_archivo": row["ruta_archivo"],
            }
        )
    return documentos


def buscar_metadata_carrera(slug_carrera):
    """Ubica el manifiesto de programas de una carrera sin fijar su sigla."""
    directorio = CARRERAS_PATH / slug_carrera / "metadata"
    preferido = directorio / "metadata_programas.csv"
    if preferido.exists():
        return preferido

    candidatos = sorted(directorio.glob("*programas*.csv"))
    if len(candidatos) == 1:
        return candidatos[0]
    if not candidatos:
        raise FileNotFoundError(
            f"No existe metadata de programas para la carrera '{slug_carrera}' en "
            f"{directorio}"
        )
    raise ValueError(
        f"Hay más de un manifiesto de programas en {directorio}; "
        "renombra el activo como metadata_programas.csv."
    )


def cargar_documentos_carrera(slug_carrera):
    """Carga solo programas disponibles; los pendientes permanecen en metadata."""
    ruta_metadata = buscar_metadata_carrera(slug_carrera)
    df = leer_csv_validado(
        ruta_metadata,
        COLUMNAS_METADATA_CARRERA,
        f"programas de la carrera {slug_carrera}",
    )
    carreras = df["carrera"].dropna().astype(str).str.strip().unique()
    if len(carreras) != 1:
        raise ValueError(
            f"La metadata {ruta_metadata} debe contener exactamente una carrera."
        )

    estados = df["estado"].fillna("").astype(str).str.strip().str.lower()
    invalidos = sorted(set(estados) - {"disponible", "pendiente"})
    if invalidos:
        raise ValueError(
            "La columna estado solo admite 'disponible' o 'pendiente': "
            + ", ".join(invalidos)
        )

    documentos = []
    for fila in df.loc[estados.eq("disponible")].to_dict("records"):
        codigo = str(fila["codigo_asignatura"]).strip().upper()
        documentos.append(
            {
                "carrera": str(fila["carrera"]).strip(),
                "codigo_ramo": codigo,
                "nombre_ramo": codigo,
                "semestre": "",
                "tipo_documento": str(fila["tipo_documento"]).strip(),
                "ruta_archivo": str(fila["ruta_archivo"]).strip(),
            }
        )

    print(
        f"Programas disponibles para {carreras[0]}: {len(documentos)} | "
        f"pendientes: {int(estados.eq('pendiente').sum())}"
    )
    return documentos, carreras[0]


def construir_chunk_id(codigo_ramo, ruta_archivo, indice, carrera=None):
    nombre_archivo = Path(str(ruta_archivo)).stem
    nombre_seguro = re.sub(r"[^A-Za-z0-9]+", "_", nombre_archivo).strip("_")
    codigo_seguro = re.sub(r"[^A-Za-z0-9]+", "_", str(codigo_ramo)).strip("_")
    prefijo = ""
    if carrera:
        carrera_segura = re.sub(r"[^A-Za-z0-9]+", "_", str(carrera)).strip("_")
        prefijo = f"{carrera_segura}_"
    return f"{prefijo}{codigo_seguro}_{nombre_seguro}_{indice:04d}"


def construir_fuente_legible(doc):
    archivo = Path(str(doc["ruta_archivo"])).name
    return f"{doc['nombre_ramo']} ({doc['codigo_ramo']}) — {archivo}"


def extraer_nombre_asignatura(texto, codigo):
    """Extrae el nombre declarado en el PDF sin inferirlo desde el código."""
    texto_plano = " ".join(str(texto).split())
    patrones = (
        rf"PROGRAMA DE ASIGNATURA:\s*(.+?)\s*-\s*{re.escape(codigo)}\b",
        rf"Programa:\s*{re.escape(codigo)}\s+(.+?)\s+Versión:",
        rf"Sigla\s+{re.escape(codigo)}\s+Nombre\s+(.+?)\s+Créditos Totales",
    )
    for patron in patrones:
        coincidencia = re.search(patron, texto_plano, flags=re.IGNORECASE)
        if coincidencia:
            nombre = coincidencia.group(1).strip(" .–—-")
            if nombre:
                return nombre[:180]
    return str(codigo)


def procesar_documentos(documentos, output_path):
    """Extrae y fragmenta documentos; escribe únicamente si obtuvo registros."""
    print(f"Total documentos a procesar: {len(documentos)}")
    registros = []
    documentos_sin_texto = []

    for doc in documentos:
        ruta_relativa = Path(str(doc["ruta_archivo"]))
        ruta_abs = (BASE_DIR / ruta_relativa).resolve()

        if not ruta_abs.exists():
            print(f"ADVERTENCIA | PDF no encontrado: {doc['ruta_archivo']}")
            continue

        texto = extraer_texto_pdf(ruta_abs)
        if not texto:
            documentos_sin_texto.append(doc["ruta_archivo"])
            print(
                "ADVERTENCIA | PDF sin texto extraíble; se omite y la ingesta continúa: "
                f"{doc['ruta_archivo']}"
            )
            continue

        if doc["nombre_ramo"] == doc["codigo_ramo"]:
            doc = dict(doc)
            doc["nombre_ramo"] = extraer_nombre_asignatura(
                texto, doc["codigo_ramo"]
            )

        chunks = dividir_texto_con_metadata(texto)
        for i, chunk in enumerate(chunks):
            registros.append(
                {
                    "chunk_id": construir_chunk_id(
                        doc["codigo_ramo"],
                        doc["ruta_archivo"],
                        i,
                        doc.get("carrera"),
                    ),
                    "carrera": doc.get("carrera", CARRERA_COMERCIAL),
                    "codigo_ramo": doc["codigo_ramo"],
                    "nombre_ramo": doc["nombre_ramo"],
                    "semestre": doc["semestre"],
                    "tipo_documento": doc["tipo_documento"],
                    "ruta_archivo": doc["ruta_archivo"],
                    "fuente_legible": construir_fuente_legible(doc),
                    "pagina_aproximada": chunk["pagina_aproximada"],
                    "texto": chunk["texto"],
                }
            )

        print(
            f"Procesado: {doc['codigo_ramo']} | {doc['nombre_ramo']} | "
            f"fragmentos: {len(chunks)}"
        )

    if not registros:
        print("ERROR | No se generaron fragmentos. El CSV existente no será sobrescrito.")
        return 1

    salida = pd.DataFrame(registros)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(output_path, index=False, encoding="utf-8-sig")

    print()
    print(f"Base creada correctamente: {output_path}")
    print(f"Total fragmentos generados: {len(registros)}")
    print(f"Documentos sin texto extraíble: {len(documentos_sin_texto)}")
    for ruta in documentos_sin_texto:
        print(f"  - {ruta}")
    return 0


def main(slug_carrera=None):
    try:
        if slug_carrera:
            documentos, _carrera = cargar_documentos_carrera(slug_carrera)
            output_path = (
                CARRERAS_PATH / slug_carrera / "indice" / "document_chunks.csv"
            )
        else:
            documentos = cargar_documentos_malla() + cargar_documentos_ramos()
            output_path = OUTPUT_PATH
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR DE CONFIGURACIÓN | {exc}")
        return 1
    return procesar_documentos(documentos, output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconstruye un corpus documental local.")
    parser.add_argument(
        "--carrera",
        help=(
            "Slug bajo data/carreras/ (por ejemplo, "
            "ingenieria_civil_industrial). Si se omite, reconstruye Comercial."
        ),
    )
    argumentos = parser.parse_args()
    raise SystemExit(main(argumentos.carrera))
