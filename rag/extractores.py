"""Extractores heurísticos de programas de asignatura."""

import re

import pandas as pd

from chatbot.intenciones import normalizar


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

