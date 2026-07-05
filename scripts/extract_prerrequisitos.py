"""Extrae prerrequisitos curriculares desde los fragmentos de programas PDF.

El extractor es deliberadamente conservador: solo genera relaciones hacia ramos
que existen en data/malla.csv y nunca infiere dependencias por semestre, nombre
parecido o posición en la malla.
"""

import re
import unicodedata
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
CHUNKS_PATH = BASE_DIR / "data" / "document_chunks.csv"
MALLA_PATH = BASE_DIR / "data" / "malla.csv"
OUTPUT_PATH = BASE_DIR / "data" / "prerrequisitos.csv"

COLUMNAS_CHUNKS = {"codigo_ramo", "ruta_archivo", "texto"}
COLUMNAS_MALLA = {"codigo_ramo", "nombre_ramo"}
COLUMNAS_SALIDA = [
    "codigo_ramo",
    "nombre_ramo",
    "codigo_prerrequisito",
    "nombre_prerrequisito",
    "tipo",
    "fuente_archivo",
    "evidencia_textual",
    "confianza",
]

PATRON_CLAVE = re.compile(
    r"\b(?:pre[\s-]?requisitos?|requisitos?(?:\s+acad[eé]micos?)?|"
    r"asignatura\s+previa|requisitos?\s+de\s+la\s+asignatura)\b",
    flags=re.IGNORECASE,
)
PATRON_FIN_CAMPO = re.compile(
    r"\bDISTRIBUCI[ÓO]N\s+DE\s+HORAS(?:\s+TOTALES)?(?:\s+DE\s+LA\s+ASIGNATURA)?\b",
    flags=re.IGNORECASE,
)
PATRON_SIN_REQUISITO = re.compile(
    r"\b(?:sin\s+(?:pre[\s-]?)?requisitos?|no\s+(?:requiere|aplica)|ninguno|ninguna)\b",
    flags=re.IGNORECASE,
)


def normalizar_espacios(texto):
    return " ".join(str(texto).replace("\x00", " ").split())


def normalizar_busqueda(texto):
    texto = unicodedata.normalize("NFKD", str(texto).casefold())
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return " ".join(texto.split())


def leer_csv_validado(ruta, columnas_requeridas, descripcion):
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {descripcion}: {ruta}")
    try:
        df = pd.read_csv(ruta)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"{descripcion} está vacío: {ruta}") from exc
    except Exception as exc:
        raise ValueError(f"No se pudo leer {descripcion}: {ruta}. {exc}") from exc

    faltantes = sorted(columnas_requeridas - set(df.columns))
    if faltantes:
        raise ValueError(
            f"{descripcion} no contiene las columnas requeridas: {', '.join(faltantes)}"
        )
    if df.empty:
        raise ValueError(f"{descripcion} no contiene registros: {ruta}")
    return df


def construir_evidencia(etiqueta, campo, limite=280):
    """Evidencia centrada en el campo de requisito (etiqueta + valor).

    Se descarta el texto anterior a la palabra clave, que solía arrastrar el
    encabezado administrativo del PDF (``E-SUPPORT``, ``Régimen``, jornadas) y
    no aportaba respaldo real de la relación de prerrequisito.
    """
    etiqueta = normalizar_espacios(etiqueta).strip(" :-–—;,.()")
    campo = normalizar_espacios(campo).strip(" :-–—;,.()")
    if not campo:
        return etiqueta
    evidencia = f"{etiqueta}: {campo}" if etiqueta else campo
    return evidencia[:limite].strip()


def extraer_bloques_requisito(fragmentos):
    """Devuelve bloques candidatos priorizando el campo formal del encabezado."""
    bloques = []
    for _, fila in fragmentos.iterrows():
        texto = normalizar_espacios(fila["texto"])
        for coincidencia in PATRON_CLAVE.finditer(texto):
            etiqueta = coincidencia.group(0)
            fin = PATRON_FIN_CAMPO.search(texto, coincidencia.end())
            if fin:
                campo = texto[coincidencia.end() : fin.start()].strip(" :-–—;,.()")
                bloques.append(
                    {
                        "campo": campo,
                        "evidencia": construir_evidencia(etiqueta, campo),
                        "fuente_archivo": str(fila["ruta_archivo"]),
                        "campo_formal": True,
                    }
                )
            else:
                campo = texto[coincidencia.end() : coincidencia.end() + 420].strip()
                bloques.append(
                    {
                        "campo": campo,
                        "evidencia": construir_evidencia(etiqueta, campo),
                        "fuente_archivo": str(fila["ruta_archivo"]),
                        "campo_formal": False,
                    }
                )

    # Los encabezados formales son más confiables; entre duplicados por solapamiento
    # se prefiere el bloque más corto porque suele contener el campo completo y limpio.
    return sorted(
        bloques,
        key=lambda bloque: (
            not bloque["campo_formal"],
            len(bloque["campo"]),
            bloque["evidencia"],
        ),
    )


def patron_codigo(codigo):
    codigo_limpio = re.sub(r"[^A-Za-z0-9]", "", str(codigo)).upper()
    coincidencia = re.fullmatch(r"([A-Z]+)(\d+)", codigo_limpio)
    if not coincidencia:
        return re.compile(rf"(?<![A-Z0-9]){re.escape(codigo_limpio)}(?![A-Z0-9])")
    letras, numeros = coincidencia.groups()
    return re.compile(
        rf"(?<![A-Z0-9]){re.escape(letras)}[\s-]?{re.escape(numeros)}(?![A-Z0-9])",
        flags=re.IGNORECASE,
    )


def detectar_candidatos(campo, malla, codigo_actual):
    candidatos = {}
    for _, ramo in malla.iterrows():
        codigo = str(ramo["codigo_ramo"]).strip()
        nombre = str(ramo["nombre_ramo"]).strip()
        if codigo == codigo_actual:
            continue

        if patron_codigo(codigo).search(campo):
            candidatos[codigo] = {
                "codigo": codigo,
                "nombre": nombre,
                "confianza": "Alta",
                "metodo": "código oficial",
            }
            continue

        nombre_normalizado = normalizar_busqueda(nombre)
        campo_normalizado = normalizar_busqueda(campo)
        if nombre_normalizado and re.search(
            rf"(?<!\w){re.escape(nombre_normalizado)}(?!\w)", campo_normalizado
        ):
            candidatos[codigo] = {
                "codigo": codigo,
                "nombre": nombre,
                "confianza": "Media",
                "metodo": "nombre oficial",
            }

    return sorted(candidatos.values(), key=lambda candidato: candidato["codigo"])


def fila_sin_relacion(ramo, tipo, fuente, evidencia, confianza):
    return {
        "codigo_ramo": ramo["codigo_ramo"],
        "nombre_ramo": ramo["nombre_ramo"],
        "codigo_prerrequisito": "",
        "nombre_prerrequisito": "",
        "tipo": tipo,
        "fuente_archivo": fuente,
        "evidencia_textual": evidencia,
        "confianza": confianza,
    }


def extraer_prerrequisitos(chunks, malla):
    registros = []
    for _, ramo in malla.iterrows():
        codigo_actual = str(ramo["codigo_ramo"]).strip()
        nombre_actual = str(ramo["nombre_ramo"]).strip()
        ramo_limpio = {"codigo_ramo": codigo_actual, "nombre_ramo": nombre_actual}
        fragmentos = chunks[
            chunks["codigo_ramo"].astype(str).str.strip() == codigo_actual
        ]

        if fragmentos.empty:
            registros.append(
                fila_sin_relacion(
                    ramo_limpio,
                    "No detectado",
                    "",
                    "No hay fragmentos documentales asociados al ramo.",
                    "No aplica",
                )
            )
            continue

        bloques = extraer_bloques_requisito(fragmentos)
        if not bloques:
            registros.append(
                fila_sin_relacion(
                    ramo_limpio,
                    "No detectado",
                    str(fragmentos.iloc[0]["ruta_archivo"]),
                    "No se encontró un campo de prerrequisitos en los fragmentos indexados.",
                    "No aplica",
                )
            )
            continue

        bloque = bloques[0]
        campo = bloque["campo"]
        evidencia = bloque["evidencia"]
        fuente = bloque["fuente_archivo"]

        if not campo or PATRON_SIN_REQUISITO.search(campo):
            registros.append(
                fila_sin_relacion(
                    ramo_limpio,
                    "Sin prerrequisito",
                    fuente,
                    evidencia,
                    "Alta" if bloque["campo_formal"] else "Media",
                )
            )
            continue

        candidatos = detectar_candidatos(campo, malla, codigo_actual)
        if not candidatos:
            registros.append(
                fila_sin_relacion(
                    ramo_limpio,
                    "No detectado",
                    fuente,
                    evidencia,
                    "No aplica",
                )
            )
            continue

        for candidato in candidatos:
            registros.append(
                {
                    "codigo_ramo": codigo_actual,
                    "nombre_ramo": nombre_actual,
                    "codigo_prerrequisito": candidato["codigo"],
                    "nombre_prerrequisito": candidato["nombre"],
                    "tipo": "Prerrequisito",
                    "fuente_archivo": fuente,
                    "evidencia_textual": evidencia,
                    "confianza": candidato["confianza"],
                }
            )

    return pd.DataFrame(registros, columns=COLUMNAS_SALIDA)


def imprimir_resumen(resultado, total_ramos):
    con_prerrequisito = resultado.loc[
        resultado["tipo"] == "Prerrequisito", "codigo_ramo"
    ].nunique()
    sin_prerrequisito = resultado.loc[
        resultado["tipo"] == "Sin prerrequisito", "codigo_ramo"
    ].nunique()
    no_detectados = resultado.loc[
        resultado["tipo"] == "No detectado", "codigo_ramo"
    ].nunique()
    baja_confianza = len(
        resultado[
            (resultado["tipo"] == "Prerrequisito")
            & (resultado["confianza"] == "Baja")
        ]
    )

    print("\nResumen de extracción")
    print("---------------------")
    print(f"Total de ramos analizados: {total_ramos}")
    print(f"Ramos con prerrequisito detectado: {con_prerrequisito}")
    print(f"Ramos sin prerrequisito explícito: {sin_prerrequisito}")
    print(f"Ramos no detectados: {no_detectados}")
    print(f"Candidatos de baja confianza: {baja_confianza}")
    print(f"Filas generadas: {len(resultado)}")
    print(f"Archivo generado: {OUTPUT_PATH}")


def main():
    try:
        chunks = leer_csv_validado(
            CHUNKS_PATH, COLUMNAS_CHUNKS, "data/document_chunks.csv"
        )
        malla = leer_csv_validado(MALLA_PATH, COLUMNAS_MALLA, "data/malla.csv")
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR | {exc}")
        return 1

    malla = malla[["codigo_ramo", "nombre_ramo"]].drop_duplicates("codigo_ramo")
    resultado = extraer_prerrequisitos(chunks, malla)

    if resultado.empty:
        print("ERROR | No se generaron resultados; el archivo existente no será sobrescrito.")
        return 1

    temporal = OUTPUT_PATH.with_suffix(".csv.tmp")
    resultado.to_csv(temporal, index=False, encoding="utf-8-sig")
    temporal.replace(OUTPUT_PATH)
    imprimir_resumen(resultado, len(malla))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
