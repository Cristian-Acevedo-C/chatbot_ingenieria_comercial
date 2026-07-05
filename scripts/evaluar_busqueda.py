"""Evaluación offline de la búsqueda documental (TF-IDF vs embeddings/auto).

Ejecuta un conjunto de consultas representativas contra la base documental y
reporta si el primer resultado corresponde al ramo esperado. No toca la app ni
la interfaz; sirve para comparar motores de recuperación de forma reproducible.

Uso:
    python scripts/evaluar_busqueda.py --metodo tfidf
    python scripts/evaluar_busqueda.py --metodo auto
    python scripts/evaluar_busqueda.py --metodo embeddings
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# Asegura que la raíz del proyecto esté en sys.path al ejecutar como script.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import DATA_DIR  # noqa: E402
from rag.busqueda import buscar_documentos, fuente_fragmento  # noqa: E402
from rag.indice import construir_indice_documental  # noqa: E402

CONSULTAS_DEFECTO = ROOT / "eval" / "consultas_busqueda.csv"
SALIDA_DEFECTO = ROOT / "eval" / "resultados_busqueda.csv"
COLUMNAS_SALIDA = [
    "metodo",
    "pregunta",
    "ramo_esperado",
    "ramo_recuperado_top1",
    "score_top1",
    "fuente_top1",
    "coincide_ramo",
    "top_k_resumen",
]


def cargar_chunks():
    ruta = DATA_DIR / "document_chunks.csv"
    if not ruta.exists() or ruta.stat().st_size == 0:
        raise SystemExit(f"[ERROR] No se encontró o está vacío: {ruta}")
    chunks = pd.read_csv(ruta)
    if chunks.empty:
        raise SystemExit("[ERROR] document_chunks.csv no contiene registros.")
    return chunks


def evaluar(metodo, top_k, umbral, consultas_path, salida_path):
    chunks = cargar_chunks()
    consultas = pd.read_csv(consultas_path)

    textos = tuple(chunks["texto"].fillna("").astype(str))
    metodo_real, modelo, matriz = construir_indice_documental(textos, metodo=metodo)
    if metodo in {"auto", "embeddings"} and metodo_real != "embeddings":
        print(
            f"[AVISO] Se solicitó '{metodo}' pero se usó '{metodo_real}': "
            "sentence-transformers no está disponible o el modelo no cargó. "
            "Se continúa con el fallback TF-IDF."
        )

    filas = []
    aciertos = 0
    for _, consulta in consultas.iterrows():
        pregunta = str(consulta["pregunta"])
        ramo_esperado = str(consulta["ramo_esperado"])
        resultados = buscar_documentos(
            chunks, pregunta, modelo, matriz, top_k=top_k, umbral=umbral
        )
        if resultados.empty:
            fila = {
                "metodo": metodo_real,
                "pregunta": pregunta,
                "ramo_esperado": ramo_esperado,
                "ramo_recuperado_top1": "",
                "score_top1": "",
                "fuente_top1": "",
                "coincide_ramo": False,
                "top_k_resumen": "",
            }
        else:
            top1 = resultados.iloc[0]
            ramo_top1 = str(top1["codigo_ramo"])
            coincide = ramo_top1 == ramo_esperado
            aciertos += int(coincide)
            resumen = "; ".join(
                f"{fila['codigo_ramo']}:{float(fila['score']):.3f}"
                for _, fila in resultados.iterrows()
            )
            fila = {
                "metodo": metodo_real,
                "pregunta": pregunta,
                "ramo_esperado": ramo_esperado,
                "ramo_recuperado_top1": ramo_top1,
                "score_top1": round(float(top1["score"]), 4),
                "fuente_top1": fuente_fragmento(top1),
                "coincide_ramo": coincide,
                "top_k_resumen": resumen,
            }
        filas.append(fila)

    salida = pd.DataFrame(filas, columns=COLUMNAS_SALIDA)
    salida_path.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(salida_path, index=False, encoding="utf-8")

    total = len(salida)
    precision = aciertos / total if total else 0.0
    print(f"Motor efectivo: {metodo_real}")
    print(f"Consultas evaluadas: {total}")
    print(f"Aciertos de ramo (top-1): {aciertos}/{total} ({precision:.0%})")
    print(f"Resultados guardados en: {salida_path}")
    return salida


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metodo",
        choices=["tfidf", "auto", "embeddings"],
        default="tfidf",
        help="Motor de búsqueda a evaluar.",
    )
    parser.add_argument("--top-k", type=int, default=4, help="Resultados por consulta.")
    parser.add_argument(
        "--umbral",
        type=float,
        default=0.0,
        help="Umbral mínimo de similitud (0 para recuperar siempre el top-1).",
    )
    parser.add_argument("--consultas", type=Path, default=CONSULTAS_DEFECTO)
    parser.add_argument("--salida", type=Path, default=SALIDA_DEFECTO)
    args = parser.parse_args()
    evaluar(args.metodo, args.top_k, args.umbral, args.consultas, args.salida)


if __name__ == "__main__":
    main()
