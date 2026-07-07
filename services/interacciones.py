"""Persistencia local anónima de interacciones del asistente (demo).

Guarda cada turno pregunta/respuesta en una base SQLite local
(``data/interacciones_demo.db`` por defecto) para poder responder la pregunta
"¿dónde quedan guardadas las interacciones?" sin depender de servicios externos.

Principios de esta capa:

- **Responsable con la privacidad:** solo se registra el texto de la consulta y
  metadata de intención/carrera. No hay columnas para nombre real, RUT, correo
  ni teléfono. El usuario es advertido en la interfaz de no ingresar datos
  sensibles.
- **A prueba de fallos:** ninguna función pública propaga excepciones a la UI.
  Si la escritura falla (disco de solo lectura, ruta inválida, etc.) se devuelve
  ``None``/``False``/estructura vacía y la app sigue funcionando.
- **Solo strings/ints:** este módulo no conoce el contrato ``RespuestaChatbot``;
  recibe valores planos ya extraídos por la capa conversacional.

Nota de despliegue: en Streamlit Cloud el sistema de archivos es efímero, por lo
que la base persiste durante la sesión pero puede reiniciarse en cada
reinicio/redeploy. Para una versión institucional conviene migrar a una base
externa segura (PostgreSQL, Supabase, etc.). Ver README.md.
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config.settings import INTERACCIONES_DB_DEFECTO

_ENV_RUTA = "CHATBOT_INTERACCIONES_DB"

# Columnas ordenadas de la tabla, para lecturas explícitas y estables.
_COLUMNAS = (
    "id",
    "timestamp",
    "session_id",
    "pregunta_usuario",
    "respuesta_bot",
    "intencion_detectada",
    "carrera_contexto",
    "fuente_respuesta",
    "requiere_derivacion",
    "feedback_utilidad",
    "comentario_feedback",
)

_DDL = """
CREATE TABLE IF NOT EXISTS interacciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    session_id TEXT,
    pregunta_usuario TEXT,
    respuesta_bot TEXT,
    intencion_detectada TEXT,
    carrera_contexto TEXT,
    fuente_respuesta TEXT,
    requiere_derivacion INTEGER DEFAULT 0,
    feedback_utilidad TEXT,
    comentario_feedback TEXT
)
"""

FEEDBACK_VALIDO = {"positivo", "negativo"}


def ruta_db(db_path=None):
    """Resuelve la ruta de la base en tiempo de llamada.

    Prioridad: argumento explícito > variable de entorno
    ``CHATBOT_INTERACCIONES_DB`` > ``config.settings.INTERACCIONES_DB_DEFECTO``.
    Resolver la env var aquí (y no al importar) permite que los tests apunten la
    escritura a un archivo temporal sin tocar el ``data/`` real del repo.
    """
    if db_path:
        return Path(db_path)
    env = os.environ.get(_ENV_RUTA)
    if env:
        return Path(env)
    return Path(INTERACCIONES_DB_DEFECTO)


def _conectar(db_path=None):
    """Abre una conexión y garantiza el esquema. Puede lanzar; uso interno."""
    ruta = ruta_db(db_path)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta)
    conexion.execute(_DDL)
    return conexion


def inicializar_base(db_path=None):
    """Crea la carpeta y la tabla si no existen. Devuelve la ruta o ``None``."""
    try:
        conexion = _conectar(db_path)
    except (sqlite3.Error, OSError):
        return None
    try:
        conexion.commit()
        return ruta_db(db_path)
    finally:
        conexion.close()


def _texto(valor, limite=None):
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    if limite is not None and len(texto) > limite:
        return texto[:limite]
    return texto


def registrar_interaccion(
    pregunta,
    respuesta,
    *,
    intencion=None,
    carrera=None,
    fuente=None,
    requiere_derivacion=False,
    session_id=None,
    db_path=None,
):
    """Inserta una interacción y devuelve su ``id`` (o ``None`` si falla).

    Tolera valores ``None`` o faltantes: se guardan como ``NULL``. Nunca lanza.
    """
    try:
        conexion = _conectar(db_path)
    except (sqlite3.Error, OSError):
        return None
    try:
        cursor = conexion.execute(
            """
            INSERT INTO interacciones (
                timestamp, session_id, pregunta_usuario, respuesta_bot,
                intencion_detectada, carrera_contexto, fuente_respuesta,
                requiere_derivacion, feedback_utilidad, comentario_feedback
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
            """,
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                _texto(session_id),
                _texto(pregunta, limite=2000),
                _texto(respuesta, limite=4000),
                _texto(intencion),
                _texto(carrera),
                _texto(fuente),
                1 if requiere_derivacion else 0,
            ),
        )
        conexion.commit()
        return int(cursor.lastrowid)
    except (sqlite3.Error, OSError, ValueError):
        return None
    finally:
        conexion.close()


def actualizar_feedback(interaccion_id, feedback_utilidad, comentario=None, db_path=None):
    """Actualiza el feedback de una interacción existente. Devuelve ``bool``.

    ``feedback_utilidad`` debe ser ``'positivo'`` o ``'negativo'``; otro valor
    (o un id inexistente) devuelve ``False`` sin lanzar.
    """
    feedback = _texto(feedback_utilidad)
    if feedback not in FEEDBACK_VALIDO:
        return False
    try:
        identificador = int(interaccion_id)
    except (TypeError, ValueError):
        return False
    try:
        conexion = _conectar(db_path)
    except (sqlite3.Error, OSError):
        return False
    try:
        cursor = conexion.execute(
            """
            UPDATE interacciones
               SET feedback_utilidad = ?, comentario_feedback = ?
             WHERE id = ?
            """,
            (feedback, _texto(comentario, limite=1000), identificador),
        )
        conexion.commit()
        return cursor.rowcount > 0
    except (sqlite3.Error, OSError):
        return False
    finally:
        conexion.close()


def _conteo_por(conexion, columna):
    """Lista de (valor, n) agrupada por una columna, ignorando NULL/vacíos."""
    filas = conexion.execute(
        f"""
        SELECT COALESCE(NULLIF(TRIM({columna}), ''), '(sin dato)') AS clave,
               COUNT(*) AS n
          FROM interacciones
         GROUP BY clave
         ORDER BY n DESC, clave ASC
        """
    ).fetchall()
    return [(str(clave), int(n)) for clave, n in filas]


def _metricas_vacias():
    return {
        "total": 0,
        "por_intencion": [],
        "por_carrera": [],
        "feedback_positivo": 0,
        "feedback_negativo": 0,
        "sin_feedback": 0,
        "derivaciones": 0,
        "ultimas": [],
    }


def calcular_metricas(db_path=None):
    """Métricas agregadas para el panel demo. Nunca lanza; base vacía → ceros."""
    try:
        conexion = _conectar(db_path)
    except (sqlite3.Error, OSError):
        return _metricas_vacias()
    try:
        total = conexion.execute("SELECT COUNT(*) FROM interacciones").fetchone()[0]
        positivos = conexion.execute(
            "SELECT COUNT(*) FROM interacciones WHERE feedback_utilidad = 'positivo'"
        ).fetchone()[0]
        negativos = conexion.execute(
            "SELECT COUNT(*) FROM interacciones WHERE feedback_utilidad = 'negativo'"
        ).fetchone()[0]
        derivaciones = conexion.execute(
            "SELECT COUNT(*) FROM interacciones WHERE requiere_derivacion = 1"
        ).fetchone()[0]
        ultimas = [
            {
                "timestamp": fila[0] or "",
                "pregunta": (fila[1] or "")[:120],
                "intencion": fila[2] or "—",
                "carrera": fila[3] or "—",
                "requiere_derivacion": bool(fila[4]),
            }
            for fila in conexion.execute(
                """
                SELECT timestamp, pregunta_usuario, intencion_detectada,
                       carrera_contexto, requiere_derivacion
                  FROM interacciones
                 ORDER BY id DESC
                 LIMIT 5
                """
            ).fetchall()
        ]
        return {
            "total": int(total),
            "por_intencion": _conteo_por(conexion, "intencion_detectada"),
            "por_carrera": _conteo_por(conexion, "carrera_contexto"),
            "feedback_positivo": int(positivos),
            "feedback_negativo": int(negativos),
            "sin_feedback": int(total) - int(positivos) - int(negativos),
            "derivaciones": int(derivaciones),
            "ultimas": ultimas,
        }
    except (sqlite3.Error, OSError):
        return _metricas_vacias()
    finally:
        conexion.close()
