# Asistente Académico Demo

Prototipo conversacional en **Streamlit** que orienta sobre información académica
de **Ingeniería Comercial** e **Ingeniería Civil Industrial** (UDLA): ramos,
malla, prerrequisitos, contenidos de programas y alertas básicas. Funciona por
completo en local, con datos sintéticos y documentos cargados manualmente.

> **Etapa demo/piloto** · Datos sintéticos y locales · Búsqueda documental TF-IDF
> · Sin modelos generativos, sin login, sin integraciones externas.
>
> Este proyecto es un **prototipo demostrativo**. No es un sistema oficial, no
> está validado institucionalmente y no reemplaza la información de coordinación
> académica ni de Registro Académico.

---

## Estado del demo

Una lectura honesta de qué es y qué no es este proyecto hoy:

| | |
|---|---|
| **Qué es** | Un prototipo funcional que responde consultas académicas frecuentes con evidencia extraída de programas de asignatura y datos locales. |
| **Qué no es** | Un sistema oficial, una fuente validada, ni un reemplazo de los canales institucionales. |
| **Qué funciona hoy** | Chat con clasificación de intención, búsqueda documental (TF-IDF), guía de prerrequisitos, feedback por respuesta y registro anónimo de interacciones con panel de métricas. |
| **Qué es simulado** | Los roles (no hay autenticación), los datos personales (sintéticos) y la persistencia (efímera en la nube). |
| **Nombre y alcance** | Se presenta como "Asistente Académico Demo". No usa marca institucional ni se anuncia como solución validada. |

## El problema que aborda

Los estudiantes repiten dudas frecuentes —qué ramos tienen inscritos, qué
prerrequisitos exige una asignatura, qué contenidos o evaluaciones tiene un
programa, si están en alerta académica— que hoy se resuelven consultando varios
documentos o escribiendo a coordinación. Este prototipo explora si un asistente
conversacional puede **orientar de forma inmediata y responsable** sobre esas
preguntas, citando la evidencia disponible y derivando a los canales oficiales
cuando no hay información confiable.

El asistente reconoce el **tipo de pregunta** y responde como guía académica, no
como un buscador que pega fragmentos de PDF. La información es **extractiva**: se
obtiene de los PDF y CSV locales. Cuando un dato no puede extraerse con
seguridad, la aplicación lo declara ("Información no disponible en los documentos
cargados") en lugar de inventarlo.

## Funciones actuales

- **Chat orientado por intención**: distingue saludos, dudas frecuentes y
  consultas académicas, y adapta la respuesta al tipo de pregunta.
- **Consultas académicas** sobre datos sintéticos: ramos inscritos; sede,
  jornada y semestre; alertas básicas según el historial.
- **Guía documental** desde los programas: qué estudiar (unidades y plan),
  contenidos, bibliografía y evaluaciones detectadas.
- **Prerrequisitos**: requisitos de un ramo y su estado según el historial, más
  un mapa completo de prerrequisitos de la malla.
- **Soporte multicarrera**: un selector determina de forma excluyente qué corpus
  se indexa y consulta (Ingeniería Comercial o Ingeniería Civil Industrial).
- **Feedback por respuesta**: bajo cada respuesta, "¿Te sirvió?" con 👍/👎 y un
  comentario opcional.
- **Registro anónimo de interacciones** en SQLite local + **panel de métricas**
  demo (ver [Registro de interacciones y feedback](#registro-de-interacciones-y-feedback)).
- **Roles simulados** (Estudiante / Coordinación demo / Admin demo) para mostrar
  distintas vistas sin autenticación real.

## Arquitectura

```text
   PDFs de programas + manifiestos
                 |
                 v
        ingest.py  (pypdf → fragmentos con solapamiento)
                 |
                 v
   document_chunks.csv  (un corpus por carrera)
                 |
                 v
            app.py / Streamlit
   ├── Índice TF-IDF en memoria (similitud coseno), solo de la carrera activa
   ├── Datos académicos sintéticos (alumnos, malla, historial, prerrequisitos)
   ├── Clasificación de intención → enrutador de respuestas
   ├── Respuesta estructurada + evidencia citada (expander)
   └── Registro anónimo de la interacción → SQLite local (defensivo)
```

Componentes principales:

- **`ingest.py`**: valida manifiestos, extrae texto con `pypdf`, fragmenta con
  solapamiento y genera un `document_chunks.csv` independiente por carrera.
- **`rag/`**: índice TF-IDF y búsqueda por similitud coseno (con una capa opcional
  de embeddings; ver más abajo). No usa OpenAI, Claude, LangChain ni una base
  vectorial externa.
- **`chatbot/`**: clasificación heurística de intención, contrato tipado de
  respuestas y familias de respuesta por tema.
- **`services/`**: carga de CSV, reglas de prerrequisitos y el registro de
  interacciones (`services/interacciones.py`).
- **`ui/`**: componentes, paneles y estilos de Streamlit.

## Datos utilizados

Todos los datos personales son **sintéticos**; la información académica proviene
de programas de asignatura en PDF y CSV locales.

- 18 alumnos sintéticos (8 de Ingeniería Comercial y 10 de Ingeniería Civil
  Industrial);
- 52 ramos por malla curricular;
- 52 programas de asignatura en PDF y 2 documentos de malla;
- ~870 fragmentos indexados en `data/document_chunks.csv` (Comercial) y ~875
  fragmentos para Ingeniería Civil Industrial;
- 1 programa registrado como **pendiente** en ICI (`FIS504`), sin contenido
  inventado.

La malla ICI corresponde a la versión oficial **UDLA 2025** que coincide con los
52 códigos descargados (`pdf/malla/malla_ici_2025.pdf`); no debe confundirse con
versiones posteriores del plan de estudios.

### Prerrequisitos

Se **generan automáticamente** desde los programas indexados con
`scripts/extract_prerrequisitos.py`. El proceso es deliberadamente conservador:
solo crea relaciones hacia ramos que existen en la malla, por código oficial
(confianza alta) o por nombre oficial (confianza media). **Nunca** infiere
prerrequisitos por semestre, posición en la malla ni parecido.

Para los ramos marcados como "No detectado", la aplicación muestra una
advertencia y no infiere ninguna relación. El estado de cada prerrequisito
(Aprobado, Cursando, Reprobado, Pendiente o No aplica) se calcula únicamente con
`data/historial_academico.csv`.

### Contenidos de los programas

La respuesta "¿Qué debería estudiar?" arma una tabla de unidades a partir de la
sección de contenidos del programa. La extracción es **estructural** (basada en el
formato del PDF) y reconoce contenidos en 51 de los 52 ramos; el restante
(`TDE400`) no expone una sección extraíble y se informa como "Información no
disponible". Un documento de malla (`malla_alumno_sistema.pdf`) no tiene texto
extraíble con `pypdf`: la ingesta lo reporta como advertencia y continúa (no se
aplica OCR en esta fase).

## Registro de interacciones y feedback

La aplicación guarda un **registro anónimo** de cada turno de conversación en una
base **SQLite local** (`data/interacciones_demo.db`, ignorada por git; se crea
sola en la primera interacción). Así el proyecto responde de forma concreta a
*«¿dónde quedan guardadas las interacciones?»* sin depender de servicios externos.

### Qué se registra

Tabla `interacciones`:

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

**Feedback:** bajo cada respuesta aparece *«¿Te sirvió esta respuesta?»* con
botones 👍/👎 y un campo opcional; la elección actualiza la fila correspondiente.

**Panel de métricas (demo):** la vista **Coordinación demo** muestra el total de
interacciones, feedback positivo/negativo, consultas que requieren derivación,
preguntas por intención y por carrera, y las últimas 5 preguntas anonimizadas. El
sidebar incluye además un contador rápido en «Estado de la sesión».

### Qué NO se registra

**No** se guarda nombre real, RUT, correo, teléfono ni ningún dato personal
sensible: **no existen columnas** para esa información. El único campo que podría
contener datos escritos por la persona es el texto de la consulta, por lo que la
interfaz muestra un aviso pidiendo no ingresar datos personales sensibles.

El guardado es **defensivo**: si la escritura falla, la aplicación sigue
funcionando y la conversación no se interrumpe. La ruta puede sobrescribirse con
la variable de entorno `CHATBOT_INTERACCIONES_DB` (los tests la usan para no
tocar `data/`).

## Privacidad responsable

- **Datos sintéticos por diseño.** Los perfiles de alumno del demo son ficticios;
  no representan personas reales.
- **Sin recolección de datos personales.** El registro de interacciones es anónimo
  y no incluye identificadores personales.
- **Transparencia en la interfaz.** La aplicación indica que es un demo, que las
  respuestas son orientativas y que las interacciones pueden registrarse de forma
  anónima; pide explícitamente no ingresar datos personales sensibles.
- **No inventa información oficial.** Cuando un dato no puede verificarse con los
  documentos cargados, lo declara y deriva a coordinación o secretaría académica.
- **No subir datos reales a despliegues públicos.** Ver la nota en
  [Despliegue](#despliegue-en-streamlit-community-cloud).
- **Para producción** se debe definir una política de anonimización, retención y
  control de acceso antes de migrar a una base persistente (ver [Roadmap](#roadmap)).

## Instalación y ejecución local

### Requisitos

- Python 3.10 o superior.
- PowerShell para los ejemplos de Windows.

Dependencias de ejecución (`requirements.txt`): Streamlit, pandas, pypdf y
scikit-learn. Las herramientas de test (pytest) están en `requirements-dev.txt`.
No se usa OpenAI/Claude/LangChain/ChromaDB.

### Instalación

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip

# Uso normal (solo ejecutar la app)
python -m pip install -r requirements.txt

# Desarrollo (incluye herramientas de test)
python -m pip install -r requirements-dev.txt
```

### Ejecutar la aplicación

```powershell
python -m streamlit run app.py --server.fileWatcherType none
```

Abre [http://localhost:8501](http://localhost:8501). En la barra lateral, el
selector **Carrera documental** determina de forma excluyente qué corpus se
indexa y consulta.

**Preguntas de prueba:**

- ¿Qué ramos tengo inscritos?
- ¿Cuál es mi sede y jornada?
- ¿Estoy atrasado o tengo alguna alerta?
- ¿Qué debería estudiar para Microeconomía I?
- ¿Qué contenidos tiene Econometría?
- ¿Qué prerrequisitos tiene Microeconomía II?
- ¿Puedo cursar Econometría?
- ¿Cómo se evalúa EIN908?
- ¿Qué contenidos tiene FIS504? *(debe informar que no hay evidencia suficiente)*

La selección opcional de un ramo inscrito en la barra lateral sirve como contexto
cuando la pregunta no menciona una asignatura.

### Pruebas

Con las dependencias de desarrollo instaladas:

```powershell
pytest -q                    # Suite completa
python -m py_compile app.py  # Validación de sintaxis del orquestador
```

La suite cubre clasificación de intención, búsqueda documental, extractores de
programas, reglas de prerrequisitos, contrato tipado de respuestas, registro de
interacciones y la interfaz del chat.

### Búsqueda semántica opcional (embeddings)

La búsqueda usa **TF-IDF** por defecto. Opcionalmente puede activarse una capa de
**embeddings** (modelo local `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`)
que mejora la recuperación semántica, con TF-IDF como *fallback* automático:

```powershell
python -m pip install -r requirements-embeddings.txt
```

- Con la dependencia instalada, el modo `auto` (por defecto) usa embeddings y, si
  el modelo no carga, vuelve a TF-IDF sin romper la aplicación.
- Para **forzar** un motor, define `CHATBOT_BUSQUEDA` con `tfidf`, `embeddings` o
  `auto`. El sidebar indica el motor activo.

> En Streamlit Community Cloud, **no** incluyas `sentence-transformers` en
> `requirements.txt` salvo que aceptes la descarga del modelo (~470 MB) y un mayor
> uso de memoria; el runtime gratuito puede quedar ajustado.

## Despliegue en Streamlit Community Cloud

1. Sube el repositorio a GitHub y entra a *Community Cloud* → **New app**.
2. Selecciona el repositorio y la rama `main`.
3. Indica `app.py` como archivo principal (*Main file path*).
4. Community Cloud instala las dependencias desde `requirements.txt`.
5. La configuración base (`.streamlit/config.toml`) ya está versionada.

La demo usa exclusivamente datos sintéticos incluidos en `data/`. **No subas
datos personales ni información académica real a un despliegue público.**

> **Persistencia efímera.** En Streamlit Community Cloud el sistema de archivos se
> reinicia en cada reinicio o redeploy del contenedor. El registro de
> interacciones (`data/interacciones_demo.db`) persiste durante la ejecución, pero
> **no** de forma duradera. Para conservar métricas hay que migrar a una base
> externa (ver [Roadmap](#roadmap)).

## Operación y mantenimiento (avanzado)

Estas tareas son opcionales: las bases ya vienen incluidas en `data/`.

### Regenerar las bases locales

```powershell
python -u ingest.py                                             # Base documental (Comercial)
python -u ingest.py --carrera ingenieria_civil_industrial       # Corpus ICI
python -u scripts/generar_datos_sinteticos_ici.py               # Capa académica sintética ICI
python -u scripts/extract_prerrequisitos.py                     # Prerrequisitos (Comercial)
python -u scripts/extract_prerrequisitos.py --carrera ingenieria_civil_industrial
```

Los scripts validan sus insumos y **no sobrescriben** el CSV existente si no
logran generar registros.

### Agregar una nueva carrera

Cada carrera vive bajo un `slug` propio y genera un corpus independiente. Crea
`data/carreras/<slug>/pdf/programas/` con los PDFs y
`data/carreras/<slug>/metadata/metadata_programas.csv` con estas columnas:

```csv
carrera,codigo_asignatura,nombre_archivo,ruta_archivo,tipo_documento,estado
Ingeniería en Informática,INF100,INF100.pdf,data/carreras/ingenieria_en_informatica/pdf/programas/INF100.pdf,programa_asignatura,disponible
```

- `estado` solo admite `disponible` o `pendiente`; un ramo pendiente se registra
  en metadata pero no crea PDF ni fragmento ficticio.
- `ruta_archivo` es relativa a la raíz del proyecto.

Reconstruye solo esa carrera con `python -u ingest.py --carrera <slug>`. Al
reiniciar Streamlit, el selector **Carrera documental** la descubre
automáticamente. Para habilitar la ficha estudiantil, agrega bajo `academico/`
los cinco CSV (`alumnos.csv`, `malla.csv`, `ramos_inscritos.csv`,
`historial_academico.csv`, `prerrequisitos.csv`) con una columna `carrera`
consistente.

### Evaluación offline de búsqueda documental

```powershell
python scripts/evaluar_busqueda.py --metodo tfidf
python scripts/evaluar_busqueda.py --metodo auto
python scripts/evaluar_busqueda.py --metodo embeddings
```

Usa las consultas de `eval/consultas_busqueda.csv`, escribe el detalle en
`eval/resultados_busqueda.csv` (ignorado por git) e imprime la precisión de ramo
en el top-1. Si se pide `embeddings`/`auto` sin la dependencia, avisa y continúa
con TF-IDF.

## Estructura del proyecto

```text
chatbot_ingenieria_comercial/
├── app.py                     # Orquestador Streamlit
├── ingest.py                  # Pipeline local de ingesta de PDFs
├── config/                    # Constantes y esquemas de datos
├── utils/                     # Utilidades puras (normalización de texto)
├── services/                  # Carga de CSV, prerrequisitos e interacciones
│   └── interacciones.py       # Registro anónimo SQLite (demo)
├── rag/                       # Índice TF-IDF, búsqueda y extractores de PDF
├── chatbot/                   # Clasificación, contrato tipado y respuestas
│   ├── intenciones.py         # Clasificación heurística de consultas
│   ├── contratos.py           # RespuestaChatbot / SeccionRespuesta / Evidencia
│   ├── conversacion.py        # Estado de sesión y flujo conversacional
│   └── respuestas/            # Enrutador y respuestas por tema
├── ui/                        # Componentes, paneles y estilos de Streamlit
├── tests/                     # Suite de pytest
├── scripts/                   # Ingesta auxiliar, extracción y evaluación
├── docs/                      # roadmap.md y arquitectura_datos.md
├── data/                      # CSV, PDFs y bases locales (por carrera)
└── assets/                    # Logos institucionales
```

## Limitaciones actuales

- **Sin modelo generativo**: las respuestas son extractivas y estructuradas a
  partir del PDF y los CSV, no una síntesis semántica avanzada.
- La extracción de contenidos, bibliografía y evaluaciones depende del formato del
  programa; puede quedar incompleta y, cuando no hay estructura reconocible, se
  informa como no disponible.
- El umbral TF-IDF es heurístico y puede requerir calibración.
- **Sin OCR** para PDFs escaneados o basados solo en imágenes.
- Los prerrequisitos "No detectado" requieren revisión manual contra el programa
  oficial.
- Las alertas son orientativas y no reemplazan sistemas ni reglamentos oficiales.
- **Sin autenticación real** (los roles son simulados).
- La persistencia de interacciones usa SQLite local y es **efímera** en Streamlit
  Community Cloud; no sustituye a una base institucional gobernada.

## Roadmap

Etapas propuestas, ordenadas de menor a mayor complejidad y riesgo. Ninguna está
implementada como producto; se listan como dirección de trabajo. El detalle está
en [`docs/roadmap.md`](docs/roadmap.md) y la propuesta de modelo de datos en
[`docs/arquitectura_datos.md`](docs/arquitectura_datos.md).

1. **Base documental validada** — revisar programas y prerrequisitos contra
   fuentes oficiales; completar los ramos "No detectado".
2. **Mejora de interfaz** — refinar la experiencia del chat, los paneles y la
   accesibilidad.
3. **Métricas persistentes** — conservar el registro de interacciones más allá de
   una sesión efímera.
4. **Feedback avanzado** — motivos categorizados, seguimiento y reportes de
   utilidad.
5. **Base externa segura** — migrar a PostgreSQL / Supabase (u hoja de cálculo
   institucional gobernada) con control de acceso y retención definida.
6. **Integración WhatsApp** — canal conversacional adicional, con consentimiento y
   backend persistente.
7. **ML / analítica de patrones** — clasificación aprendida y tableros agregados
   de uso sobre datos anónimos.

## Uso académico responsable

Este repositorio es un **prototipo demostrativo** que opera **solo con datos
sintéticos y archivos locales**. **No reemplaza la información oficial de la
coordinación académica ni del sistema de registro académico de la universidad.**
Toda recomendación debe contrastarse con los programas completos, la malla oficial
y la orientación académica institucional. La aplicación no inventa información:
cuando un dato no puede extraerse con seguridad, lo declara explícitamente.
