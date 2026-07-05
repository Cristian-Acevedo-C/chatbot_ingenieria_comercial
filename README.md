# Asistente Académico de Ingeniería Comercial

MVP local desarrollado con Streamlit para consultar información académica sintética y recuperar evidencia desde programas oficiales de asignatura de Ingeniería Comercial (UDLA).

El proyecto funciona completamente en el equipo local. La búsqueda documental utiliza TF-IDF y similitud coseno; no se conecta con OpenAI, Claude, LangChain, otros modelos de lenguaje ni una base vectorial externa.

## Objetivo

El asistente reconoce el tipo de pregunta y responde como guía académica —no como un buscador que pega fragmentos de PDF—. Cubre consultas como:

- ramos inscritos de un alumno;
- sede, jornada y semestre actual;
- alertas básicas a partir del historial académico;
- **qué estudiar** para un ramo (guía con unidades, plan y prerrequisitos);
- contenidos, bibliografía y evaluaciones detectados en el programa;
- prerrequisitos de un ramo y su estado según el historial;
- mapa completo de prerrequisitos de la malla.

Los datos personales del MVP son sintéticos. La información académica es **extractiva**: se obtiene desde los PDF cargados y desde los CSV locales. Cuando algo no puede extraerse con seguridad, la aplicación lo indica ("Información no disponible en los documentos cargados") en lugar de inventarlo.

## Arquitectura

```text
Manifiestos CSV + PDFs
          |
          v
      ingest.py  ------------------>  data/document_chunks.csv
                                              |
                                              v
                           scripts/extract_prerrequisitos.py
                                              |
                                              v
                                   data/prerrequisitos.csv
                                              |
          +-----------------------------------+
          v
   app.py / Streamlit
   - Índice TF-IDF en memoria (similitud coseno)
   - Clasificación del tipo de pregunta
   - Respuesta académica estructurada + evidencia en expander
```

- `ingest.py` valida los manifiestos, extrae texto con `pypdf`, divide el contenido en fragmentos con solapamiento y genera el CSV documental.
- `scripts/extract_prerrequisitos.py` recorre los fragmentos y genera `data/prerrequisitos.csv`. Es deliberadamente conservador: solo crea relaciones hacia ramos que existen en `data/malla.csv`, ya sea por código oficial (confianza alta) o por nombre oficial (confianza media). Nunca infiere prerrequisitos por semestre, posición en la malla ni parecido.
- `app.py` carga los datos, construye una vez el índice TF-IDF mediante la caché de Streamlit, clasifica la pregunta y arma una respuesta académica. La evidencia textual del PDF se muestra en un expander, recortada, como respaldo de la respuesta (no como respuesta principal).

## Estructura del proyecto

```text
chatbot_ingenieria_comercial/
|-- app.py                          # Aplicación Streamlit
|-- ingest.py                       # Pipeline local de ingesta de PDFs
|-- requirements.txt                # Dependencias utilizadas
|-- scripts/
|   |-- extract_prerrequisitos.py   # Genera data/prerrequisitos.csv desde los fragmentos
|   `-- download_programas_udla.ps1 # Descarga auxiliar de programas (opcional)
|-- data/
|   |-- alumnos.csv
|   |-- historial_academico.csv
|   |-- malla.csv
|   |-- ramos_inscritos.csv
|   |-- prerrequisitos.csv          # Generado desde los PDFs (ver más abajo)
|   |-- documentos_malla.csv        # Manifiesto de PDFs de malla
|   |-- documentos_ramos.csv        # Manifiesto de PDFs de programas
|   `-- document_chunks.csv         # Base documental fragmentada
|-- documentos/
|   |-- malla/
|   `-- semestre_01/ ... semestre_10/
|-- assets/                         # Logos institucionales UDLA
`-- README.md
```

## Datos utilizados

El estado actual del MVP contiene:

- 8 alumnos sintéticos;
- 52 ramos en la malla curricular;
- 52 programas de asignatura en PDF;
- 2 documentos PDF de malla;
- 870 fragmentos en `data/document_chunks.csv`;
- 74 filas en `data/prerrequisitos.csv`.

### Prerrequisitos

`data/prerrequisitos.csv` está **generado automáticamente** desde los programas indexados mediante `scripts/extract_prerrequisitos.py`. El estado actual reporta:

- 39 ramos con prerrequisito detectado;
- 10 ramos sin prerrequisito explícito en el programa;
- 3 ramos cuyo prerrequisito no pudo detectarse de forma confiable;
- 61 relaciones de prerrequisito válidas (todas hacia ramos existentes en la malla, sin autorreferencias).

Para los ramos marcados como "No detectado", la aplicación muestra una advertencia informativa y no infiere ninguna relación. El estado de cada prerrequisito (Aprobado, Cursando, Reprobado, Pendiente o No aplica) se calcula únicamente con `data/historial_academico.csv`.

### Contenidos de los programas

La respuesta "¿Qué debería estudiar?" arma una tabla de unidades a partir de la sección de contenidos del programa. La extracción es estructural (basada en el formato del PDF) y reconoce contenidos en 51 de los 52 ramos; el restante (`TDE400`) no expone una sección de contenidos extraíble y la aplicación lo informa como "Información no disponible".

Uno de los documentos de malla, `malla_alumno_sistema.pdf`, no posee texto extraíble mediante `pypdf`. La ingesta lo reporta como advertencia y continúa; no se aplica OCR en esta fase.

## Requisitos

- Python 3.10 o superior.
- PowerShell para los ejemplos de Windows.

Dependencias de ejecución: Streamlit, pandas, pypdf y scikit-learn. No se usa `python-dotenv` (la aplicación no consume variables de entorno) ni OpenAI/Claude/LangChain/ChromaDB.

## Instalación

Desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Regenerar las bases locales (opcional)

Las bases ya están incluidas en `data/`. Para regenerarlas voluntariamente:

```powershell
# 1) Base documental desde los PDFs
python -u ingest.py

# 2) Prerrequisitos desde los fragmentos indexados
python -u scripts/extract_prerrequisitos.py
```

Ambos scripts validan sus insumos y **no sobrescriben** el CSV existente si no logran generar registros.

## Ejecutar la aplicación

```powershell
python -m streamlit run app.py --server.fileWatcherType none
```

Luego abre [http://localhost:8501](http://localhost:8501). La barra lateral debe mostrar 8 alumnos, 52 ramos y 870 fragmentos, además del estado de los prerrequisitos cargados.

## Preguntas de prueba

- ¿Qué ramos tengo inscritos?
- ¿Cuál es mi sede y jornada?
- ¿Estoy atrasado o tengo alguna alerta?
- ¿Qué debería estudiar para Microeconomía I?
- ¿Qué contenidos tiene Econometría?
- ¿Qué bibliografía tiene Contabilidad I?
- ¿Qué evaluaciones tiene Microeconomía I?
- ¿Qué prerrequisitos tiene Microeconomía II?
- ¿Puedo cursar Econometría?
- Muéstrame todos los prerrequisitos

La selección opcional de un ramo inscrito en la barra lateral sirve como contexto cuando la pregunta no menciona explícitamente una asignatura.

## Limitaciones actuales

- No se usa un modelo generativo: las respuestas son extractivas y estructuradas a partir del PDF y los CSV, no una síntesis semántica avanzada.
- La extracción de contenidos, bibliografía y evaluaciones depende del formato del programa; puede quedar incompleta en algunos ramos y, cuando no hay estructura reconocible, se informa como no disponible.
- El umbral TF-IDF es una heurística y puede requerir calibración con más preguntas evaluadas.
- No hay OCR para PDFs escaneados o compuestos solo por imágenes.
- Los prerrequisitos "No detectado" no se completan automáticamente: requieren revisión manual contra el programa oficial.
- Las alertas son orientativas y no reemplazan los sistemas ni reglamentos oficiales de la universidad.
- No existe persistencia de conversaciones ni autenticación.

## Mejoras futuras

- validar manualmente los 3 prerrequisitos "No detectado" contra el programa oficial;
- incorporar OCR con trazabilidad de páginas para PDFs sin texto;
- dividir documentos por secciones académicas y no solo por longitud;
- crear un conjunto de evaluación para medir precisión de recuperación;
- añadir pruebas automatizadas de datos, reglas e interfaz.

## Uso académico responsable

Este repositorio es un prototipo demostrativo con datos sintéticos. Toda recomendación debe contrastarse con los programas completos, la malla oficial y la orientación académica institucional. La aplicación no inventa información: cuando un dato no puede extraerse con seguridad, lo declara explícitamente.
