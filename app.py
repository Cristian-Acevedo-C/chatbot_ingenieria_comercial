import random
import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
LOGO_UDLA = ASSETS_DIR / "logo_udla.png"
LOGO_UDLA_FINE = ASSETS_DIR / "logo_udla_fine.png"
UMBRAL_SIMILITUD = 0.05
TOP_K = 4

STOPWORDS_ES = {
    "a", "al", "algo", "como", "con", "cual", "cuando", "de", "del", "desde",
    "donde", "el", "ella", "en", "es", "esta", "este", "hay", "hoy", "la", "las", "lo",
    "los", "mi", "mis", "o", "para", "por", "que", "quien", "se", "si", "sin",
    "sobre", "su", "sus", "un", "una", "uno", "y", "ya",
}

PREGUNTAS_RAPIDAS = [
    "¿Qué ramos tengo inscritos?",
    "¿Cuál es mi sede y jornada?",
    "¿Estoy atrasado o tengo alguna alerta?",
    "¿Qué dice el programa de Marketing Estratégico?",
    "¿Qué debería estudiar para Microeconomía I?",
    "¿Qué dice el programa de Datos y Decisiones?",
    "¿Tengo prerrequisitos pendientes?",
    "¿Qué prerrequisitos tiene Microeconomía II?",
    "¿Puedo cursar Econometría?",
]

ESQUEMAS = {
    "alumnos.csv": {"id_alumno", "nombre", "carrera", "sede", "jornada", "semestre_actual"},
    "malla.csv": {"codigo_ramo", "nombre_ramo", "semestre"},
    "ramos_inscritos.csv": {"id_alumno", "codigo_ramo", "nombre_ramo", "estado"},
    "historial_academico.csv": {"id_alumno", "codigo_ramo", "nombre_ramo", "estado", "nota"},
    "document_chunks.csv": {
        "chunk_id",
        "codigo_ramo",
        "nombre_ramo",
        "ruta_archivo",
        "texto",
    },
    "prerrequisitos.csv": {
        "codigo_ramo",
        "nombre_ramo",
        "codigo_prerrequisito",
        "nombre_prerrequisito",
        "tipo",
        "fuente_archivo",
        "evidencia_textual",
        "confianza",
    },
}


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return re.sub(r"\s+", " ", texto).strip()


@st.cache_data(show_spinner=False)
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


@st.cache_resource(show_spinner="Preparando el índice documental local...")
def construir_indice_tfidf(textos):
    textos = list(textos)
    if not textos or not any(texto.strip() for texto in textos):
        return None, None

    vectorizador = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        max_features=20000,
        sublinear_tf=True,
        stop_words=sorted(STOPWORDS_ES),
    )
    matriz = vectorizador.fit_transform(textos)
    return vectorizador, matriz


def buscar_alumno(alumnos, id_alumno):
    coincidencias = alumnos[alumnos["id_alumno"].astype(str) == str(id_alumno)]
    return None if coincidencias.empty else coincidencias.iloc[0]


def filtrar_por_alumno(df, id_alumno):
    if df.empty:
        return pd.DataFrame(columns=df.columns)
    return df[df["id_alumno"].astype(str) == str(id_alumno)].copy()


def valor_texto(valor):
    return "" if pd.isna(valor) else str(valor).strip()


def preparar_mapa_prerrequisitos(prerrequisitos, malla):
    if prerrequisitos.empty:
        return pd.DataFrame(columns=[*prerrequisitos.columns, "semestre"])
    semestres = malla[["codigo_ramo", "semestre"]].copy()
    semestres["codigo_ramo"] = semestres["codigo_ramo"].astype(str)
    mapa = prerrequisitos.copy()
    mapa["codigo_ramo"] = mapa["codigo_ramo"].astype(str)
    return mapa.merge(semestres, on="codigo_ramo", how="left", validate="many_to_one")


def obtener_estado_prerrequisito(historial, codigo_prerrequisito, tipo):
    tipo_normalizado = normalizar(tipo)
    if tipo_normalizado in {"sin prerrequisito", "no detectado"}:
        return "No aplica"
    if not codigo_prerrequisito or historial.empty:
        return "Pendiente"

    registros = historial[
        historial["codigo_ramo"].astype(str) == str(codigo_prerrequisito)
    ]
    if registros.empty:
        return "Pendiente"

    estados = set(registros["estado"].fillna("").astype(str).map(normalizar))
    if "aprobado" in estados:
        return "Aprobado"
    if "cursando" in estados:
        return "Cursando"
    if "reprobado" in estados:
        return "Reprobado"
    return "Pendiente"


def obtener_alerta_prerrequisito(estado, tipo):
    if normalizar(tipo) == "no detectado":
        return "Información incompleta"
    return {
        "Aprobado": "OK",
        "No aplica": "OK",
        "Reprobado": "Riesgo alto",
        "Cursando": "Riesgo medio",
        "Pendiente": "Pendiente",
    }.get(estado, "Pendiente")


def construir_prerrequisitos_alumno(ramos, historial, prerrequisitos):
    columnas = [
        "codigo_ramo",
        "nombre_ramo",
        "codigo_prerrequisito",
        "nombre_prerrequisito",
        "tipo",
        "estado_prerrequisito",
        "alerta",
        "fuente_archivo",
        "evidencia_textual",
        "confianza",
    ]
    if ramos.empty or prerrequisitos.empty:
        return pd.DataFrame(columns=columnas)

    registros = []
    for _, ramo in ramos.iterrows():
        codigo_ramo = str(ramo["codigo_ramo"])
        relaciones = prerrequisitos[
            prerrequisitos["codigo_ramo"].astype(str) == codigo_ramo
        ]
        if relaciones.empty:
            relaciones = pd.DataFrame(
                [
                    {
                        "codigo_ramo": codigo_ramo,
                        "nombre_ramo": ramo["nombre_ramo"],
                        "codigo_prerrequisito": "",
                        "nombre_prerrequisito": "",
                        "tipo": "No detectado",
                        "fuente_archivo": "",
                        "evidencia_textual": "No existe una fila para este ramo en prerrequisitos.csv.",
                        "confianza": "No aplica",
                    }
                ]
            )

        for _, relacion in relaciones.iterrows():
            tipo = valor_texto(relacion.get("tipo"))
            codigo_prerrequisito = valor_texto(relacion.get("codigo_prerrequisito"))
            estado = obtener_estado_prerrequisito(
                historial, codigo_prerrequisito, tipo
            )
            registros.append(
                {
                    "codigo_ramo": codigo_ramo,
                    "nombre_ramo": str(ramo["nombre_ramo"]),
                    "codigo_prerrequisito": codigo_prerrequisito,
                    "nombre_prerrequisito": valor_texto(
                        relacion.get("nombre_prerrequisito")
                    ),
                    "tipo": tipo,
                    "estado_prerrequisito": estado,
                    "alerta": obtener_alerta_prerrequisito(estado, tipo),
                    "fuente_archivo": valor_texto(relacion.get("fuente_archivo")),
                    "evidencia_textual": valor_texto(
                        relacion.get("evidencia_textual")
                    ),
                    "confianza": valor_texto(relacion.get("confianza")),
                }
            )

    return pd.DataFrame(registros, columns=columnas)


def calcular_metricas_prerrequisitos(prerrequisitos):
    if prerrequisitos.empty:
        return {
            "analizados": 0,
            "con_prerrequisito": 0,
            "sin_prerrequisito": 0,
            "no_detectados": 0,
            "relaciones": 0,
        }
    return {
        "analizados": prerrequisitos["codigo_ramo"].nunique(),
        "con_prerrequisito": prerrequisitos.loc[
            prerrequisitos["tipo"] == "Prerrequisito", "codigo_ramo"
        ].nunique(),
        "sin_prerrequisito": prerrequisitos.loc[
            prerrequisitos["tipo"] == "Sin prerrequisito", "codigo_ramo"
        ].nunique(),
        "no_detectados": prerrequisitos.loc[
            prerrequisitos["tipo"] == "No detectado", "codigo_ramo"
        ].nunique(),
        "relaciones": int((prerrequisitos["tipo"] == "Prerrequisito").sum()),
    }


def detectar_ramo(malla, pregunta):
    if malla.empty:
        return None, None

    pregunta_normalizada = normalizar(pregunta)
    for _, ramo in malla.iterrows():
        codigo = str(ramo["codigo_ramo"])
        nombre = str(ramo["nombre_ramo"])
        if re.search(rf"\b{re.escape(normalizar(codigo))}\b", pregunta_normalizada):
            return codigo, nombre
        nombre_normalizado = normalizar(nombre)
        if re.search(rf"(?<!\w){re.escape(nombre_normalizado)}(?!\w)", pregunta_normalizada):
            return codigo, nombre

    mejor_ramo = None
    mejor_score = 0
    palabras_pregunta = set(re.findall(r"[a-z0-9]+", pregunta_normalizada))
    for _, ramo in malla.iterrows():
        palabras_ramo = {
            palabra
            for palabra in re.findall(r"[a-z0-9]+", normalizar(ramo["nombre_ramo"]))
            if len(palabra) >= 5
        }
        score = len(palabras_ramo & palabras_pregunta)
        if score > mejor_score:
            mejor_score = score
            mejor_ramo = ramo

    if mejor_ramo is not None and mejor_score > 0:
        return str(mejor_ramo["codigo_ramo"]), str(mejor_ramo["nombre_ramo"])
    return None, None


def buscar_documentos(
    chunks,
    pregunta,
    vectorizador,
    matriz,
    codigo_ramo=None,
    top_k=TOP_K,
    umbral=UMBRAL_SIMILITUD,
):
    if chunks.empty or vectorizador is None or matriz is None or not pregunta.strip():
        return pd.DataFrame()

    if codigo_ramo:
        posiciones = chunks.index[
            chunks["codigo_ramo"].astype(str) == str(codigo_ramo)
        ].to_numpy()
    else:
        posiciones = chunks.index.to_numpy()

    if len(posiciones) == 0:
        return pd.DataFrame()

    consulta = vectorizador.transform([pregunta])
    terminos_minimos = 1 if codigo_ramo else 2
    if consulta.nnz < terminos_minimos:
        return pd.DataFrame()

    similitudes = cosine_similarity(consulta, matriz[posiciones]).ravel()
    orden_local = similitudes.argsort()[::-1]
    seleccion = [indice for indice in orden_local if similitudes[indice] >= umbral][:top_k]
    if not seleccion:
        return pd.DataFrame()

    posiciones_finales = posiciones[seleccion]
    resultados = chunks.iloc[posiciones_finales].copy()
    resultados["score"] = [float(similitudes[indice]) for indice in seleccion]
    return resultados.reset_index(drop=True)


def limpiar_fragmento(texto, limite=850):
    fragmento = " ".join(str(texto).replace("\n", " ").split())
    return fragmento if len(fragmento) <= limite else fragmento[:limite].rstrip() + "..."


def pagina_fragmento(fila):
    if "pagina_aproximada" in fila.index and pd.notna(fila["pagina_aproximada"]):
        return str(int(float(fila["pagina_aproximada"])))
    coincidencia = re.search(r"\[Página\s+(\d+)\]", str(fila["texto"]))
    return coincidencia.group(1) if coincidencia else None


def fuente_fragmento(fila):
    if "fuente_legible" in fila.index and pd.notna(fila["fuente_legible"]):
        fuente = str(fila["fuente_legible"])
    else:
        fuente = f"{fila['nombre_ramo']} — {fila['ruta_archivo']}"
    pagina = pagina_fragmento(fila)
    return f"{fuente}, página aproximada {pagina}" if pagina else fuente


def detectar_tipo_pregunta(pregunta):
    texto = normalizar(pregunta)
    if "prerrequisit" in texto or "pre-requisit" in texto:
        return "prerrequisitos"
    if "bibliograf" in texto or "libros" in texto or "lecturas" in texto:
        return "bibliografia"
    if "evaluacion" in texto or "evaluaciones" in texto or "como se evalua" in texto:
        return "evaluaciones"
    if any(frase in texto for frase in ("que deberia estudiar", "que estudiar", "como estudiar")):
        return "estudio"
    if any(palabra in texto for palabra in ("contenidos", "unidades", "temas")):
        return "contenidos"
    return "documental"


def reconstruir_texto_ramo(chunks, codigo_ramo):
    filas = chunks[chunks["codigo_ramo"].astype(str) == str(codigo_ramo)].copy()
    if filas.empty:
        return ""
    filas["_orden"] = pd.to_numeric(
        filas["chunk_id"].astype(str).str.extract(r"_(\d+)$")[0],
        errors="coerce",
    ).fillna(0)
    textos = filas.sort_values("_orden")["texto"].fillna("").astype(str).tolist()
    reconstruido = textos[0]
    for texto in textos[1:]:
        solapamiento = 0
        maximo = min(350, len(reconstruido), len(texto))
        for largo in range(maximo, 19, -1):
            if reconstruido[-largo:] == texto[:largo]:
                solapamiento = largo
                break
        reconstruido += " " + texto[solapamiento:]
    return colapsar_repeticiones_largas(reconstruido)


def colapsar_repeticiones_largas(texto):
    """Elimina bloques largos repetidos de forma consecutiva tras el empalme.

    El solapamiento entre fragmentos puede dejar una misma frase pegada dos veces
    seguidas; esto la colapsa sin alterar el resto del programa (Bug 1).
    """
    return re.sub(r"(.{25,}?)\s+\1(?=\s|$)", r"\1", str(texto))


def limpiar_texto_programa(texto):
    texto = re.sub(
        r"\[Página\s+\d+\]\s*Publicado por:.*?Página:\s*\d+\s+de\s+\d+",
        " ",
        str(texto),
        flags=re.IGNORECASE | re.DOTALL,
    )
    return " ".join(texto.replace("\x00", " ").split())


def extraer_seccion(texto, patron_inicio, patron_fin):
    inicio = re.search(patron_inicio, texto, flags=re.IGNORECASE)
    if not inicio:
        return ""
    fin = re.search(patron_fin, texto[inicio.end() :], flags=re.IGNORECASE)
    limite = inicio.end() + fin.start() if fin else min(len(texto), inicio.end() + 7000)
    return texto[inicio.end() : limite].strip()


RUIDO_UNIDAD = {
    "clase", "clases", "columna", "columnas", "tema", "temas",
    "unidad", "unidades", "contenido", "contenidos",
}


def colapsar_frase_duplicada(texto):
    """Colapsa títulos que la plantilla PDF repite (``X. X.`` o ``X X``)."""
    texto = normalizar_espacios_academicos(texto)
    if not texto:
        return texto

    def _clave(parte):
        # Ignora enumeradores iniciales (``I.-``, ``1.``) al comparar mitades.
        return normalizar(re.sub(r"^[ivxlc\d]+\s*[.\-)]+\s*", "", parte, flags=re.IGNORECASE))

    partes = [parte.strip(" .") for parte in re.split(r"\.\s+", texto) if parte.strip(" .")]
    if len(partes) >= 2 and _clave(partes[0]) and _clave(partes[0]) == _clave(partes[1]):
        return partes[0]

    palabras = texto.split()
    total = len(palabras)
    norma = [normalizar(palabra) for palabra in palabras]
    # Busca el mayor corte donde la cola repite (total o parcialmente) la cabeza;
    # tolera que la última palabra de la cola sea un prefijo truncado del PDF.
    for corte in range((total + 1) // 2, 0, -1):
        cabeza, cola = norma[:corte], norma[corte:]
        if not cola or len(cola) > corte or len(cola) < max(2, corte // 2):
            continue
        cuerpo_igual = all(cola[i] == cabeza[i] for i in range(len(cola) - 1))
        ultimo_igual = cabeza[len(cola) - 1].startswith(cola[-1])
        if cuerpo_igual and ultimo_igual:
            return " ".join(palabras[:corte])
    return texto


def depurar_nombre_unidad(nombre):
    """Colapsa duplicados, quita enumeradores iniciales y recorta prosa larga.

    Los títulos cortos y limpios (la mayoría) pasan intactos: el recorte por
    "prosa" solo actúa sobre nombres largos (>70) típicos del formato
    ``Trabajo Personal`` o de programas con sub-ítems numerados.
    """
    nombre = colapsar_frase_duplicada(nombre)
    nombre = re.sub(
        r"^(?:de\s+|del\s+|[ivxlc\d]+\s*[.\-)]+\s*)+", "", nombre, flags=re.IGNORECASE
    ).strip()
    if len(nombre) > 70:
        corte = re.search(r"\s\d+\.(?:\d+)?\s|:\s|(?<=\.)\s+(?=[A-ZÁÉÍÓÚÑ])", nombre)
        if corte:
            nombre = nombre[: corte.start()]
    nombre = colapsar_frase_duplicada(nombre)
    return nombre[:120].strip(" .:-–—;,")


def nombre_unidad_valido(nombre):
    """Evita ``unidades`` basura como ``clases`` o ``columnas`` (ver Bug 2)."""
    normalizado = normalizar(nombre)
    if len(normalizado) < 4 or not re.search(r"[a-z]{4,}", normalizado):
        return False
    palabras = [palabra for palabra in re.findall(r"[a-z]+", normalizado) if len(palabra) > 2]
    if palabras and all(palabra in RUIDO_UNIDAD for palabra in palabras):
        return False
    return True


def seccion_contenidos_catedra(seccion):
    """Prepara el bloque de contenidos: quita ``(N clases)`` y el encabezado.

    Si el bloque de cátedra (5.1) no contiene el encabezado ``N° Unidad Tema``
    —por ejemplo cuando el programa solo trae ``5.2 Trabajo Personal``— se usa
    la sección completa en lugar de descartarla.
    """
    seccion = re.sub(r"\(\s*\d+\s*clases?\s*\)", " ", seccion, flags=re.IGNORECASE)
    candidato = re.split(r"5\.2\s*Contenido", seccion, maxsplit=1, flags=re.IGNORECASE)[0]
    if not re.search(r"N[°º]?\s*Unidad\s+Tema", candidato, flags=re.IGNORECASE):
        candidato = seccion
    return re.sub(
        r"^.*?N[°º]?\s*Unidad\s+Tema", "", candidato, count=1, flags=re.IGNORECASE
    ).strip()


def _fila_contenido(numero, nombre_unidad, temas):
    temas_limpios = [
        tema
        for tema in temas
        if normalizar(tema) != normalizar(nombre_unidad) and 2 < len(tema) <= 180
    ]
    return {
        "Unidad": f"Unidad {numero}",
        "Tema principal": nombre_unidad,
        "Qué repasar": "; ".join(temas_limpios[:5]) or nombre_unidad,
    }


def extraer_contenidos_desde_texto(texto):
    texto_limpio = limpiar_texto_programa(texto)
    seccion = extraer_seccion(
        texto_limpio,
        r"5\.\s*CONTENIDOS?(?:,\s*ACTIVIDADES\s+Y\s+ACTITUDES)?",
        r"6\.\s*ESTRATEGIAS?\s+METODOL[ÓO]GICAS?",
    )
    if not seccion:
        return []
    seccion_catedra = seccion_contenidos_catedra(seccion)

    # El límite alto (240) permite capturar títulos que el PDF duplica; luego se
    # colapsan con ``colapsar_frase_duplicada`` (Bug 1).
    patron_unidad = re.compile(r"(?<![\d.])(\d{1,2})\s+([^•]{2,240}?)\s*•")
    coincidencias = list(patron_unidad.finditer(seccion_catedra))
    contenidos = []
    unidades_vistas = set()
    for indice, coincidencia in enumerate(coincidencias):
        numero = int(coincidencia.group(1))
        if numero < 1 or numero > 20 or numero in unidades_vistas:
            continue
        siguiente = coincidencias[indice + 1].start() if indice + 1 < len(coincidencias) else len(seccion_catedra)
        nombre_unidad = depurar_nombre_unidad(coincidencia.group(2))
        if not nombre_unidad_valido(nombre_unidad):
            continue
        bloque_temas = seccion_catedra[coincidencia.end() : siguiente]
        temas = [
            colapsar_frase_duplicada(tema)
            for tema in re.split(r"\s*•\s*", bloque_temas)
            if normalizar_espacios_academicos(tema)
        ]
        unidades_vistas.add(numero)
        contenidos.append(_fila_contenido(numero, nombre_unidad, temas))

    if not contenidos:
        return extraer_contenidos_fallback(seccion_catedra)
    return contenidos


def extraer_contenidos_fallback(seccion_catedra):
    """Fallback tolerante para programas sin viñetas ``•`` (sub-ítems numerados).

    Solo se usa cuando el parser principal no reconoce ninguna unidad. Divide por
    los números de unidad y toma como temas los sub-ítems ``1.1`` o los segmentos
    separados por punto. No infiere contenidos: si no hay estructura, no devuelve
    nada y la interfaz mostrará "Información no disponible".
    """
    if not seccion_catedra:
        return []
    marcadores = list(re.finditer(r"(?<![\d.])(\d{1,2})\s+(?=[A-ZÁÉÍÓÚÑ])", seccion_catedra))
    contenidos = []
    unidades_vistas = set()
    for indice, marcador in enumerate(marcadores):
        numero = int(marcador.group(1))
        if numero < 1 or numero > 20 or numero in unidades_vistas:
            continue
        fin = marcadores[indice + 1].start() if indice + 1 < len(marcadores) else len(seccion_catedra)
        bloque = seccion_catedra[marcador.end() : fin].strip()
        # El nombre va hasta el primer sub-ítem numerado, viñeta, dos puntos o
        # cambio de frase; así se evita arrastrar la descripción como título.
        corte = re.search(r"•|:\s|\s\d+\.(?:\d+)?\s+|(?<=\.)\s+(?=[A-ZÁÉÍÓÚÑ])", bloque)
        nombre_unidad = depurar_nombre_unidad(bloque[: corte.start()] if corte else bloque[:240])
        if not nombre_unidad_valido(nombre_unidad):
            continue
        resto = bloque[corte.start():] if corte else ""
        temas = [
            normalizar_espacios_academicos(tema)
            for tema in re.split(r"\s*•\s*|\s+\d+\.\d+\.?\s*|\.\s+(?=[A-ZÁÉÍÓÚÑ])", resto)
            if normalizar_espacios_academicos(tema)
        ]
        unidades_vistas.add(numero)
        contenidos.append(_fila_contenido(numero, nombre_unidad, temas))
    return contenidos


def normalizar_espacios_academicos(texto):
    texto = re.sub(r"\s+", " ", str(texto)).strip(" :-–—;,.()")
    return texto


def extraer_bibliografia_desde_texto(texto):
    texto_limpio = limpiar_texto_programa(texto)
    secciones = [
        (
            "Básica",
            extraer_seccion(
                texto_limpio,
                r"8\.1\s*BIBLIOGRAF[IÍ]A\s+B[ÁA]SICA",
                r"8\.2\s*BIBLIOGRAF[IÍ]A\s+COMPLEMENTARIA",
            ),
        ),
        (
            "Complementaria",
            extraer_seccion(
                texto_limpio,
                r"8\.2\s*BIBLIOGRAF[IÍ]A\s+COMPLEMENTARIA",
                r"8\.3\s*RECURSOS\s+INFORM[ÁA]TICOS",
            ),
        ),
    ]
    entradas = []
    patron = re.compile(
        r"([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚáéíóúÑñÜü.,' -]{2,100}?)\s+"
        r"((?:19|20)\d{2})\s+(.{3,180}?)(?=\s+[A-ZÁÉÍÓÚÑ]{3,}(?:\s|$))"
    )
    for tipo, seccion in secciones:
        if not seccion:
            continue
        seccion = re.sub(
            r"^.*?(?:LINK|ISBN)", "", seccion, count=1, flags=re.IGNORECASE
        ).strip()
        for coincidencia in patron.finditer(seccion):
            autor = normalizar_espacios_academicos(coincidencia.group(1))
            titulo = normalizar_espacios_academicos(coincidencia.group(3))
            if len(autor) > 100 or len(titulo) > 180:
                continue
            entrada = {
                "Tipo": tipo,
                "Autor": autor,
                "Año": coincidencia.group(2),
                "Título": titulo,
            }
            if entrada not in entradas:
                entradas.append(entrada)
    return entradas[:15]


def extraer_evaluaciones_desde_texto(texto):
    texto_limpio = limpiar_texto_programa(texto)
    seccion = extraer_seccion(
        texto_limpio,
        r"7\.\s*(?:EVALUACI[ÓO]N|ESTRATEGIA\s+EVALUATIVA)",
        r"8\.\s*RECURSOS\s+DE\s+APRENDIZAJE",
    )
    base = seccion or texto_limpio
    descripcion = re.search(
        r"La evaluaci[óo]n de la asignatura considera\s+(.{20,650}?)(?:\.\s|$)",
        base,
        flags=re.IGNORECASE,
    )
    evaluaciones = []
    texto_descripcion = descripcion.group(1) if descripcion else base
    patrones = [
        ("Cátedras", r"(\d+)\s+c[áa]tedras?"),
        ("Ejercicios", r"(\d+)\s+ejercicios?"),
        ("Examen final", r"(?:un|1)\s+examen\s+final"),
    ]
    for componente, patron in patrones:
        coincidencia = re.search(patron, texto_descripcion, flags=re.IGNORECASE)
        if not coincidencia:
            continue
        cantidad = coincidencia.group(1) if coincidencia.lastindex else "1"
        ponderacion = ""
        patron_porcentaje = re.search(
            rf"{re.escape(componente.split()[0])}\s+(\d+(?:[.,]\d+)?)",
            base,
            flags=re.IGNORECASE,
        )
        if patron_porcentaje:
            ponderacion = f"{patron_porcentaje.group(1)}%"
        evaluaciones.append(
            {
                "Componente": componente,
                "Cantidad detectada": cantidad,
                "Ponderación detectada": ponderacion or "No indicada",
            }
        )
    return evaluaciones


def construir_plan_estudio(contenidos):
    return [
        {
            "Prioridad": indice,
            "Acción de estudio": f"Repasar {contenido['Tema principal']}",
            "Motivo": f"Corresponde a {contenido['Unidad']} del programa cargado.",
        }
        for indice, contenido in enumerate(contenidos, start=1)
    ]


def seleccionar_evidencias(chunks, codigo_ramo, tipo, resultados=None):
    filas = chunks[chunks["codigo_ramo"].astype(str) == str(codigo_ramo)].copy()
    terminos = {
        "estudio": ("5. contenidos", "n° unidad", "unidad", "tema"),
        "contenidos": ("5. contenidos", "n° unidad", "unidad", "tema"),
        "bibliografia": (
            "8.1 bibliografía básica",
            "8.2 bibliografía complementaria",
            "bibliografía",
        ),
        "evaluaciones": (
            "7.2. estrategia evaluativa",
            "7.3. descripción de la estrategia evaluativa",
            "evaluación de la asignatura",
        ),
    }.get(tipo, ())
    seleccionadas = []
    if terminos:
        filas["_prioridad_evidencia"] = filas["texto"].fillna("").astype(str).map(
            lambda texto: sum(
                len(terminos) - indice
                for indice, termino in enumerate(terminos)
                if normalizar(termino) in normalizar(texto)
            )
        )
        filas = filas.sort_values("_prioridad_evidencia", ascending=False)
    for _, fila in filas.iterrows():
        texto_normalizado = normalizar(fila["texto"])
        if terminos and not any(normalizar(termino) in texto_normalizado for termino in terminos):
            continue
        seleccionadas.append(
            {
                "texto": limpiar_fragmento(fila["texto"], limite=500),
                "fuente": fuente_fragmento(fila),
            }
        )
        if len(seleccionadas) == 3:
            break
    if not seleccionadas and resultados is not None and not resultados.empty:
        for _, fila in resultados.head(3).iterrows():
            seleccionadas.append(
                {
                    "texto": limpiar_fragmento(fila["texto"], limite=500),
                    "fuente": fuente_fragmento(fila),
                }
            )
    return seleccionadas


def respuesta_sin_evidencia(nombre_ramo=None):
    contexto = f" para **{nombre_ramo}**" if nombre_ramo else ""
    return (
        "### Respuesta breve\n\n"
        f"No encontré evidencia documental suficientemente similar{contexto}.\n\n"
        "### Evidencia encontrada\n\n"
        "La búsqueda quedó bajo el umbral mínimo de similitud, por lo que no se muestran "
        "fragmentos potencialmente irrelevantes.\n\n"
        "### Recomendación de estudio\n\n"
        "Reformula la pregunta usando el código del ramo, su nombre completo o un tema específico.\n\n"
        "### Fuente consultada\n\n"
        "Base documental local `data/document_chunks.csv`."
    )


def respuesta_documental(resultados, nombre_ramo=None):
    if resultados.empty:
        return respuesta_sin_evidencia(nombre_ramo)
    contexto = f" sobre {nombre_ramo}" if nombre_ramo else " en la base documental"
    evidencias = [
        {
            "texto": limpiar_fragmento(fila["texto"], limite=500),
            "fuente": fuente_fragmento(fila),
        }
        for _, fila in resultados.head(3).iterrows()
    ]
    return {
        "formato": "academico",
        "tipo": "documental",
        "resumen": (
            f"Encontré evidencia pertinente{contexto} en los programas de asignatura "
            "cargados localmente. Revisa los extractos breves para precisar la consulta."
        ),
        "contenidos": [],
        "plan": [],
        "prerrequisitos": [],
        "bibliografia": [],
        "evaluaciones": [],
        "evidencias": evidencias,
    }


def construir_respuesta_academica(
    tipo,
    codigo,
    nombre,
    chunks,
    resultados,
    prerrequisitos,
    historial,
):
    texto_programa = reconstruir_texto_ramo(chunks, codigo)
    contenidos = extraer_contenidos_desde_texto(texto_programa)
    bibliografia = extraer_bibliografia_desde_texto(texto_programa)
    evaluaciones = extraer_evaluaciones_desde_texto(texto_programa)
    evidencias = seleccionar_evidencias(chunks, codigo, tipo, resultados)

    if tipo == "estudio":
        if contenidos:
            bloques = ", ".join(
                contenido["Tema principal"] for contenido in contenidos[:5]
            )
            resumen = (
                f"Para **{codigo} — {nombre}**, prioriza estos bloques del programa: "
                f"{bloques}. Avanza en el orden de las unidades y usa los temas detectados "
                "como lista de repaso."
            )
        else:
            resumen = (
                f"Encontré evidencia para **{codigo} — {nombre}**, pero no pude convertir "
                "la sección de contenidos en una tabla confiable."
            )
    elif tipo == "contenidos":
        resumen = (
            f"El programa de **{codigo} — {nombre}** contiene "
            f"**{len(contenidos)} unidades estructuradas**."
            if contenidos
            else f"No pude extraer una tabla limpia de contenidos para **{codigo} — {nombre}**."
        )
    elif tipo == "bibliografia":
        resumen = (
            f"Detecté **{len(bibliografia)} referencias bibliográficas** en el programa de "
            f"**{codigo} — {nombre}**."
            if bibliografia
            else f"No pude extraer referencias bibliográficas estructuradas para **{codigo} — {nombre}**."
        )
    else:
        resumen = (
            f"Detecté **{len(evaluaciones)} componentes de evaluación** en el programa de "
            f"**{codigo} — {nombre}**."
            if evaluaciones
            else f"No pude extraer una tabla limpia de evaluaciones para **{codigo} — {nombre}**."
        )

    vista_prerrequisitos = []
    if tipo == "estudio":
        ramo_objetivo = pd.DataFrame(
            [{"codigo_ramo": codigo, "nombre_ramo": nombre}]
        )
        vista_prerrequisitos = construir_prerrequisitos_alumno(
            ramo_objetivo, historial, prerrequisitos
        ).to_dict("records")

    return {
        "formato": "academico",
        "tipo": tipo,
        "codigo": codigo,
        "nombre": nombre,
        "resumen": resumen,
        "contenidos": contenidos if tipo in {"estudio", "contenidos"} else [],
        "plan": construir_plan_estudio(contenidos) if tipo == "estudio" else [],
        "prerrequisitos": vista_prerrequisitos,
        "bibliografia": bibliografia if tipo in {"estudio", "bibliografia"} else [],
        "evaluaciones": evaluaciones if tipo == "evaluaciones" else [],
        "evidencias": evidencias,
    }


def render_respuesta_academica(respuesta):
    if not isinstance(respuesta, dict) or respuesta.get("formato") != "academico":
        st.markdown(respuesta)
        return

    st.markdown("### Respuesta breve")
    st.markdown(respuesta["resumen"])
    tipo = respuesta["tipo"]

    if tipo in {"estudio", "contenidos"}:
        titulo = "Qué estudiar" if tipo == "estudio" else "Unidades y contenidos"
        st.markdown(f"### {titulo}")
        if respuesta["contenidos"]:
            st.dataframe(
                pd.DataFrame(respuesta["contenidos"]),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No fue posible formar una tabla limpia; consulta la evidencia del PDF.")

    if tipo == "estudio":
        st.markdown("### Plan sugerido")
        if respuesta["plan"]:
            st.dataframe(
                pd.DataFrame(respuesta["plan"]),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No se propone un plan porque no se detectaron contenidos estructurados.")

        st.markdown("### Prerrequisitos académicos")
        st.caption(
            "Los prerrequisitos ayudan a identificar qué conocimientos previos conviene "
            "reforzar antes de estudiar este ramo."
        )
        if respuesta["prerrequisitos"]:
            tabla_prerrequisitos = pd.DataFrame(respuesta["prerrequisitos"])[
                [
                    "codigo_prerrequisito",
                    "nombre_prerrequisito",
                    "tipo",
                    "estado_prerrequisito",
                    "alerta",
                ]
            ].rename(
                columns={
                    "codigo_prerrequisito": "Código",
                    "nombre_prerrequisito": "Ramo previo",
                    "tipo": "Tipo",
                    "estado_prerrequisito": "Estado",
                    "alerta": "Alerta",
                }
            )
            st.dataframe(tabla_prerrequisitos, width="stretch", hide_index=True)
        else:
            st.info("No hay prerrequisitos cargados para mostrar.")

    if respuesta["bibliografia"]:
        st.markdown("### Bibliografía")
        st.dataframe(
            pd.DataFrame(respuesta["bibliografia"]),
            width="stretch",
            hide_index=True,
        )
    elif tipo == "bibliografia":
        st.info("No fue posible formar una tabla bibliográfica limpia.")

    if tipo == "evaluaciones":
        st.markdown("### Evaluaciones detectadas")
        if respuesta["evaluaciones"]:
            st.dataframe(
                pd.DataFrame(respuesta["evaluaciones"]),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No fue posible formar una tabla limpia de evaluaciones.")

    with st.expander("Ver evidencia del PDF"):
        if respuesta["evidencias"]:
            for indice, evidencia in enumerate(respuesta["evidencias"], start=1):
                st.markdown(f"**Evidencia {indice}**")
                st.write(evidencia["texto"][:500])
                st.caption(evidencia["fuente"])
        else:
            st.info("No se encontraron extractos breves para mostrar.")


def respuesta_ramos(ramos):
    if ramos.empty:
        resumen = "No hay ramos inscritos registrados para el alumno seleccionado."
        evidencia = "El archivo de inscripciones no contiene filas asociadas a este alumno."
    else:
        resumen = f"El alumno tiene **{len(ramos)} ramos inscritos**."
        evidencia = "\n".join(
            f"- **{fila['codigo_ramo']}** — {fila['nombre_ramo']} ({fila['estado']})"
            for _, fila in ramos.iterrows()
        )
    return (
        f"### Respuesta breve\n\n{resumen}\n\n"
        f"### Evidencia encontrada\n\n{evidencia}\n\n"
        "### Recomendación de estudio\n\nPrioriza semanalmente los ramos con evaluaciones "
        "más próximas y reserva bloques de repaso para los cursos cuantitativos.\n\n"
        "### Fuente consultada\n\n`data/ramos_inscritos.csv`."
    )


def respuesta_datos_alumno(alumno):
    return (
        "### Respuesta breve\n\n"
        f"**{alumno['nombre']}** estudia en sede **{alumno['sede']}**, jornada "
        f"**{alumno['jornada']}**, y cursa el semestre **{alumno['semestre_actual']}**.\n\n"
        "### Evidencia encontrada\n\n"
        f"Carrera registrada: **{alumno['carrera']}**.\n\n"
        "### Recomendación de estudio\n\nOrganiza tu planificación según la jornada y los "
        "horarios oficiales informados por la institución.\n\n"
        "### Fuente consultada\n\n`data/alumnos.csv`."
    )


def respuesta_alertas(historial, prerrequisitos_alumno, prerrequisitos_cargados):
    if historial.empty:
        resumen = "No existe historial suficiente para calcular una alerta académica."
        evidencia = "No hay registros académicos asociados al alumno seleccionado."
        recomendacion = "Confirma o completa el historial antes de evaluar avance o riesgo."
    else:
        reprobados = historial[
            historial["estado"].astype(str).map(normalizar) == "reprobado"
        ]
        cantidad = len(reprobados)
        if cantidad == 0:
            resumen = "No se observan ramos reprobados en el historial disponible."
            evidencia = f"Se revisaron **{len(historial)} registros** y no hay reprobaciones."
            recomendacion = "Mantén seguimiento de notas y carga académica; esto no reemplaza una revisión oficial."
        else:
            resumen = f"Se detectaron **{cantidad} ramos reprobados** en el historial disponible."
            detalle = "\n".join(
                f"- **{fila['codigo_ramo']}** — {fila['nombre_ramo']} | Nota: {fila['nota']}"
                for _, fila in reprobados.iterrows()
            )
            evidencia = f"Cantidad de reprobaciones: **{cantidad}**.\n\n{detalle}"
            recomendacion = (
                "Prioriza los ramos reprobados y solicita orientación académica antes de definir "
                "la próxima carga. No es posible afirmar atraso curricular solo con estos datos."
            )

    if prerrequisitos_cargados.empty:
        evidencia += "\n\n**Prerrequisitos:** No hay prerrequisitos cargados."
        fuente_prerrequisitos = ""
    else:
        alertas = prerrequisitos_alumno[
            (prerrequisitos_alumno["tipo"] == "Prerrequisito")
            & (prerrequisitos_alumno["alerta"] != "OK")
        ]
        incompletos = prerrequisitos_alumno[
            prerrequisitos_alumno["tipo"] == "No detectado"
        ]
        if alertas.empty:
            evidencia += (
                "\n\n**Revisión de prerrequisitos:** no se detectaron relaciones "
                "incumplidas entre los ramos inscritos y el historial disponible."
            )
        else:
            detalle_alertas = "\n".join(
                f"- **{fila['codigo_ramo']}** requiere **{fila['codigo_prerrequisito']}** "
                f"({fila['estado_prerrequisito']}; {fila['alerta']})."
                for _, fila in alertas.iterrows()
            )
            evidencia += (
                f"\n\n**Alertas de prerrequisitos ({len(alertas)}):**\n\n"
                f"{detalle_alertas}"
            )
            recomendacion += (
                " Revisa estas relaciones con coordinación académica antes de mantener "
                "la inscripción correspondiente."
            )
        if not incompletos.empty:
            codigos = ", ".join(sorted(incompletos["codigo_ramo"].unique()))
            evidencia += (
                "\n\n**Advertencia informativa:** hay prerrequisitos no detectados para "
                f"{codigos}; no se infiere ninguna relación adicional."
            )
        fuente_prerrequisitos = " y `data/prerrequisitos.csv`"

    return (
        f"### Respuesta breve\n\n{resumen}\n\n"
        f"### Evidencia encontrada\n\n{evidencia}\n\n"
        f"### Recomendación de estudio\n\n{recomendacion}\n\n"
        f"### Fuente consultada\n\n`data/historial_academico.csv`{fuente_prerrequisitos}."
    )


def respuesta_todos_prerrequisitos(prerrequisitos):
    if prerrequisitos.empty:
        return respuesta_prerrequisitos_no_cargados()
    relaciones = prerrequisitos[prerrequisitos["tipo"] == "Prerrequisito"]
    detalle = "\n".join(
        f"- **{fila['codigo_ramo']} — {fila['nombre_ramo']}** requiere "
        f"**{fila['codigo_prerrequisito']} — {fila['nombre_prerrequisito']}**."
        for _, fila in relaciones.iterrows()
    )
    metricas = calcular_metricas_prerrequisitos(prerrequisitos)
    return (
        "### Respuesta breve\n\n"
        f"Hay **{metricas['relaciones']} relaciones** de prerrequisito para "
        f"**{metricas['con_prerrequisito']} ramos**.\n\n"
        f"### Evidencia encontrada\n\n{detalle}\n\n"
        "### Recomendación de estudio\n\nUsa el mapa como orientación y contrasta cada "
        "relación con la evidencia del programa de asignatura.\n\n"
        "### Fuente consultada\n\n`data/prerrequisitos.csv`."
    )


def respuesta_prerrequisitos_no_cargados():
    return (
        "### Respuesta breve\n\nNo hay prerrequisitos cargados.\n\n"
        "### Evidencia encontrada\n\nNo existe información utilizable en "
        "`data/prerrequisitos.csv`.\n\n"
        "### Recomendación de estudio\n\nEjecuta el extractor local antes de consultar "
        "relaciones curriculares.\n\n"
        "### Fuente consultada\n\n`data/prerrequisitos.csv`."
    )


def respuesta_prerrequisitos_ramo(prerrequisitos, codigo, nombre, historial=None):
    if prerrequisitos.empty:
        return respuesta_prerrequisitos_no_cargados()
    if not codigo:
        return (
            "### Respuesta breve\n\nNo pude identificar el ramo consultado.\n\n"
            "### Evidencia encontrada\n\nIndica el código o el nombre completo del ramo.\n\n"
            "### Recomendación de estudio\n\nPrueba, por ejemplo, `AEA315` o "
            "`Microeconomía II`.\n\n"
            "### Fuente consultada\n\n`data/malla.csv` y `data/prerrequisitos.csv`."
        )

    filas = prerrequisitos[
        prerrequisitos["codigo_ramo"].astype(str) == str(codigo)
    ]
    if filas.empty:
        return (
            f"### Respuesta breve\n\nNo hay información cargada para **{codigo} — {nombre}**.\n\n"
            "### Evidencia encontrada\n\nNo existe una fila asociada en el CSV.\n\n"
            "### Recomendación de estudio\n\nRevisa la cobertura del extractor.\n\n"
            "### Fuente consultada\n\n`data/prerrequisitos.csv`."
        )

    tipo = valor_texto(filas.iloc[0]["tipo"])
    historial = historial if historial is not None else pd.DataFrame()
    ramo_objetivo = pd.DataFrame(
        [{"codigo_ramo": codigo, "nombre_ramo": nombre}]
    )
    vista = construir_prerrequisitos_alumno(
        ramo_objetivo, historial, prerrequisitos
    )
    if tipo == "Sin prerrequisito":
        breve = f"**{codigo} — {nombre}** figura sin prerrequisito explícito."
        detalle = "El campo de requisito del programa está vacío. Estado: **No aplica (OK)**."
    elif tipo == "No detectado":
        breve = f"Los prerrequisitos de **{codigo} — {nombre}** no fueron detectados."
        detalle = (
            "La evidencia existe, pero no produjo una relación válida con la malla actual. "
            "Estado: **No aplica (Información incompleta)**."
        )
    else:
        breve = f"**{codigo} — {nombre}** tiene {len(filas)} prerrequisito(s) registrado(s)."
        detalle = "\n".join(
            f"- **{fila['codigo_prerrequisito']} — {fila['nombre_prerrequisito']}**: "
            f"{fila['estado_prerrequisito']} ({fila['alerta']}; confianza: "
            f"{fila['confianza']})."
            for _, fila in vista.iterrows()
        )

    evidencias = "\n".join(
        f"- {limpiar_fragmento(fila['evidencia_textual'], limite=420)}"
        for _, fila in filas.drop_duplicates("evidencia_textual").iterrows()
    )
    fuentes = "\n".join(
        f"- {fuente}"
        for fuente in filas["fuente_archivo"].dropna().astype(str).unique()
        if fuente
    )
    return (
        f"### Respuesta breve\n\n{breve}\n\n"
        f"### Evidencia encontrada\n\n{detalle}\n\n{evidencias}\n\n"
        "### Recomendación de estudio\n\nVerifica el cumplimiento en tu historial y "
        "confirma las alternativas del requisito con coordinación académica.\n\n"
        f"### Fuente consultada\n\n{fuentes or '`data/prerrequisitos.csv`.'}"
    )


def respuesta_ramos_por_tipo(prerrequisitos, tipo, descripcion):
    if prerrequisitos.empty:
        return respuesta_prerrequisitos_no_cargados()
    filas = prerrequisitos[prerrequisitos["tipo"] == tipo].drop_duplicates("codigo_ramo")
    detalle = "\n".join(
        f"- **{fila['codigo_ramo']} — {fila['nombre_ramo']}**"
        for _, fila in filas.iterrows()
    )
    return (
        f"### Respuesta breve\n\nHay **{len(filas)} ramos** {descripcion}.\n\n"
        f"### Evidencia encontrada\n\n{detalle or 'No se encontraron ramos.'}\n\n"
        "### Recomendación de estudio\n\nConsulta la evidencia textual del mapa antes "
        "de tomar decisiones académicas.\n\n"
        "### Fuente consultada\n\n`data/prerrequisitos.csv`."
    )


def respuesta_prerrequisitos_pendientes(prerrequisitos_alumno, prerrequisitos):
    if prerrequisitos.empty:
        return respuesta_prerrequisitos_no_cargados()
    alertas = prerrequisitos_alumno[
        (prerrequisitos_alumno["tipo"] == "Prerrequisito")
        & (prerrequisitos_alumno["alerta"] != "OK")
    ]
    incompletos = prerrequisitos_alumno[
        prerrequisitos_alumno["tipo"] == "No detectado"
    ]
    if alertas.empty:
        breve = "No se detectaron prerrequisitos pendientes en los ramos inscritos."
        detalle = "Todos los prerrequisitos registrados aparecen aprobados o no aplican."
    else:
        breve = f"Se detectaron **{len(alertas)} relaciones pendientes o en riesgo**."
        detalle = "\n".join(
            f"- **{fila['codigo_ramo']}** requiere **{fila['codigo_prerrequisito']}**: "
            f"{fila['estado_prerrequisito']} ({fila['alerta']})."
            for _, fila in alertas.iterrows()
        )
    if not incompletos.empty:
        detalle += (
            "\n\nInformación incompleta para: "
            + ", ".join(sorted(incompletos["codigo_ramo"].unique()))
            + "."
        )
    return (
        f"### Respuesta breve\n\n{breve}\n\n"
        f"### Evidencia encontrada\n\n{detalle}\n\n"
        "### Recomendación de estudio\n\nRegulariza primero los prerrequisitos reprobados "
        "o pendientes y confirma los casos incompletos con coordinación académica.\n\n"
        "### Fuente consultada\n\n`data/prerrequisitos.csv` y "
        "`data/historial_academico.csv`."
    )


def respuesta_puede_cursar(codigo, nombre, historial, prerrequisitos):
    if prerrequisitos.empty:
        return respuesta_prerrequisitos_no_cargados()
    if not codigo:
        return respuesta_prerrequisitos_ramo(
            prerrequisitos, codigo, nombre, historial
        )
    ramo = pd.DataFrame([{"codigo_ramo": codigo, "nombre_ramo": nombre}])
    vista = construir_prerrequisitos_alumno(ramo, historial, prerrequisitos)
    if vista.empty:
        return respuesta_prerrequisitos_ramo(
            prerrequisitos, codigo, nombre, historial
        )

    tipo = vista.iloc[0]["tipo"]
    if tipo == "Sin prerrequisito":
        breve = f"**{codigo} — {nombre}** no tiene prerrequisito explícito registrado."
        detalle = "Estado: No aplica (OK)."
    elif tipo == "No detectado":
        breve = f"No es posible evaluar **{codigo} — {nombre}** con información completa."
        detalle = "El CSV marca el requisito como No detectado; no se infieren relaciones."
    else:
        pendientes = vista[vista["alerta"] != "OK"]
        if pendientes.empty:
            breve = (
                f"Todos los prerrequisitos registrados para **{codigo} — {nombre}** "
                "figuran aprobados."
            )
        else:
            breve = (
                f"No se puede confirmar el cumplimiento de todos los prerrequisitos "
                f"registrados para **{codigo} — {nombre}**."
            )
        detalle = "\n".join(
            f"- **{fila['codigo_prerrequisito']} — {fila['nombre_prerrequisito']}**: "
            f"{fila['estado_prerrequisito']} ({fila['alerta']})."
            for _, fila in vista.iterrows()
        )
    return (
        f"### Respuesta breve\n\n{breve}\n\n"
        f"### Evidencia encontrada\n\n{detalle}\n\n"
        "### Recomendación de estudio\n\nEsta evaluación usa solo el historial y las "
        "relaciones extraídas; confirma la autorización formal con la universidad.\n\n"
        "### Fuente consultada\n\n`data/prerrequisitos.csv` y "
        "`data/historial_academico.csv`."
    )


def responder(
    pregunta,
    alumno,
    ramos,
    historial,
    prerrequisitos,
    malla,
    chunks,
    vectorizador,
    matriz,
    ramo_contexto=None,
):
    pregunta_normalizada = normalizar(pregunta)
    codigo, nombre = detectar_ramo(malla, pregunta)
    prerrequisitos_alumno = construir_prerrequisitos_alumno(
        ramos, historial, prerrequisitos
    )

    if "ramos" in pregunta_normalizada and (
        "inscrito" in pregunta_normalizada or "tengo" in pregunta_normalizada
    ):
        return respuesta_ramos(ramos)
    if "puedo cursar" in pregunta_normalizada:
        return respuesta_puede_cursar(codigo, nombre, historial, prerrequisitos)
    if "prerrequisit" in pregunta_normalizada:
        if "pendiente" in pregunta_normalizada and any(
            palabra in pregunta_normalizada for palabra in ("tengo", "mis")
        ):
            return respuesta_prerrequisitos_pendientes(
                prerrequisitos_alumno, prerrequisitos
            )
        if "no detectado" in pregunta_normalizada:
            return respuesta_ramos_por_tipo(
                prerrequisitos,
                "No detectado",
                "con prerrequisito no detectado",
            )
        if "no tienen" in pregunta_normalizada or "sin prerrequisito" in pregunta_normalizada:
            return respuesta_ramos_por_tipo(
                prerrequisitos,
                "Sin prerrequisito",
                "sin prerrequisito explícito",
            )
        if "todos" in pregunta_normalizada:
            return respuesta_todos_prerrequisitos(prerrequisitos)
        if codigo:
            return respuesta_prerrequisitos_ramo(
                prerrequisitos, codigo, nombre, historial
            )
        return respuesta_todos_prerrequisitos(prerrequisitos)
    if any(palabra in pregunta_normalizada for palabra in ("alerta", "atrasado", "riesgo", "reprobado")):
        return respuesta_alertas(
            historial, prerrequisitos_alumno, prerrequisitos
        )
    if any(palabra in pregunta_normalizada for palabra in ("sede", "jornada", "carrera", "semestre")):
        return respuesta_datos_alumno(alumno)

    if codigo is None and ramo_contexto:
        codigo = ramo_contexto["codigo_ramo"]
        nombre = ramo_contexto["nombre_ramo"]

    consulta = f"{pregunta} {nombre}" if nombre and normalizar(nombre) not in pregunta_normalizada else pregunta
    resultados = buscar_documentos(
        chunks,
        consulta,
        vectorizador,
        matriz,
        codigo_ramo=codigo,
    )
    tipo_pregunta = detectar_tipo_pregunta(pregunta)
    if codigo and tipo_pregunta in {
        "estudio",
        "contenidos",
        "bibliografia",
        "evaluaciones",
    }:
        return construir_respuesta_academica(
            tipo_pregunta,
            codigo,
            nombre,
            chunks,
            resultados,
            prerrequisitos,
            historial,
        )
    return respuesta_documental(resultados, nombre_ramo=nombre)


# --------------------------------------------------------------------------- #
# Capa conversacional guiada (solo durante la sesión, sin memoria permanente).
# Envuelve `responder()` sin alterar la lógica académica: agrega una frase de
# apertura, resuelve el ramo por contexto para preguntas de seguimiento y cierra
# con una pregunta de acompañamiento.
# --------------------------------------------------------------------------- #

APERTURAS = (
    "Perfecto, revisé la información disponible.",
    "Buena pregunta. Te lo resumo de forma clara.",
    "Claro, revisemos eso con los datos cargados.",
    "Qué bueno que lo preguntes, porque esto ayuda a planificar mejor.",
    "Entiendo. Vamos por partes.",
)

MENSAJES_SOCIALES = {
    "saludo": (
        "Hola, qué bueno verte por acá. Soy tu asistente académico. Puedo ayudarte a "
        "revisar tus ramos, qué estudiar, prerrequisitos, bibliografía o alertas "
        "académicas. ¿Qué quieres revisar primero?"
    ),
    "agradecimiento": (
        "De nada. Me alegra que te sirva. ¿Quieres revisar otro ramo o prefieres ver "
        "tus alertas académicas?"
    ),
    "confusion": (
        "Tranquilo, podemos ordenarlo paso a paso. Primero puedo revisar tus ramos "
        "inscritos y luego sugerirte cuál estudiar según contenidos, prerrequisitos y "
        "alertas. ¿Quieres que partamos por tus ramos inscritos?"
    ),
}

PREGUNTAS_CIERRE = {
    "estudio": "¿Quieres que ahora revise la bibliografía o los prerrequisitos de este ramo?",
    "contenidos": "¿Quieres que revise las evaluaciones o los prerrequisitos de este ramo?",
    "bibliografia": "¿Quieres que también te sugiera qué contenidos estudiar primero?",
    "evaluaciones": "¿Quieres que veamos qué contenidos conviene priorizar para esas evaluaciones?",
    "prerrequisitos": "¿Quieres que revise si tienes alguno pendiente según tu historial?",
    "puede_cursar": "¿Quieres que revise si tienes algún prerrequisito pendiente según tu historial?",
    "alertas": "¿Quieres que te muestre qué acción podrías tomar primero?",
    "ramos_inscritos": "¿Quieres que te recomiende cuál revisar primero?",
    "datos_alumno": "¿Quieres que revisemos tus ramos inscritos o tus alertas académicas?",
    "documental": "¿Quieres que lo veamos para un ramo específico? Indícame su nombre o código.",
    "recomendacion": "¿Quieres que abramos uno de esos ramos para ver qué estudiar?",
    "pedir_ramo": None,
}

SALUDOS = (
    "hola", "holi", "buenas", "buen dia", "buenos dias", "buenas tardes",
    "buenas noches", "que tal", "como estas", "como andas", "hey", "saludos",
)
AGRADECIMIENTOS = (
    "gracias", "muchas gracias", "mil gracias", "vale", "perfecto", "genial",
    "excelente", "buenisimo",
)
CONFUSION = (
    "estoy perdido", "estoy perdida", "no se que estudiar", "no entiendo",
    "no se por donde partir", "no se por donde empezar", "no se por donde comenzar",
    "no se por donde", "estoy confundido", "estoy confundida", "no se que hacer",
)
HINTS_ACADEMICOS = (
    "bibliograf", "contenido", "evaluacion", "prerrequisit", "estudiar", "estudio",
    "ramo", "cursar", "alerta", "inscrit", "sede", "jornada", "semestre", "malla",
)


def elegir_apertura():
    return random.choice(APERTURAS)


def detectar_intencion_social(pregunta):
    texto = normalizar(pregunta)
    if any(frase in texto for frase in CONFUSION):
        return "confusion"
    if any(hint in texto for hint in HINTS_ACADEMICOS):
        return None
    palabras = texto.split()
    if len(palabras) <= 5:
        if any(saludo in palabras for saludo in ("hola", "holi", "buenas", "hey", "saludos")) or any(
            texto == saludo or texto.startswith(saludo) for saludo in SALUDOS
        ):
            return "saludo"
        if any(gracias in palabras for gracias in ("gracias", "vale", "perfecto", "genial", "excelente")) or any(
            texto.startswith(agradecimiento) for agradecimiento in AGRADECIMIENTOS
        ):
            return "agradecimiento"
    return None


def es_recomendacion(pregunta):
    texto = normalizar(pregunta)
    return any(
        frase in texto
        for frase in (
            "cual reviso primero", "cual reviso", "que reviso primero", "que hago ahora",
            "por donde parto", "por donde empiezo", "por donde comienzo",
            "que estudio primero", "cual estudio primero", "cual me recomiendas",
            "cual priorizo",
        )
    )


def es_seguimiento_de_ramo(pregunta):
    texto = normalizar(pregunta)
    claves = (
        "bibliograf", "contenido", "evaluacion", "prerrequisit", "pre-requisit",
        "puedo cursar", "cursarlo", "que estudiar", "deberia estudiar", "que repaso",
    )
    if any(clave in texto for clave in claves):
        return True
    return bool(re.match(r"^y\s+(la|el|los|las|del|de)\b", texto))


def clasificar_intencion(pregunta, codigo):
    texto = normalizar(pregunta)
    if "ramos" in texto and ("inscrito" in texto or "tengo" in texto):
        return "ramos_inscritos"
    if "puedo cursar" in texto or "cursarlo" in texto or "lo puedo tomar" in texto:
        return "puede_cursar"
    if "prerrequisit" in texto or "pre-requisit" in texto:
        return "prerrequisitos"
    if any(palabra in texto for palabra in ("alerta", "atrasado", "riesgo", "reprobado")):
        return "alertas"
    if any(palabra in texto for palabra in ("sede", "jornada", "carrera", "semestre")):
        return "datos_alumno"
    if codigo:
        return detectar_tipo_pregunta(pregunta)
    return "documental"


def respuesta_pedir_ramo(opciones_ramos):
    disponibles = [etiqueta for etiqueta in opciones_ramos if etiqueta != "Todos los ramos"]
    lista = "\n".join(f"- {etiqueta}" for etiqueta in disponibles)
    return (
        "### Respuesta breve\n\n¿Sobre qué ramo quieres que revise esa información?\n\n"
        "### Ramos inscritos\n\n"
        f"{lista or 'No hay ramos inscritos registrados para este alumno.'}\n\n"
        "### Recomendación\n\nEscribe el nombre o el código del ramo y lo reviso enseguida.\n\n"
        "### Fuente consultada\n\n`data/ramos_inscritos.csv`."
    )


def respuesta_recomendacion(ramos, historial, prerrequisitos_alumno):
    if ramos.empty:
        return (
            "### Respuesta breve\n\nAún no hay ramos inscritos registrados para recomendar.\n\n"
            "### Recomendación de estudio\n\nCuando existan ramos inscritos podré sugerirte un orden.\n\n"
            "### Fuente consultada\n\n`data/ramos_inscritos.csv`."
        )
    riesgos = prerrequisitos_alumno[
        (prerrequisitos_alumno["tipo"] == "Prerrequisito")
        & (prerrequisitos_alumno["alerta"].isin(["Riesgo alto", "Riesgo medio", "Pendiente"]))
    ].copy()
    if not riesgos.empty:
        orden = {"Riesgo alto": 0, "Riesgo medio": 1, "Pendiente": 2}
        riesgos["_orden"] = riesgos["alerta"].map(orden).fillna(3)
        riesgos = riesgos.sort_values("_orden")
        top = riesgos.iloc[0]
        breve = (
            f"Te sugiero partir por **{top['codigo_ramo']} — {top['nombre_ramo']}**, porque su "
            f"prerrequisito **{top['codigo_prerrequisito']} — {top['nombre_prerrequisito']}** "
            f"figura como **{top['estado_prerrequisito']} ({top['alerta']})**."
        )
        detalle = "\n".join(
            f"- **{fila['codigo_ramo']} — {fila['nombre_ramo']}** depende de "
            f"**{fila['codigo_prerrequisito']}** ({fila['estado_prerrequisito']}; {fila['alerta']})."
            for _, fila in riesgos.iterrows()
        )
        fuente = "`data/prerrequisitos.csv` y `data/historial_academico.csv`"
    else:
        reprobados = (
            historial[historial["estado"].astype(str).map(normalizar) == "reprobado"]
            if not historial.empty
            else historial.iloc[0:0]
        )
        if not reprobados.empty:
            primero = reprobados.iloc[0]
            breve = (
                "No veo prerrequisitos pendientes, pero podrías retomar primero "
                f"**{primero['codigo_ramo']} — {primero['nombre_ramo']}**, que figura reprobado "
                "en tu historial."
            )
            detalle = "\n".join(
                f"- **{fila['codigo_ramo']} — {fila['nombre_ramo']}** (nota {fila['nota']})."
                for _, fila in reprobados.iterrows()
            )
            fuente = "`data/historial_academico.csv`"
        else:
            primero = ramos.iloc[0]
            breve = (
                "No hay una señal de riesgo en tus datos, así que puedes empezar por "
                f"**{primero['codigo_ramo']} — {primero['nombre_ramo']}** y avanzar según tu preferencia."
            )
            detalle = "No se detectaron prerrequisitos pendientes ni ramos reprobados en tu historial."
            fuente = "`data/ramos_inscritos.csv`"
    return (
        f"### Respuesta breve\n\n{breve}\n\n"
        f"### Evidencia encontrada\n\n{detalle}\n\n"
        "### Recomendación de estudio\n\nEsta sugerencia usa solo tus datos locales; confirma el "
        "orden con tu malla y con coordinación académica.\n\n"
        f"### Fuente consultada\n\n{fuente}."
    )


def responder_conversacional(
    pregunta,
    alumno,
    ramos,
    historial,
    prerrequisitos,
    prerrequisitos_alumno,
    malla,
    chunks,
    vectorizador,
    matriz,
    ramo_contexto,
    opciones_ramos,
):
    social = detectar_intencion_social(pregunta)
    if social:
        st.session_state["ultima_intencion"] = social
        return {"apertura": MENSAJES_SOCIALES[social], "cuerpo": None, "cierre": None}

    if es_recomendacion(pregunta):
        st.session_state["ultima_intencion"] = "recomendacion"
        return {
            "apertura": elegir_apertura(),
            "cuerpo": respuesta_recomendacion(ramos, historial, prerrequisitos_alumno),
            "cierre": PREGUNTAS_CIERRE["recomendacion"],
        }

    codigo, nombre = detectar_ramo(malla, pregunta)
    pregunta_efectiva = pregunta
    if codigo is None and es_seguimiento_de_ramo(pregunta):
        if st.session_state.get("ultimo_ramo_codigo"):
            codigo = st.session_state["ultimo_ramo_codigo"]
            nombre = st.session_state["ultimo_ramo_nombre"]
            pregunta_efectiva = f"{pregunta} {nombre}"
        elif ramo_contexto:
            codigo = ramo_contexto["codigo_ramo"]
            nombre = ramo_contexto["nombre_ramo"]
            pregunta_efectiva = f"{pregunta} {nombre}"
        else:
            st.session_state["ultima_intencion"] = "pedir_ramo"
            return {
                "apertura": elegir_apertura(),
                "cuerpo": respuesta_pedir_ramo(opciones_ramos),
                "cierre": None,
            }

    cuerpo = responder(
        pregunta_efectiva,
        alumno,
        ramos,
        historial,
        prerrequisitos,
        malla,
        chunks,
        vectorizador,
        matriz,
        ramo_contexto,
    )

    codigo_efectivo = codigo or (ramo_contexto["codigo_ramo"] if ramo_contexto else None)
    nombre_efectivo = nombre or (ramo_contexto["nombre_ramo"] if ramo_contexto else None)
    if codigo_efectivo:
        st.session_state["ultimo_ramo_codigo"] = codigo_efectivo
        st.session_state["ultimo_ramo_nombre"] = nombre_efectivo

    intencion = clasificar_intencion(pregunta_efectiva, codigo_efectivo)
    st.session_state["ultima_intencion"] = intencion
    return {
        "apertura": elegir_apertura(),
        "cuerpo": cuerpo,
        "cierre": PREGUNTAS_CIERRE.get(intencion),
    }


def render_mensaje(mensaje):
    rol = mensaje["rol"]
    avatar = "🎓" if rol == "assistant" else None
    with st.chat_message(rol, avatar=avatar):
        if rol == "user":
            st.markdown(mensaje["texto"])
            return
        if mensaje.get("apertura"):
            st.markdown(
                f'<div class="udla-apertura">{mensaje["apertura"]}</div>',
                unsafe_allow_html=True,
            )
        if mensaje.get("cuerpo") is not None:
            render_respuesta_academica(mensaje["cuerpo"])
        if mensaje.get("cierre"):
            st.markdown(
                f'<div class="udla-followup">{mensaje["cierre"]}</div>',
                unsafe_allow_html=True,
            )


def aplicar_estilos():
    """Aplica únicamente la identidad visual institucional de la interfaz."""
    st.markdown(
        """
        <style>
        :root {
            --udla-blue: #003A70;
            --udla-blue-secondary: #005EB8;
            --udla-orange: #F58220;
            --udla-bg: #F5F7FA;
            --udla-white: #FFFFFF;
            --udla-text: #1F2933;
            --udla-border: #D9DEE7;
        }

        .stApp {
            background: var(--udla-bg);
            color: var(--udla-text);
        }

        [data-testid="stHeader"] {
            background: rgba(245, 247, 250, 0.94);
        }

        .block-container {
            max-width: 1280px;
            padding-top: 1.4rem;
            padding-bottom: 3rem;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--udla-blue) 0%, #002B54 100%);
            border-right: 4px solid var(--udla-orange);
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p {
            color: var(--udla-white);
        }

        [data-testid="stSidebar"] [data-testid="stImage"] {
            background: var(--udla-white);
            border-radius: 10px;
            padding: 0.65rem;
            border-bottom: 4px solid var(--udla-orange);
        }

        [data-testid="stSidebar"] hr {
            border-color: rgba(255, 255, 255, 0.28);
        }

        [data-testid="stSidebar"] div[data-baseweb="select"] * {
            color: var(--udla-text) !important;
        }

        .udla-hero {
            min-height: 168px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            background: linear-gradient(135deg, var(--udla-blue) 0%, var(--udla-blue-secondary) 100%);
            border-left: 7px solid var(--udla-orange);
            border-radius: 14px;
            padding: 1.6rem 2rem;
            box-shadow: 0 10px 24px rgba(0, 58, 112, 0.14);
        }

        .udla-hero__eyebrow {
            color: #DCEBFA;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            margin-bottom: 0.45rem;
            text-transform: uppercase;
        }

        .udla-hero h1 {
            color: var(--udla-white);
            font-size: clamp(1.75rem, 3vw, 2.65rem);
            line-height: 1.12;
            margin: 0;
        }

        .udla-hero p {
            color: #EAF3FB;
            font-size: 1rem;
            line-height: 1.55;
            margin: 0.75rem 0 0;
            max-width: 820px;
        }

        h2, h3 {
            color: var(--udla-blue);
        }

        [data-testid="stMetric"] {
            background: var(--udla-white);
            border: 1px solid var(--udla-border);
            border-top: 4px solid var(--udla-orange);
            border-radius: 10px;
            padding: 0.75rem;
            box-shadow: 0 4px 12px rgba(31, 41, 51, 0.06);
        }

        [data-testid="stMetricLabel"] p,
        [data-testid="stMetricValue"] {
            color: var(--udla-blue) !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--udla-white);
            border-color: var(--udla-border) !important;
            border-radius: 12px;
            box-shadow: 0 5px 16px rgba(31, 41, 51, 0.05);
        }

        [data-testid="stButton"] button {
            border: 1px solid var(--udla-blue-secondary);
            border-radius: 8px;
            color: var(--udla-blue);
            font-weight: 650;
        }

        [data-testid="stButton"] button:hover {
            border-color: var(--udla-orange);
            color: var(--udla-blue);
        }

        [data-testid="stButton"] button[kind="primary"] {
            background: var(--udla-orange);
            border-color: var(--udla-orange);
            color: var(--udla-white);
            min-height: 3rem;
            font-size: 1rem;
        }

        [data-testid="stButton"] button[kind="primary"]:hover {
            background: #D96D12;
            border-color: #D96D12;
            color: var(--udla-white);
        }

        [data-testid="stTextArea"] textarea {
            background: var(--udla-white);
            border-color: var(--udla-border);
            border-radius: 10px;
        }

        [data-testid="stTextArea"] textarea:focus {
            border-color: var(--udla-blue-secondary);
            box-shadow: 0 0 0 1px var(--udla-blue-secondary);
        }

        [data-testid="stDataFrame"],
        [data-testid="stExpander"] {
            background: var(--udla-white);
            border: 1px solid var(--udla-border);
            border-radius: 10px;
        }

        .udla-response-label {
            color: var(--udla-blue);
            border-left: 5px solid var(--udla-orange);
            font-size: 0.82rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            margin: 1.4rem 0 0.65rem;
            padding-left: 0.7rem;
            text-transform: uppercase;
        }

        .udla-apertura {
            color: var(--udla-text);
            font-size: 1.02rem;
            font-weight: 600;
            margin-bottom: 0.35rem;
        }

        .udla-followup {
            margin-top: 1.1rem;
            padding: 0.7rem 1rem;
            background: #EAF3FB;
            border-left: 4px solid var(--udla-orange);
            border-radius: 8px;
            color: var(--udla-blue);
            font-weight: 600;
        }

        @media (max-width: 700px) {
            .udla-hero {
                min-height: auto;
                padding: 1.25rem;
            }
            .block-container {
                padding-top: 0.8rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title="Asistente Académico | Ingeniería Comercial",
    page_icon="🎓",
    layout="wide",
)

aplicar_estilos()

col_logo, col_encabezado = st.columns([1, 3.2], vertical_alignment="center")
with col_logo:
    with st.container(border=True):
        st.image(str(LOGO_UDLA), width="stretch")
with col_encabezado:
    st.markdown(
        """
        <section class="udla-hero">
            <div class="udla-hero__eyebrow">Facultad de Ingeniería y Negocios</div>
            <h1>Asistente Académico de Ingeniería Comercial</h1>
            <p>
                Consulta antecedentes académicos sintéticos y encuentra evidencia en programas
                de asignatura mediante búsqueda documental local con TF-IDF.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

try:
    alumnos, malla, inscritos, historial, chunks, prerrequisitos = cargar_datos()
except (FileNotFoundError, ValueError) as exc:
    st.error(f"No fue posible iniciar la aplicación: {exc}")
    st.stop()

textos_indice = tuple(chunks["texto"].fillna("").astype(str))
vectorizador, matriz_tfidf = construir_indice_tfidf(textos_indice)
mapa_prerrequisitos = preparar_mapa_prerrequisitos(prerrequisitos, malla)
metricas_prerrequisitos = calcular_metricas_prerrequisitos(prerrequisitos)

with st.sidebar:
    st.image(str(LOGO_UDLA_FINE), width="stretch")
    st.header("Panel académico")
    id_alumno = st.selectbox(
        "Alumno",
        alumnos["id_alumno"].astype(str).tolist(),
        help="Los registros utilizados en este MVP son sintéticos.",
    )
    alumno = buscar_alumno(alumnos, id_alumno)
    if alumno is None:
        st.error("El alumno seleccionado no existe en la base.")
        st.stop()

    ramos_alumno = filtrar_por_alumno(inscritos, id_alumno)
    historial_alumno = filtrar_por_alumno(historial, id_alumno)
    opciones_ramos = {"Todos los ramos": None}
    for _, fila in ramos_alumno.iterrows():
        etiqueta = f"{fila['codigo_ramo']} — {fila['nombre_ramo']}"
        opciones_ramos[etiqueta] = {
            "codigo_ramo": str(fila["codigo_ramo"]),
            "nombre_ramo": str(fila["nombre_ramo"]),
        }
    etiqueta_ramo = st.selectbox(
        "Ramo inscrito (opcional)",
        list(opciones_ramos),
        help="Se usa como contexto si la pregunta no menciona un ramo.",
    )
    ramo_contexto = opciones_ramos[etiqueta_ramo]

    st.divider()
    st.subheader("Estado de la base")
    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Alumnos", len(alumnos))
    col_m2.metric("Ramos", len(malla))
    st.metric("Fragmentos documentales", len(chunks))
    if vectorizador is not None:
        st.success("Índice TF-IDF disponible")
    else:
        st.warning("Índice documental no disponible")
    if prerrequisitos.empty:
        st.info("No hay prerrequisitos cargados")
    else:
        st.success(
            f"Prerrequisitos disponibles: {metricas_prerrequisitos['relaciones']} relaciones"
        )

    st.divider()
    st.subheader("Conversación")
    if st.button("Reiniciar conversación", key="reiniciar_conversacion", width="stretch"):
        for clave in (
            "historial_conversacion",
            "ultimo_ramo_codigo",
            "ultimo_ramo_nombre",
            "ultima_intencion",
            "ultima_alerta",
            "ultimo_tema",
        ):
            st.session_state.pop(clave, None)
        st.success("Conversación reiniciada. Puedes comenzar una nueva consulta.")

prerrequisitos_alumno = construir_prerrequisitos_alumno(
    ramos_alumno, historial_alumno, prerrequisitos
)

col_datos, col_ramos = st.columns([1, 1.4])
with col_datos:
    with st.container(border=True):
        st.subheader("Ficha del alumno")
        st.write(f"**Nombre:** {alumno['nombre']}")
        st.write(f"**Carrera:** {alumno['carrera']}")
        st.write(f"**Sede y jornada:** {alumno['sede']} · {alumno['jornada']}")
        st.write(f"**Semestre actual:** {alumno['semestre_actual']}")

with col_ramos:
    with st.container(border=True):
        st.subheader("Ramos inscritos")
        if ramos_alumno.empty:
            st.info("No hay ramos inscritos para este alumno.")
        else:
            st.dataframe(
                ramos_alumno[["codigo_ramo", "nombre_ramo", "estado"]],
                width="stretch",
                hide_index=True,
            )

st.subheader("Prerrequisitos del alumno")
with st.container(border=True):
    if prerrequisitos.empty:
        st.info("No hay prerrequisitos cargados")
    elif prerrequisitos_alumno.empty:
        st.info("No hay ramos inscritos o relaciones disponibles para este alumno.")
    else:
        columnas_alumno = {
            "codigo_ramo": "Código ramo",
            "nombre_ramo": "Ramo inscrito",
            "codigo_prerrequisito": "Código prerrequisito",
            "nombre_prerrequisito": "Prerrequisito",
            "tipo": "Tipo",
            "estado_prerrequisito": "Estado",
            "alerta": "Alerta",
        }
        st.dataframe(
            prerrequisitos_alumno[list(columnas_alumno)].rename(
                columns=columnas_alumno
            ),
            width="stretch",
            hide_index=True,
        )
        st.caption(
            "Los estados se calculan únicamente con historial_academico.csv y las "
            "relaciones presentes en prerrequisitos.csv."
        )

st.divider()
st.subheader("Conversa con tu asistente académico")

for clave, valor in (
    ("historial_conversacion", []),
    ("ultimo_ramo_codigo", None),
    ("ultimo_ramo_nombre", None),
    ("ultima_intencion", None),
    ("pregunta_pendiente", None),
):
    st.session_state.setdefault(clave, valor)

st.caption("Sugerencias para empezar:")
columnas_preguntas = st.columns(3)
for indice, pregunta_rapida in enumerate(PREGUNTAS_RAPIDAS):
    if columnas_preguntas[indice % 3].button(
        pregunta_rapida, key=f"rapida_{indice}", width="stretch"
    ):
        st.session_state["pregunta_pendiente"] = pregunta_rapida

if not st.session_state["historial_conversacion"]:
    with st.chat_message("assistant", avatar="🎓"):
        st.markdown(
            f'<div class="udla-apertura">{MENSAJES_SOCIALES["saludo"]}</div>',
            unsafe_allow_html=True,
        )

for mensaje in st.session_state["historial_conversacion"]:
    render_mensaje(mensaje)

entrada = st.chat_input("Escribe tu consulta académica...")
consulta_usuario = entrada or st.session_state.pop("pregunta_pendiente", None)
if consulta_usuario and consulta_usuario.strip():
    st.session_state["historial_conversacion"].append(
        {"rol": "user", "texto": consulta_usuario}
    )
    with st.spinner("Consultando la base local..."):
        mensaje_asistente = responder_conversacional(
            consulta_usuario,
            alumno,
            ramos_alumno,
            historial_alumno,
            prerrequisitos,
            prerrequisitos_alumno,
            malla,
            chunks,
            vectorizador,
            matriz_tfidf,
            ramo_contexto,
            opciones_ramos,
        )
    mensaje_asistente["rol"] = "assistant"
    st.session_state["historial_conversacion"].append(mensaje_asistente)
    st.rerun()

st.divider()
with st.expander("Mapa de prerrequisitos", expanded=False):
    if prerrequisitos.empty:
        st.info("No hay prerrequisitos cargados")
    else:
        columnas_metricas = st.columns(5)
        columnas_metricas[0].metric(
            "Ramos analizados", metricas_prerrequisitos["analizados"]
        )
        columnas_metricas[1].metric(
            "Con prerrequisito", metricas_prerrequisitos["con_prerrequisito"]
        )
        columnas_metricas[2].metric(
            "Sin prerrequisito", metricas_prerrequisitos["sin_prerrequisito"]
        )
        columnas_metricas[3].metric(
            "No detectados", metricas_prerrequisitos["no_detectados"]
        )
        columnas_metricas[4].metric(
            "Relaciones", metricas_prerrequisitos["relaciones"]
        )

        filtro_semestre, filtro_ramo, filtro_tipo = st.columns(3)
        semestres_disponibles = sorted(
            mapa_prerrequisitos["semestre"].dropna().astype(int).unique().tolist()
        )
        semestre_seleccionado = filtro_semestre.selectbox(
            "Semestre del ramo",
            ["Todos", *semestres_disponibles],
            key="filtro_prerrequisitos_semestre",
        )
        etiquetas_ramos = {
            "Todos": None,
            **{
                f"{fila['codigo_ramo']} — {fila['nombre_ramo']}": str(
                    fila["codigo_ramo"]
                )
                for _, fila in mapa_prerrequisitos.drop_duplicates(
                    "codigo_ramo"
                ).iterrows()
            },
        }
        ramo_seleccionado = filtro_ramo.selectbox(
            "Ramo",
            list(etiquetas_ramos),
            key="filtro_prerrequisitos_ramo",
        )
        tipo_seleccionado = filtro_tipo.selectbox(
            "Tipo",
            ["Todos", "Prerrequisito", "Sin prerrequisito", "No detectado"],
            key="filtro_prerrequisitos_tipo",
        )

        mapa_filtrado = mapa_prerrequisitos.copy()
        if semestre_seleccionado != "Todos":
            mapa_filtrado = mapa_filtrado[
                mapa_filtrado["semestre"].fillna(-1).astype(int)
                == semestre_seleccionado
            ]
        codigo_ramo_seleccionado = etiquetas_ramos[ramo_seleccionado]
        if codigo_ramo_seleccionado:
            mapa_filtrado = mapa_filtrado[
                mapa_filtrado["codigo_ramo"].astype(str)
                == codigo_ramo_seleccionado
            ]
        if tipo_seleccionado != "Todos":
            mapa_filtrado = mapa_filtrado[
                mapa_filtrado["tipo"] == tipo_seleccionado
            ]

        columnas_mapa = [
            "semestre",
            "codigo_ramo",
            "nombre_ramo",
            "codigo_prerrequisito",
            "nombre_prerrequisito",
            "tipo",
            "confianza",
            "fuente_archivo",
        ]
        nombres_mapa = {
            "semestre": "Semestre",
            "codigo_ramo": "Código ramo",
            "nombre_ramo": "Ramo",
            "codigo_prerrequisito": "Código prerrequisito",
            "nombre_prerrequisito": "Prerrequisito",
            "tipo": "Tipo",
            "confianza": "Confianza",
            "fuente_archivo": "Fuente",
            "evidencia_textual": "Evidencia textual",
        }
        mostrar_evidencia = st.checkbox(
            "Mostrar evidencia textual",
            value=False,
            key="mostrar_evidencia_prerrequisitos",
        )
        if mostrar_evidencia:
            columnas_mapa.append("evidencia_textual")
        st.dataframe(
            mapa_filtrado[columnas_mapa].rename(columns=nombres_mapa),
            width="stretch",
            hide_index=True,
        )
        st.caption(f"Filas mostradas: {len(mapa_filtrado)}")

with st.expander("Ver historial académico sintético"):
    st.dataframe(historial_alumno, width="stretch", hide_index=True)
with st.expander("Ver malla curricular"):
    st.dataframe(malla, width="stretch", hide_index=True)
with st.expander("Ver muestra de la base documental"):
    columnas_muestra = [
        columna
        for columna in ("chunk_id", "codigo_ramo", "nombre_ramo", "fuente_legible", "ruta_archivo")
        if columna in chunks.columns
    ]
    st.dataframe(chunks[columnas_muestra].head(20), width="stretch", hide_index=True)
