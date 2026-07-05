"""Utilidades puras de normalización de texto."""

import re
import unicodedata


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return re.sub(r"\s+", " ", texto).strip()
