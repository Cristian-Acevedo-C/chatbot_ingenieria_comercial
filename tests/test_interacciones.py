"""Registro anónimo de interacciones en SQLite (demo).

Cada test usa un ``db_path`` temporal explícito, por lo que quedan aislados
entre sí y del ``data/`` real del proyecto.
"""

import sqlite3

import pytest

from services.interacciones import (
    actualizar_feedback,
    calcular_metricas,
    inicializar_base,
    registrar_interaccion,
)


@pytest.fixture
def db(tmp_path):
    return tmp_path / "interacciones.db"


def _tablas(db_path):
    conexion = sqlite3.connect(db_path)
    try:
        return {
            fila[0]
            for fila in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    finally:
        conexion.close()


def test_inicializar_crea_base_y_tabla(db):
    ruta = inicializar_base(db_path=db)
    assert ruta is not None
    assert db.exists()
    assert "interacciones" in _tablas(db)


def test_registrar_devuelve_id_y_persiste(db):
    id_1 = registrar_interaccion(
        "¿qué ramos tengo?",
        "Tienes 3 ramos inscritos.",
        intencion="ramos_inscritos",
        carrera="Ingeniería Comercial",
        fuente="ramos_inscritos",
        session_id="abc123",
        db_path=db,
    )
    assert isinstance(id_1, int)

    conexion = sqlite3.connect(db)
    try:
        fila = conexion.execute(
            "SELECT pregunta_usuario, respuesta_bot, intencion_detectada, "
            "carrera_contexto, session_id, feedback_utilidad FROM interacciones "
            "WHERE id = ?",
            (id_1,),
        ).fetchone()
    finally:
        conexion.close()
    assert fila[0] == "¿qué ramos tengo?"
    assert fila[1] == "Tienes 3 ramos inscritos."
    assert fila[2] == "ramos_inscritos"
    assert fila[3] == "Ingeniería Comercial"
    assert fila[4] == "abc123"
    assert fila[5] is None  # sin feedback aún


def test_registrar_incrementa_ids(db):
    id_1 = registrar_interaccion("p1", "r1", db_path=db)
    id_2 = registrar_interaccion("p2", "r2", db_path=db)
    assert id_2 != id_1


def test_actualizar_feedback_modifica_la_fila_correcta(db):
    id_1 = registrar_interaccion("p1", "r1", db_path=db)
    id_2 = registrar_interaccion("p2", "r2", db_path=db)

    assert actualizar_feedback(id_2, "negativo", "faltó el detalle", db_path=db) is True

    conexion = sqlite3.connect(db)
    try:
        f1 = conexion.execute(
            "SELECT feedback_utilidad FROM interacciones WHERE id=?", (id_1,)
        ).fetchone()
        f2 = conexion.execute(
            "SELECT feedback_utilidad, comentario_feedback FROM interacciones WHERE id=?",
            (id_2,),
        ).fetchone()
    finally:
        conexion.close()
    assert f1[0] is None
    assert f2[0] == "negativo"
    assert f2[1] == "faltó el detalle"


def test_actualizar_feedback_valor_invalido_no_persiste(db):
    id_1 = registrar_interaccion("p1", "r1", db_path=db)
    assert actualizar_feedback(id_1, "tal vez", db_path=db) is False


def test_actualizar_feedback_id_inexistente_devuelve_false(db):
    inicializar_base(db_path=db)
    assert actualizar_feedback(9999, "positivo", db_path=db) is False


def test_registrar_tolera_campos_faltantes(db):
    id_1 = registrar_interaccion(None, None, db_path=db)
    assert isinstance(id_1, int)

    conexion = sqlite3.connect(db)
    try:
        fila = conexion.execute(
            "SELECT pregunta_usuario, respuesta_bot, intencion_detectada, "
            "requiere_derivacion FROM interacciones WHERE id=?",
            (id_1,),
        ).fetchone()
    finally:
        conexion.close()
    assert fila[0] is None
    assert fila[1] is None
    assert fila[2] is None
    assert fila[3] == 0  # requiere_derivacion por defecto


def test_metricas_base_vacia_devuelve_ceros(db):
    inicializar_base(db_path=db)
    metricas = calcular_metricas(db_path=db)
    assert metricas["total"] == 0
    assert metricas["por_intencion"] == []
    assert metricas["por_carrera"] == []
    assert metricas["feedback_positivo"] == 0
    assert metricas["feedback_negativo"] == 0
    assert metricas["sin_feedback"] == 0
    assert metricas["derivaciones"] == 0
    assert metricas["ultimas"] == []


def test_metricas_agregan_correctamente(db):
    registrar_interaccion(
        "p1", "r1", intencion="ramos_inscritos", carrera="Ingeniería Comercial",
        db_path=db,
    )
    id_2 = registrar_interaccion(
        "p2", "r2", intencion="documental", carrera="Ingeniería Comercial",
        requiere_derivacion=True, db_path=db,
    )
    registrar_interaccion(
        "p3", "r3", intencion="ramos_inscritos",
        carrera="Ingeniería Civil Industrial", db_path=db,
    )
    actualizar_feedback(id_2, "negativo", db_path=db)

    metricas = calcular_metricas(db_path=db)
    assert metricas["total"] == 3
    assert metricas["derivaciones"] == 1
    assert metricas["feedback_negativo"] == 1
    assert metricas["feedback_positivo"] == 0
    assert metricas["sin_feedback"] == 2

    por_intencion = dict(metricas["por_intencion"])
    assert por_intencion["ramos_inscritos"] == 2
    assert por_intencion["documental"] == 1

    por_carrera = dict(metricas["por_carrera"])
    assert por_carrera["Ingeniería Comercial"] == 2
    assert por_carrera["Ingeniería Civil Industrial"] == 1


def test_ultimas_devuelve_como_maximo_cinco_mas_recientes_primero(db):
    for indice in range(7):
        registrar_interaccion(f"pregunta {indice}", "r", db_path=db)
    ultimas = calcular_metricas(db_path=db)["ultimas"]
    assert len(ultimas) == 5
    # La más reciente (índice 6) debe ir primero.
    assert ultimas[0]["pregunta"] == "pregunta 6"


def test_intencion_y_carrera_faltantes_se_agrupan_como_sin_dato(db):
    registrar_interaccion("p", "r", db_path=db)
    metricas = calcular_metricas(db_path=db)
    assert dict(metricas["por_intencion"]).get("(sin dato)") == 1
    assert dict(metricas["por_carrera"]).get("(sin dato)") == 1
