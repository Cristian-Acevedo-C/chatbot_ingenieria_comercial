# Arquitectura de datos — estado actual y propuesta SQLite

> **Estado:** propuesta. El backend activo de la aplicación **sigue siendo CSV**
> (`data/*.csv` cargados con pandas y cacheados por Streamlit). Este documento
> describe un modelo relacional futuro para una eventual migración; no cambia el
> comportamiento actual.

## Backend activo (hoy)

- Archivos planos en `data/` (`alumnos.csv`, `malla.csv`, `ramos_inscritos.csv`,
  `historial_academico.csv`, `prerrequisitos.csv`, `document_chunks.csv`).
- Ventajas para el MVP: cero infraestructura, versionable, fácil de inspeccionar.
- Límite: sin integridad referencial, sin concurrencia, sin consultas agregadas
  eficientes.

## Modelo relacional propuesto (SQLite demo)

Diseño mínimo, normalizado y anonimizable. Los tipos son indicativos.

### `carreras`
| Campo | Tipo | Notas |
|---|---|---|
| id | INTEGER PK | |
| nombre | TEXT | p. ej. "Ingeniería Comercial" |

### `alumnos`
| Campo | Tipo | Notas |
|---|---|---|
| id_alumno | TEXT PK | identificador sintético |
| nombre | TEXT | sintético |
| carrera_id | INTEGER FK → carreras.id | |
| sede | TEXT | |
| jornada | TEXT | |
| semestre_actual | INTEGER | |

### `ramos`
| Campo | Tipo | Notas |
|---|---|---|
| codigo_ramo | TEXT PK | código oficial |
| nombre_ramo | TEXT | |
| semestre | INTEGER | posición en la malla |
| creditos | INTEGER | |

### `inscripciones`
| Campo | Tipo | Notas |
|---|---|---|
| id | INTEGER PK | |
| id_alumno | TEXT FK → alumnos | |
| codigo_ramo | TEXT FK → ramos | |
| estado | TEXT | Inscrito / Cursando |

### `historial`
| Campo | Tipo | Notas |
|---|---|---|
| id | INTEGER PK | |
| id_alumno | TEXT FK → alumnos | |
| codigo_ramo | TEXT FK → ramos | |
| estado | TEXT | Aprobado / Reprobado / Cursando |
| nota | REAL | |

### `prerrequisitos`
| Campo | Tipo | Notas |
|---|---|---|
| id | INTEGER PK | |
| codigo_ramo | TEXT FK → ramos | ramo que exige el requisito |
| codigo_prerrequisito | TEXT FK → ramos | puede ser vacío |
| tipo | TEXT | Prerrequisito / Sin prerrequisito / No detectado |
| confianza | TEXT | Alta / Media |
| fuente_archivo | TEXT | trazabilidad al PDF |

### `document_chunks`
| Campo | Tipo | Notas |
|---|---|---|
| chunk_id | TEXT PK | |
| codigo_ramo | TEXT FK → ramos | |
| tipo_documento | TEXT | |
| ruta_archivo | TEXT | |
| texto | TEXT | fragmento indexado |

### `consultas_log` (anonimizado)
| Campo | Tipo | Notas |
|---|---|---|
| id | INTEGER PK | |
| timestamp | TEXT | ISO-8601 |
| intencion | TEXT | clasificación detectada |
| codigo_ramo | TEXT | sin datos personales |
| motor | TEXT | tfidf / embeddings |
| tuvo_evidencia | INTEGER | 0/1 |

> **Privacidad:** `consultas_log` es explícitamente anónimo (no guarda `id_alumno`
> ni texto libre del usuario). Su objetivo es analítica agregada de uso.

## Cómo generar la base demo (opcional)

```powershell
python scripts/crear_sqlite_demo.py
```

Crea `data/asistente_academico_demo.db` (ignorado por git) importando los CSV
existentes. **No** modifica la aplicación: es material de propuesta para una
migración futura. Ver `docs/roadmap.md`.
