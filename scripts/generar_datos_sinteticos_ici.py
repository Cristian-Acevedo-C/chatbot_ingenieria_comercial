"""Genera la capa académica demo de Ingeniería Civil Industrial.

La ubicación semestral y los nombres provienen de la malla oficial UDLA 2025.
Los alumnos, notas, inscripciones e historiales son explícitamente sintéticos.
No genera contenidos ni prerrequisitos; estos últimos se extraen por separado
desde los programas PDF con ``scripts/extract_prerrequisitos.py``.
"""

import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SLUG = "ingenieria_civil_industrial"
CARRERA = "Ingeniería Civil Industrial"
BASE_CARRERA = BASE_DIR / "data" / "carreras" / SLUG
INDICE_PATH = BASE_CARRERA / "indice" / "document_chunks.csv"
OUTPUT_DIR = BASE_CARRERA / "academico"
FUENTE_MALLA = (
    "https://admision.udla.cl/wp-content/uploads/2021/06/"
    "Carrera-Ingenieria-Civil-Industrial-UDLA-2025.pdf"
)

MALLA_POR_SEMESTRE = {
    1: [
        ("MAT107", "Introducción a la Matemática para la Ingeniería"),
        ("ING102", "Introducción a la Computación"),
        ("ING120", "Taller Fundamentos de la Ingeniería"),
        ("ING110", "Innovación y Tecnología"),
        ("ING103", "Economía Circular y Desarrollo Sostenible"),
    ],
    2: [
        ("MAT170", "Cálculo Diferencial"),
        ("MAT140", "Álgebra I"),
        ("AEA220", "Economía"),
        ("AEA240", "Emprendimiento y Negocios"),
        ("ING400", "Tecnologías y Creación de Valor"),
    ],
    3: [
        ("MAT390", "Cálculo Integral"),
        ("MAT141", "Álgebra II"),
        ("FIS211", "Mecánica"),
        ("AEA131", "Administración de Negocios"),
        ("AEA214", "Microeconomía I"),
    ],
    4: [
        ("MAT402", "Cálculo Superior"),
        ("MAT450", "Ecuaciones Diferenciales"),
        ("FIS605", "Electromagnetismo y Ondas"),
        ("QUI511", "Química Industrial"),
        ("AEA316", "Macroeconomía I"),
    ],
    5: [
        ("FIS504", "Física Experimental"),
        ("AES500", "Probabilidad y Estadística"),
        ("EIN793", "Investigación de Operaciones"),
        ("EIN811", "Procesos de Negocios"),
        ("EIN103", "Contabilidad y Control de Gestión"),
    ],
    6: [
        ("FIS611", "Termodinámica"),
        ("EIN601", "Métodos Cuantitativos y Optimización"),
        ("ACI777", "Análisis de Datos"),
        ("EIN970", "Procesos Industriales"),
        ("AEA504", "Introducción a las Finanzas"),
    ],
    7: [
        ("LCE001", "Inglés I"),
        ("AEA555", "Preparación y Evaluación de Proyectos"),
        ("ACI800", "Analítica de Negocios (Business Analytics)"),
        ("EIN990", "Modelos de Simulación"),
        ("EIN830", "Sustentabilidad"),
        ("EIN611", "Organización y Planificación de la Producción"),
    ],
    8: [
        ("LCE002", "Inglés II"),
        ("AEA694", "Finanzas Corporativas"),
        ("EIN903", "Administración de Operaciones"),
        ("EIN891", "Gestión de Servicios"),
        ("EIN971", "Gestión de Proyectos"),
        ("EIN605", "Práctica Operacional"),
    ],
    9: [
        ("LCE003", "Inglés III"),
        ("AEA920", "Gestión de Emprendimiento y Nuevos Negocios"),
        ("CAM820", "Sistemas Integrados de Gestión"),
        ("EIN906", "Industria 4.0"),
        ("EIN908", "Marketing"),
        ("EIN995", "Proyecto de Título I"),
    ],
    10: [
        ("AEA325", "Dirección Estratégica"),
        ("EIN106", "Innovación en la Industria"),
        ("EIN606", "Práctica Profesional"),
        ("EIN996", "Proyecto de Título II"),
    ],
}

ALUMNOS = [
    ("2001", "Emilia González", "La Florida", 1),
    ("2002", "Tomás Araya", "Santiago Centro", 2),
    ("2003", "Isidora Navarro", "Providencia", 3),
    ("2004", "Benjamín Castro", "La Florida", 4),
    ("2005", "Catalina Vega", "Santiago Centro", 5),
    ("2006", "Vicente Morales", "Providencia", 6),
    ("2007", "Fernanda Riquelme", "Viña del Mar", 7),
    ("2008", "Martín Sepúlveda", "La Florida", 8),
    ("2009", "Antonia Salazar", "Santiago Centro", 9),
    ("2010", "Joaquín Fuentes", "Providencia", 10),
]


def extraer_creditos(chunks, codigo):
    filas = chunks[chunks["codigo_ramo"].astype(str).eq(codigo)]
    if filas.empty:
        return ""
    texto = " ".join(filas.head(2)["texto"].fillna("").astype(str))
    coincidencia = re.search(
        r"Créditos\s+Totales\s*\(SCUDLA\)\s*(\d+)", texto, flags=re.IGNORECASE
    )
    return int(coincidencia.group(1)) if coincidencia else ""


def construir_malla(chunks):
    filas = []
    for semestre, ramos in MALLA_POR_SEMESTRE.items():
        for codigo, nombre in ramos:
            filas.append(
                {
                    "carrera": CARRERA,
                    "codigo_ramo": codigo,
                    "nombre_ramo": nombre,
                    "semestre": semestre,
                    "anio": (semestre + 1) // 2,
                    "creditos": extraer_creditos(chunks, codigo),
                    "area": "Por clasificar",
                    "prerrequisito": "",
                    "tipo_codigo": "oficial_desde_malla_2025",
                    "fuente_malla": FUENTE_MALLA,
                }
            )
    return pd.DataFrame(filas)


def construir_alumnos():
    return pd.DataFrame(
        [
            {
                "id_alumno": identificador,
                "nombre": nombre,
                "carrera": CARRERA,
                "sede": sede,
                "jornada": "Diurna",
                "semestre_actual": semestre,
                "origen_datos": "sintético",
            }
            for identificador, nombre, sede, semestre in ALUMNOS
        ]
    )


def construir_inscripciones():
    filas = []
    for identificador, _nombre, _sede, semestre in ALUMNOS:
        for codigo, nombre_ramo in MALLA_POR_SEMESTRE[semestre]:
            filas.append(
                {
                    "carrera": CARRERA,
                    "id_alumno": identificador,
                    "codigo_ramo": codigo,
                    "nombre_ramo": nombre_ramo,
                    "estado": "Inscrito",
                    "origen_datos": "sintético",
                }
            )
    return pd.DataFrame(filas)


def construir_historial():
    filas = []
    for indice_alumno, (identificador, _nombre, _sede, semestre_actual) in enumerate(ALUMNOS):
        for semestre, ramos in MALLA_POR_SEMESTRE.items():
            if semestre > semestre_actual:
                continue
            for indice_ramo, (codigo, nombre_ramo) in enumerate(ramos):
                cursando = semestre == semestre_actual
                estado = "Cursando" if cursando else "Aprobado"
                nota = "" if cursando else round(4.5 + ((indice_alumno + indice_ramo + semestre) % 17) / 10, 1)

                # Un único caso sintético de riesgo para ejercitar las alertas ICI.
                if identificador == "2008" and codigo == "EIN793":
                    estado, nota = "Reprobado", 3.4

                filas.append(
                    {
                        "carrera": CARRERA,
                        "id_alumno": identificador,
                        "codigo_ramo": codigo,
                        "nombre_ramo": nombre_ramo,
                        "estado": estado,
                        "nota": nota,
                        "origen_datos": "sintético",
                    }
                )
    return pd.DataFrame(filas)


def main():
    if not INDICE_PATH.exists():
        raise FileNotFoundError(
            f"No existe {INDICE_PATH}. Ejecuta primero: "
            "python ingest.py --carrera ingenieria_civil_industrial"
        )

    chunks = pd.read_csv(INDICE_PATH)
    malla = construir_malla(chunks)
    alumnos = construir_alumnos()
    inscritos = construir_inscripciones()
    historial = construir_historial()

    if len(malla) != 52 or malla["codigo_ramo"].nunique() != 52:
        raise ValueError("La malla ICI debe contener exactamente 52 ramos únicos.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    salidas = {
        "malla.csv": malla,
        "alumnos.csv": alumnos,
        "ramos_inscritos.csv": inscritos,
        "historial_academico.csv": historial,
    }
    for nombre, datos in salidas.items():
        ruta = OUTPUT_DIR / nombre
        datos.to_csv(ruta, index=False, encoding="utf-8-sig")
        print(f"Creado: {ruta} | filas: {len(datos)}")

    creditos_pendientes = malla.loc[malla["creditos"].eq(""), "codigo_ramo"].tolist()
    print(f"Créditos no disponibles en programas: {', '.join(creditos_pendientes) or 'ninguno'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
