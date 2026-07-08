"""Respuestas curadas desde ``data/corpus/corpus_chatbot_udla_v5.csv``."""

import re
from functools import lru_cache

import pandas as pd

from chatbot.contratos import RespuestaChatbot, SeccionRespuesta
from config.settings import DATA_DIR, STOPWORDS_ES
from utils.texto import normalizar

CORPUS_CHATBOT_CSV = DATA_DIR / "corpus" / "corpus_chatbot_udla_v5.csv"

COLUMNAS_CORPUS = (
    "tipo_registro",
    "id",
    "categoria_o_escalon",
    "titulo_o_pregunta",
    "respuesta_o_instruccion",
    "fuente_datos",
    "recursos_sugeridos",
    "requiere_datos_personales",
    "tipo_respuesta",
    "ambito",
    "tipo_caso",
    "riesgo_vital",
    "contacto_oficial",
    "horario",
    "cobertura",
    "que_no_debe_prometer",
    "fuente_url",
    "fecha_verificacion",
    "nivel_confianza",
    "notas",
)

# Estas categorias ya tienen rutas deterministas o documentales en el bot.
CATEGORIAS_DERIVADAS_A_FLUJO_EXISTENTE = (
    "1.",
    "2.",
    "3.",
    "4.",
    "5.",
    "6.",
    "7.",
    "8.",
)

STOPWORDS_CORPUS = STOPWORDS_ES | {
    "como",
    "cual",
    "cuanto",
    "cuantos",
    "donde",
    "hacer",
    "hago",
    "puedo",
    "puedes",
    "tengo",
    "tener",
    "esto",
    "esta",
    "este",
    "ese",
    "esa",
    "soy",
}

RECURSOS_POR_CLAVE = (
    (("riesgo vital", "urgente", "hacerme dano", "crisis de angustia"), ("R01", "R02", "R03", "R09", "R19")),
    (("bienestar", "apoyo psicologico", "salud mental", "psicologico"), ("R09", "R11")),
    (("dae", "asuntos estudiantiles"), ("R09", "R10")),
    (("tutoria", "tutorias", "reforzamiento"), ("R14",)),
    (("reclamo", "reclamar", "solicitud"), ("R17",)),
    (("acoso", "violencia", "discriminacion"), ("R15", "R16")),
    (("beca", "socioeconomico", "financiamiento", "calamidad"), ("R12",)),
    (("limite", "oficial", "bot", "autorizacion"), ("R19",)),
)


def _leer_corpus(ruta):
    if not ruta.exists():
        return pd.DataFrame(columns=COLUMNAS_CORPUS)
    try:
        df = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    except (pd.errors.EmptyDataError, OSError):
        return pd.DataFrame(columns=COLUMNAS_CORPUS)
    faltantes = set(COLUMNAS_CORPUS) - set(df.columns)
    if faltantes:
        return pd.DataFrame(columns=COLUMNAS_CORPUS)
    return df.loc[:, COLUMNAS_CORPUS].fillna("")


@lru_cache(maxsize=1)
def _cargar_corpus_default():
    return _leer_corpus(CORPUS_CHATBOT_CSV)


def cargar_corpus_chatbot(ruta=None):
    """Carga el corpus ampliado del chatbot. Vacio si falta o es invalido."""
    if ruta is None:
        return _cargar_corpus_default().copy()
    return _leer_corpus(ruta)


def _valor(fila, columna):
    valor = fila.get(columna, "")
    return "" if pd.isna(valor) else str(valor).strip()


def _categoria_excluida(fila):
    categoria = _valor(fila, "categoria_o_escalon")
    return any(categoria.startswith(prefijo) for prefijo in CATEGORIAS_DERIVADAS_A_FLUJO_EXISTENTE)


def _tokens(texto):
    return {
        token
        for token in re.findall(r"[a-z0-9]+", normalizar(str(texto)))
        if len(token) >= 3 and token not in STOPWORDS_CORPUS
    }


def _puntaje_fila(mensaje, fila):
    consulta = normalizar(mensaje)
    titulo = normalizar(_valor(fila, "titulo_o_pregunta"))
    if not consulta or not titulo:
        return 0.0
    if consulta == titulo:
        return 1.0
    if len(consulta) >= 12 and (consulta in titulo or titulo in consulta):
        return 0.92

    tokens_consulta = _tokens(consulta)
    tokens_titulo = _tokens(titulo)
    if not tokens_consulta or not tokens_titulo:
        return 0.0

    coincidencias = tokens_consulta & tokens_titulo
    if len(coincidencias) < 2:
        return 0.0

    cobertura_consulta = len(coincidencias) / len(tokens_consulta)
    cobertura_titulo = len(coincidencias) / len(tokens_titulo)
    puntaje = (0.72 * cobertura_consulta) + (0.28 * cobertura_titulo)

    texto_contexto = " ".join(
        [
            _valor(fila, "categoria_o_escalon"),
            _valor(fila, "respuesta_o_instruccion"),
            _valor(fila, "tipo_respuesta"),
        ]
    )
    if tokens_consulta & _tokens(texto_contexto):
        puntaje += 0.08
    return min(puntaje, 1.0)


def detectar_fila_corpus(mensaje, tabla=None):
    """Busca la mejor fila del corpus ampliado para un mensaje del usuario."""
    tabla = cargar_corpus_chatbot() if tabla is None else tabla
    if tabla.empty:
        return None

    mejor = None
    mejor_puntaje = 0.0
    for _, fila in tabla.iterrows():
        if _valor(fila, "tipo_registro") == "pregunta" and _categoria_excluida(fila):
            continue
        puntaje = _puntaje_fila(mensaje, fila)
        if puntaje > mejor_puntaje:
            mejor = fila.to_dict()
            mejor_puntaje = puntaje

    if mejor is None or mejor_puntaje < 0.48:
        return None
    mejor["_puntaje_corpus"] = mejor_puntaje
    return mejor


def _ids_recursos_sugeridos(fila):
    return re.findall(r"\bR\d{2}\b", _valor(fila, "recursos_sugeridos"))


def _ids_recursos_por_contexto(fila):
    texto = normalizar(
        " ".join(
            [
                _valor(fila, "categoria_o_escalon"),
                _valor(fila, "titulo_o_pregunta"),
                _valor(fila, "respuesta_o_instruccion"),
                _valor(fila, "tipo_respuesta"),
            ]
        )
    )
    ids = []
    for claves, recursos in RECURSOS_POR_CLAVE:
        if any(clave in texto for clave in claves):
            ids.extend(recursos)
    return ids


def _recursos_para_fila(fila, tabla):
    ids = []
    for recurso_id in [*_ids_recursos_sugeridos(fila), *_ids_recursos_por_contexto(fila)]:
        if recurso_id not in ids:
            ids.append(recurso_id)
    if not ids or tabla.empty:
        return []

    recursos = []
    recursos_tabla = tabla[tabla["tipo_registro"].eq("recurso_verificado")]
    for recurso_id in ids:
        coincidencia = recursos_tabla[recursos_tabla["id"].eq(recurso_id)]
        if not coincidencia.empty:
            recursos.append(coincidencia.iloc[0].to_dict())
    return recursos


def _markdown_recurso(recurso):
    partes = [
        f"- **{_valor(recurso, 'titulo_o_pregunta')}**: "
        f"{_valor(recurso, 'respuesta_o_instruccion')}"
    ]
    contacto = _valor(recurso, "contacto_oficial")
    horario = _valor(recurso, "horario")
    cobertura = _valor(recurso, "cobertura")
    fuente = _valor(recurso, "fuente_url")
    if contacto:
        partes.append(f"  Contacto: {contacto}.")
    if horario:
        partes.append(f"  Horario: {horario}.")
    if cobertura:
        partes.append(f"  Cobertura: {cobertura}.")
    if fuente:
        partes.append(f"  Fuente: {fuente}")
    return "\n".join(partes)


def _resumen_para_fila(fila):
    instruccion = _valor(fila, "respuesta_o_instruccion")
    tipo = _valor(fila, "tipo_respuesta")
    tipo_registro = _valor(fila, "tipo_registro")

    if tipo_registro == "recurso_verificado":
        return instruccion
    if "urgente" in normalizar(tipo):
        return (
            "Esta consulta requiere apoyo humano inmediato si hay riesgo o crisis. "
            f"El corpus indica: {instruccion}"
        )
    if "derivar" in normalizar(tipo) or "contencion" in normalizar(tipo):
        return (
            f"El corpus recomienda orientar y derivar: {instruccion} "
            "Valida el caso con la unidad institucional correspondiente."
        )
    return f"Segun el corpus UDLA: {instruccion}"


def responder_desde_corpus(mensaje, contexto=None, tabla=None):
    """Responde usando el corpus ampliado si hay una coincidencia suficiente."""
    tabla = cargar_corpus_chatbot() if tabla is None else tabla
    fila = detectar_fila_corpus(mensaje, tabla=tabla)
    if fila is None:
        return None

    recursos = _recursos_para_fila(fila, tabla)
    secciones = [
        SeccionRespuesta(
            titulo="Registro del corpus",
            contenido=(
                f"- Pregunta base: **{_valor(fila, 'titulo_o_pregunta')}**\n"
                f"- Categoria: {_valor(fila, 'categoria_o_escalon')}\n"
                f"- Tipo de respuesta: {_valor(fila, 'tipo_respuesta') or 'No especificado'}"
            ),
            formato="markdown",
        )
    ]
    if recursos:
        secciones.append(
            SeccionRespuesta(
                titulo="Recursos verificados sugeridos",
                contenido="\n\n".join(_markdown_recurso(recurso) for recurso in recursos),
                formato="markdown",
            )
        )

    advertencias = [
        "Esta respuesta es orientativa y no reemplaza canales oficiales UDLA."
    ]
    if normalizar(_valor(fila, "requiere_datos_personales")) in {"si", "s"}:
        advertencias.append(
            "La consulta puede requerir datos personales; evita compartirlos en el chat y usa canales oficiales."
        )

    fuentes = [f"corpus_chatbot_udla_v5.csv:{_valor(fila, 'id')}"]
    for recurso in recursos:
        url = _valor(recurso, "fuente_url")
        if url:
            fuentes.append(url)

    return RespuestaChatbot(
        tipo="corpus_udla",
        titulo="Orientacion desde corpus UDLA",
        resumen=_resumen_para_fila(fila),
        secciones=secciones,
        fuentes=fuentes,
        advertencias=advertencias,
        metadata={
            "corpus_id": _valor(fila, "id"),
            "categoria": _valor(fila, "categoria_o_escalon"),
            "puntaje": fila.get("_puntaje_corpus"),
            "cierre_sugerido": "Quieres explorar otra categoria del corpus UDLA?",
        },
    )
