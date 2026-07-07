# Asistente Académico Multicarrera

MVP local desarrollado con Streamlit para consultar información académica sintética y recuperar evidencia desde programas oficiales de asignatura de Ingeniería Comercial e Ingeniería Civil Industrial (UDLA).

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
Comercial: manifiestos + PDFs ------> data/document_chunks.csv
Otras carreras: metadata + PDFs ---> data/carreras/<slug>/indice/document_chunks.csv
                                              |
                                              v
                           carga y filtro por carrera
                                              |
                                              v
                                  app.py / Streamlit
   - Índice TF-IDF en memoria (similitud coseno)
   - Un índice solo para st.session_state["carrera"]
   - Alumnos, malla, historial y prerrequisitos aislados por carrera
   - Clasificación del tipo de pregunta
   - Respuesta académica estructurada + evidencia en expander
```

- `ingest.py` valida los manifiestos, extrae texto con `pypdf`, divide el contenido en fragmentos con solapamiento y genera un CSV documental independiente por carrera.
- `scripts/extract_prerrequisitos.py` recorre los fragmentos y genera `data/prerrequisitos.csv`. Es deliberadamente conservador: solo crea relaciones hacia ramos que existen en `data/malla.csv`, ya sea por código oficial (confianza alta) o por nombre oficial (confianza media). Nunca infiere prerrequisitos por semestre, posición en la malla ni parecido.
- `app.py` carga los corpora, conserva la columna `carrera`, filtra por `st.session_state["carrera"]` antes de construir el índice y vuelve a aplicar el filtro al buscar. La evidencia textual del PDF se muestra con el nombre de archivo usado, por ejemplo, `Fuente: EIN908.pdf`.

## Estructura del proyecto

```text
chatbot_ingenieria_comercial/
|-- app.py                          # Orquestador Streamlit
|-- ingest.py                       # Pipeline local de ingesta de PDFs
|-- requirements.txt                # Dependencias de ejecución (runtime)
|-- requirements-dev.txt            # Runtime + herramientas de test
|-- config/                         # Constantes y esquemas de datos
|-- utils/                          # Utilidades puras (p. ej. normalización de texto)
|-- services/                       # Carga de CSV y reglas de prerrequisitos
|-- rag/                            # Índice TF-IDF, búsqueda y extractores de PDF
|-- chatbot/                        # Clasificación, contrato tipado y familias de respuesta
|   |-- intenciones.py              # Clasificación heurística de consultas
|   |-- contratos.py                # RespuestaChatbot / SeccionRespuesta / Evidencia
|   |-- conversacion.py             # Estado de sesión y flujo conversacional
|   `-- respuestas/                 # Enrutador y respuestas por tema
|-- ui/                             # Componentes, paneles y estilos de Streamlit
|-- tests/                          # Suite de pytest
|-- scripts/
|   |-- extract_prerrequisitos.py   # Genera data/prerrequisitos.csv desde los fragmentos
|   |-- generar_datos_sinteticos_ici.py # Genera la capa académica demo ICI
|   |-- smoke_streamlit.py          # Script de humo manual de Streamlit
|   `-- download_programas_udla.ps1 # Descarga auxiliar de programas (opcional)
|-- data/
|   |-- alumnos.csv
|   |-- historial_academico.csv
|   |-- malla.csv
|   |-- ramos_inscritos.csv
|   |-- prerrequisitos.csv          # Generado desde los PDFs (ver más abajo)
|   |-- documentos_malla.csv        # Manifiesto de PDFs de malla
|   |-- documentos_ramos.csv        # Manifiesto de PDFs de programas
|   |-- document_chunks.csv         # Corpus histórico de Ingeniería Comercial
|   `-- carreras/
|       `-- ingenieria_civil_industrial/
|           |-- academico/          # Alumnos, malla, inscripciones, historial y prerrequisitos
|           |-- pdf/programas/      # 51 programas disponibles
|           |-- pdf/malla/          # Malla oficial UDLA 2025
|           |-- metadata/           # 52 registros: 51 disponibles y 1 pendiente
|           `-- indice/document_chunks.csv
|-- documentos/
|   |-- malla/
|   `-- semestre_01/ ... semestre_10/
|-- assets/                         # Logos institucionales UDLA
`-- README.md
```

## Datos utilizados

El estado actual del MVP contiene:

- 18 alumnos sintéticos: 8 de Ingeniería Comercial y 10 de Ingeniería Civil Industrial;
- 52 ramos por cada malla curricular;
- 52 programas de asignatura en PDF;
- 2 documentos PDF de malla;
- 870 fragmentos en `data/document_chunks.csv`;
- 51 programas PDF y 875 fragmentos de Ingeniería Civil Industrial;
- 1 programa pendiente de Ingeniería Civil Industrial (`FIS504`), registrado sin contenido inventado;
- 74 filas en `data/prerrequisitos.csv`.
- 79 filas de prerrequisitos ICI extraídas de sus programas: 70 relaciones, 8 ramos sin prerrequisito explícito y `FIS504` como no detectado.

La malla ICI usada por esta demo corresponde a la versión oficial UDLA 2025 que coincide con los 52 códigos descargados; se conserva localmente como `pdf/malla/malla_ici_2025.pdf`. No debe confundirse con versiones posteriores del plan de estudios.

### Prerrequisitos

Los prerrequisitos están **generados automáticamente** desde los programas indexados mediante `scripts/extract_prerrequisitos.py`. Comercial conserva `data/prerrequisitos.csv`; Civil Industrial usa su archivo separado bajo `data/carreras/ingenieria_civil_industrial/academico/`.

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

Dependencias de ejecución (`requirements.txt`): Streamlit, pandas, pypdf y scikit-learn. Las herramientas de desarrollo y test (pytest) se listan aparte en `requirements-dev.txt` para mantener liviano el entorno de ejecución. No se usa `python-dotenv` (la aplicación no consume variables de entorno) ni OpenAI/Claude/LangChain/ChromaDB.

## Instalación

Desde la carpeta del proyecto, crea y activa un entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Para **uso normal** (solo ejecutar la aplicación):

```powershell
python -m pip install -r requirements.txt
```

Para **desarrollo** (incluye las herramientas de test):

```powershell
python -m pip install -r requirements-dev.txt
```

### Búsqueda semántica opcional (embeddings)

La búsqueda documental usa **TF-IDF** por defecto. De forma opcional puede activarse
una capa de **embeddings** (modelo local `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`)
que mejora la recuperación semántica, manteniendo TF-IDF como *fallback* automático.

```powershell
# Activar: instalar la dependencia opcional
python -m pip install -r requirements-embeddings.txt
```

- Con la dependencia instalada, el modo `auto` (por defecto) usa embeddings y, si el
  modelo no carga, vuelve a TF-IDF sin romper la aplicación.
- Para **forzar** un motor, define la variable de entorno `CHATBOT_BUSQUEDA` con
  `tfidf`, `embeddings` o `auto`.
- La barra lateral indica el motor activo ("Búsqueda semántica activa" o
  "Modo compatibilidad TF-IDF").

> En Streamlit Community Cloud, **no** incluyas `sentence-transformers` en
> `requirements.txt` salvo que aceptes la descarga del modelo (~470 MB) y un mayor
> uso de memoria; el runtime gratuito puede quedar ajustado.

## Regenerar las bases locales (opcional)

Las bases ya están incluidas en `data/`. Para regenerarlas voluntariamente:

```powershell
# 1) Base documental desde los PDFs
python -u ingest.py

# 1b) Corpus separado de Ingeniería Civil Industrial
python -u ingest.py --carrera ingenieria_civil_industrial

# 2) Capa académica sintética ICI desde la malla oficial y el índice
python -u scripts/generar_datos_sinteticos_ici.py

# 3) Prerrequisitos desde los fragmentos indexados
python -u scripts/extract_prerrequisitos.py
python -u scripts/extract_prerrequisitos.py --carrera ingenieria_civil_industrial
```

Ambos scripts validan sus insumos y **no sobrescriben** el CSV existente si no logran generar registros.

## Agregar documentos de una nueva carrera

Cada carrera adicional vive bajo un `slug` propio y genera un corpus independiente. Por ejemplo, para `ingenieria_en_informatica`:

```text
data/carreras/ingenieria_en_informatica/
|-- pdf/programas/
|   |-- INF100.pdf
|   `-- INF200.pdf
`-- metadata/
    `-- metadata_programas.csv
```

El manifiesto debe usar exactamente estas columnas:

```csv
carrera,codigo_asignatura,nombre_archivo,ruta_archivo,tipo_documento,estado
Ingeniería en Informática,INF100,INF100.pdf,data/carreras/ingenieria_en_informatica/pdf/programas/INF100.pdf,programa_asignatura,disponible
Ingeniería en Informática,INF200,INF200.pdf,data/carreras/ingenieria_en_informatica/pdf/programas/INF200.pdf,programa_asignatura,pendiente
```

- `estado` solo admite `disponible` o `pendiente`.
- Un ramo pendiente se registra en metadata, pero no se crea un PDF ni un fragmento ficticio.
- El nombre del ramo se extrae del texto declarado en el PDF; si no hay PDF, se conserva únicamente el código comprobable.
- `ruta_archivo` debe ser relativa a la raíz del proyecto.

Luego reconstruye solo esa carrera:

```powershell
python -u ingest.py --carrera ingenieria_en_informatica
```

El resultado queda en `data/carreras/ingenieria_en_informatica/indice/document_chunks.csv`. Al reiniciar Streamlit, el selector **Carrera documental** la descubre automáticamente y mantiene el valor activo en `st.session_state["carrera"]`.

Para habilitar también la ficha estudiantil de una nueva carrera, agrega bajo `academico/` los cinco CSV (`alumnos.csv`, `malla.csv`, `ramos_inscritos.csv`, `historial_academico.csv` y `prerrequisitos.csv`) con una columna `carrera` consistente. La aplicación los descubre, combina y filtra automáticamente.

## Ejecutar la aplicación

```powershell
python -m streamlit run app.py --server.fileWatcherType none
```

Luego abre [http://localhost:8501](http://localhost:8501). En la barra lateral, el selector **Carrera documental** determina de forma excluyente qué corpus se indexa y consulta.

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
- ¿Cuáles son los aprendizajes esperados de EIN908?
- ¿Qué unidades tiene Organización y Planificación de la Producción?
- ¿Qué bibliografía recomienda EIN971?
- ¿Cómo se evalúa EIN908?
- ¿Qué contenidos tiene FIS504? (debe informar que no hay evidencia suficiente)
- ¿Qué ramos tengo inscritos? (seleccionando un alumno ICI)
- ¿Tengo alguna alerta académica? (prueba con Martín Sepúlveda)

La selección opcional de un ramo inscrito en la barra lateral sirve como contexto cuando la pregunta no menciona explícitamente una asignatura.

## Pruebas y validación

Con las dependencias de desarrollo instaladas (`requirements-dev.txt`):

```powershell
# Suite de pruebas
pytest -q

# Validación de sintaxis del orquestador
python -m py_compile app.py
```

La suite cubre clasificación de intención, búsqueda documental, extractores de programas, reglas de prerrequisitos y el contrato tipado de respuestas.

## Evaluación offline de búsqueda documental

Para comparar los motores de recuperación de forma reproducible (sin abrir la app)
hay un conjunto de consultas representativas en `eval/consultas_busqueda.csv` y un
script que mide si el primer resultado corresponde al ramo esperado:

```powershell
python scripts/evaluar_busqueda.py --metodo tfidf
python scripts/evaluar_busqueda.py --metodo auto
python scripts/evaluar_busqueda.py --metodo embeddings
```

El script escribe el detalle en `eval/resultados_busqueda.csv` (ignorado por git,
regenerable) e imprime la precisión de ramo en el top-1. Si se pide `embeddings`/`auto`
y la dependencia no está disponible, avisa y continúa con el fallback TF-IDF.

## Modo demostración y roles

La aplicación está pensada como **demo institucional** con datos sintéticos/locales.
La barra lateral incluye un selector de **rol simulado** (no hay autenticación real):

- **Estudiante**: flujo académico completo (chat, ficha, prerrequisitos, evidencia).
- **Coordinación demo**: métricas agregadas (alumnos, ramos, inscripciones,
  relaciones de prerrequisitos, alertas, cobertura documental).
- **Admin demo**: diagnóstico de solo lectura de los archivos de datos (CSV
  presentes, filas, columnas faltantes), assets y motor de búsqueda activo. No
  permite editar ni subir archivos.

Además, el sidebar muestra un indicador de **modo demostración**, un expander
**«Estado de la sesión»** con métricas locales (consultas realizadas, última
intención/ramo, motor activo, consultas sin evidencia) y un expander
**«Cobertura documental»**.

## Registro de interacciones (demo)

La aplicación guarda un **registro anónimo** de cada turno de conversación en una
base **SQLite local**: `data/interacciones_demo.db` (ignorada por git; se crea
sola en la primera interacción). Sirve para responder de forma concreta *«¿dónde
quedan guardadas las interacciones?»* sin depender de servicios externos.

**Qué se guarda** (tabla `interacciones`):

| Campo | Descripción |
| --- | --- |
| `id` | Identificador autoincremental de la fila. |
| `timestamp` | Fecha/hora UTC del registro (ISO 8601). |
| `session_id` | UUID anónimo generado en `st.session_state` (no identifica a nadie). |
| `pregunta_usuario` | Texto de la consulta. |
| `respuesta_bot` | Texto plano de la respuesta entregada. |
| `intencion_detectada` | Intención clasificada (p. ej. `ramos_inscritos`, `documental`). |
| `carrera_contexto` | Carrera activa al momento de la consulta. |
| `fuente_respuesta` | Origen de la respuesta (conversacional, documental, etc.). |
| `requiere_derivacion` | `1` si la respuesta sugiere validar con canales oficiales. |
| `feedback_utilidad` | `positivo` / `negativo` / vacío, según el feedback del usuario. |
| `comentario_feedback` | Comentario opcional («¿qué faltó?»). |

**Qué NO se guarda:** nombre real, RUT, correo, teléfono ni ningún dato personal
sensible. No existen columnas para esa información. Bajo el chat se muestra un
aviso pidiendo no ingresar datos personales sensibles, ya que el texto de la
consulta es lo único que podría contenerlos por escrito.

**Feedback:** debajo de cada respuesta aparece *«¿Te sirvió esta respuesta?»* con
botones 👍/👎 y un campo opcional; el feedback actualiza la fila correspondiente.

**Panel de métricas:** la vista **Coordinación demo** muestra el total de
interacciones, feedback positivo/negativo, consultas que requieren derivación,
preguntas por intención y por carrera, y las últimas 5 preguntas anonimizadas.
El sidebar también incluye un contador rápido en «Estado de la sesión».

> **Persistencia en Streamlit Community Cloud:** el sistema de archivos es
> **efímero**. La base persiste durante la ejecución, pero puede reiniciarse en
> cada reinicio o redeploy del contenedor. Para una versión institucional
> conviene migrar el registro a una **base externa segura** (PostgreSQL,
> Supabase, una hoja de cálculo institucional gobernada, o similar) con control
> de acceso y retención definida. El módulo `services/interacciones.py` aísla el
> almacenamiento para facilitar esa migración.

El guardado es **defensivo**: si la escritura falla, la aplicación sigue
funcionando y la conversación no se interrumpe. La ruta puede sobrescribirse con
la variable de entorno `CHATBOT_INTERACCIONES_DB` (los tests la usan para no
tocar `data/`).

## Despliegue en Streamlit Community Cloud

La aplicación puede publicarse sin cambios en [Streamlit Community Cloud](https://streamlit.io/cloud):

1. Sube el repositorio a GitHub y entra a *Community Cloud* → **New app**.
2. Selecciona el repositorio y la rama `main`.
3. Indica `app.py` como archivo principal (*Main file path*).
4. Community Cloud instala automáticamente las dependencias desde `requirements.txt`.
5. La configuración base (`.streamlit/config.toml`) ya está versionada; no requiere ajustes.

La demo usa exclusivamente datos sintéticos incluidos en `data/`. **No subas datos personales ni información académica real a un despliegue público.** Los secretos, si alguna vez se necesitan, se cargan desde `.streamlit/secrets.toml` (ignorado por git, con plantilla en `.streamlit/secrets.toml.example`) y nunca se comitean.

## Limitaciones actuales

- No se usa un modelo generativo: las respuestas son extractivas y estructuradas a partir del PDF y los CSV, no una síntesis semántica avanzada.
- La extracción de contenidos, bibliografía y evaluaciones depende del formato del programa; puede quedar incompleta en algunos ramos y, cuando no hay estructura reconocible, se informa como no disponible.
- El umbral TF-IDF es una heurística y puede requerir calibración con más preguntas evaluadas.
- No hay OCR para PDFs escaneados o compuestos solo por imágenes.
- Los prerrequisitos "No detectado" no se completan automáticamente: requieren revisión manual contra el programa oficial.
- Las alertas son orientativas y no reemplazan los sistemas ni reglamentos oficiales de la universidad.
- No hay autenticación real (los roles son simulados).
- La persistencia de interacciones usa SQLite local y es **efímera** en Streamlit Community Cloud; no sustituye a una base institucional gobernada (ver [Registro de interacciones](#registro-de-interacciones-demo)).

## Mejoras futuras

- validar manualmente los 3 prerrequisitos "No detectado" contra el programa oficial;
- incorporar OCR con trazabilidad de páginas para PDFs sin texto;
- dividir documentos por secciones académicas y no solo por longitud;
- crear un conjunto de evaluación para medir precisión de recuperación;
- añadir pruebas automatizadas de datos, reglas e interfaz.

## Roadmap

Las etapas futuras (piloto anonimizado, panel de carga de programas, base de datos
real, roles reales, integración WhatsApp y analítica institucional) están descritas
en [`docs/roadmap.md`](docs/roadmap.md). La propuesta de modelo de datos para una
migración a SQLite/PostgreSQL está en [`docs/arquitectura_datos.md`](docs/arquitectura_datos.md).

## Uso académico responsable

Este repositorio es un prototipo demostrativo que opera **solo con datos sintéticos y archivos locales**. **No reemplaza la información oficial de la coordinación académica ni del sistema de registro académico de la universidad.** Toda recomendación debe contrastarse con los programas completos, la malla oficial y la orientación académica institucional. La aplicación no inventa información: cuando un dato no puede extraerse con seguridad, lo declara explícitamente.
