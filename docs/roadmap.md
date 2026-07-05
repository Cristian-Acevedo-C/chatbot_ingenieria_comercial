# Roadmap institucional

Estado del proyecto: **demo institucional** con datos sintéticos/locales. Este
roadmap ordena posibles etapas futuras, de menor a mayor complejidad y riesgo.
Ninguna está implementada todavía; se listan como propuesta.

## 1. Piloto con datos anonimizados
- Reemplazar los datos sintéticos por un extracto **anonimizado** real (sin datos
  personales identificables).
- Definir política de anonimización y retención antes de cargar cualquier dato.

## 2. Panel de carga de programas
- Interfaz para subir PDFs de programas y regenerar `document_chunks.csv` desde la
  app (hoy es un script manual, `ingest.py`).
- Validación de formato y trazabilidad de páginas.

## 3. Base de datos real
- Migrar de CSV a SQLite/PostgreSQL siguiendo `docs/arquitectura_datos.md`.
- Integridad referencial, consultas agregadas y `consultas_log` anónimo.

## 4. Roles reales (autenticación)
- Sustituir los roles simulados (Estudiante / Coordinación demo / Admin demo) por
  autenticación real y autorización por perfil.
- Auditoría de accesos.

## 5. Integración WhatsApp
- Canal conversacional adicional, respetando privacidad y consentimiento.
- Requiere backend persistente y gestión de sesiones.

## 6. Analítica institucional
- Tableros agregados de uso (intenciones frecuentes, ramos consultados, cobertura),
  siempre sobre datos anónimos.

---

> Prioridad recomendada: **1 → 2 → 3** antes de cualquier canal externo o rol real.
> La estabilidad, la privacidad y la calidad de los datos van primero.
