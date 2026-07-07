import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True, scope="session")
def _aislar_base_interacciones(tmp_path_factory):
    """Redirige el registro de interacciones a una base temporal.

    Evita que los tests que ejercitan la app real (streamlit AppTest) escriban en
    ``data/interacciones_demo.db`` del repositorio. ``services.interacciones``
    resuelve esta variable de entorno en tiempo de llamada, por lo que basta con
    setearla antes de que se ejecute cualquier registro.
    """
    ruta = tmp_path_factory.mktemp("interacciones") / "interacciones_test.db"
    anterior = os.environ.get("CHATBOT_INTERACCIONES_DB")
    os.environ["CHATBOT_INTERACCIONES_DB"] = str(ruta)
    try:
        yield
    finally:
        if anterior is None:
            os.environ.pop("CHATBOT_INTERACCIONES_DB", None)
        else:
            os.environ["CHATBOT_INTERACCIONES_DB"] = anterior
