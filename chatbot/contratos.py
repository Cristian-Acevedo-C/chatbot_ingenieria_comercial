"""Contrato tipado y adaptadores para respuestas nuevas y heredadas."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Evidencia:
    texto: str
    fuente: str = ""
    score: float | None = None
    pagina: str | None = None


@dataclass(frozen=True)
class SeccionRespuesta:
    titulo: str
    contenido: str | list[dict[str, Any]] | None = None
    formato: str = "markdown"

    def __post_init__(self):
        permitidos = {"markdown", "tabla", "lista", "texto"}
        if self.formato not in permitidos:
            raise ValueError(
                f"Formato de sección no soportado: {self.formato}. "
                f"Use uno de {sorted(permitidos)}."
            )


@dataclass
class RespuestaChatbot:
    tipo: str
    titulo: str | None = None
    resumen: str = ""
    secciones: list[SeccionRespuesta] = field(default_factory=list)
    evidencias: list[Evidencia] = field(default_factory=list)
    fuentes: list[str] = field(default_factory=list)
    recomendacion: str | None = None
    advertencias: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def _evidencia_desde_valor(valor):
    if isinstance(valor, Evidencia):
        return valor
    if isinstance(valor, dict):
        score = valor.get("score")
        try:
            score = float(score) if score is not None else None
        except (TypeError, ValueError):
            score = None
        return Evidencia(
            texto=str(valor.get("texto", "")),
            fuente=str(valor.get("fuente", "")),
            score=score,
            pagina=(
                str(valor["pagina"])
                if valor.get("pagina") is not None
                else None
            ),
        )
    return Evidencia(texto=str(valor))


def respuesta_desde_markdown(texto, tipo="legacy"):
    return RespuestaChatbot(
        tipo=tipo,
        secciones=[
            SeccionRespuesta(titulo="", contenido=str(texto), formato="markdown")
        ],
        metadata={"formato_original": "legacy"},
    )


def respuesta_desde_dict(diccionario, tipo=None):
    if not isinstance(diccionario, dict):
        raise TypeError("respuesta_desde_dict requiere un diccionario.")

    payload = dict(diccionario)
    tipo_respuesta = str(payload.get("tipo") or tipo or "legacy")
    formato_original = str(payload.get("formato") or "dict")
    secciones = []

    for seccion in payload.get("secciones", []):
        if isinstance(seccion, SeccionRespuesta):
            secciones.append(seccion)
        elif isinstance(seccion, dict):
            secciones.append(
                SeccionRespuesta(
                    titulo=str(seccion.get("titulo", "")),
                    contenido=seccion.get("contenido"),
                    formato=str(
                        seccion.get("formato")
                        or seccion.get("tipo")
                        or "markdown"
                    ),
                )
            )

    tablas_academicas = (
        ("contenidos", "Qué estudiar" if tipo_respuesta == "estudio" else "Unidades y contenidos"),
        ("plan", "Plan sugerido"),
        ("prerrequisitos", "Prerrequisitos académicos"),
        ("bibliografia", "Bibliografía"),
        ("evaluaciones", "Evaluaciones detectadas"),
    )
    claves_existentes = {
        seccion.titulo for seccion in secciones if seccion.formato == "tabla"
    }
    for clave, titulo_seccion in tablas_academicas:
        contenido = payload.get(clave)
        if contenido and titulo_seccion not in claves_existentes:
            secciones.append(
                SeccionRespuesta(
                    titulo=titulo_seccion,
                    contenido=list(contenido),
                    formato="tabla",
                )
            )

    return RespuestaChatbot(
        tipo=tipo_respuesta,
        titulo=payload.get("titulo"),
        resumen=str(payload.get("resumen", "")),
        secciones=secciones,
        evidencias=[
            _evidencia_desde_valor(item)
            for item in payload.get("evidencias", [])
        ],
        fuentes=[str(item) for item in payload.get("fuentes", [])],
        recomendacion=payload.get("recomendacion") or None,
        advertencias=[
            str(item) for item in payload.get("advertencias", [])
        ],
        metadata={
            "formato_original": formato_original,
            "payload_original": payload,
        },
    )


def normalizar_respuesta(respuesta, tipo="legacy"):
    if isinstance(respuesta, RespuestaChatbot):
        return respuesta
    if isinstance(respuesta, dict):
        return respuesta_desde_dict(respuesta, tipo=tipo)
    return respuesta_desde_markdown(respuesta, tipo=tipo)


def adaptar_contrato_respuesta(respuesta, tipo):
    """Alias compatible con el flujo conversacional existente."""
    return normalizar_respuesta(respuesta, tipo=tipo)

