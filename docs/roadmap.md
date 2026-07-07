# Roadmap

Estado del proyecto: **demo/piloto** con datos sintéticos/locales. Este roadmap
ordena posibles etapas futuras, de menor a mayor complejidad y riesgo. Salvo lo
indicado como "ya implementado", ninguna es un producto validado; se listan como
dirección de trabajo.

## Ya implementado en el demo

- **Registro anónimo de interacciones** en SQLite local
  (`services/interacciones.py`, tabla `interacciones`): pregunta, respuesta,
  intención, carrera, fuente y necesidad de derivación, sin datos personales.
- **Feedback por respuesta** (👍/👎 + comentario opcional) que actualiza la fila
  correspondiente.
- **Panel de métricas demo** en la vista Coordinación demo (totales, feedback,
  derivaciones, distribución por intención/carrera, últimas preguntas).

> Limitación conocida: en Streamlit Community Cloud el almacenamiento es efímero.
> La etapa 3 aborda su persistencia real.

## 1. Base documental validada

- Revisar programas y prerrequisitos contra fuentes oficiales.
- Completar o corregir los ramos marcados como "No detectado".
- Trazabilidad de páginas y versión de malla usada.

## 2. Mejora de interfaz

- Refinar la experiencia del chat, los paneles y la accesibilidad.
- Pulir textos, estados vacíos y mensajes de derivación.

## 3. Métricas persistentes

- Conservar el registro de interacciones más allá de una sesión efímera.
- Definir política de **retención** y limpieza antes de persistir.

## 4. Feedback avanzado

- Motivos categorizados (información incompleta, no era lo que buscaba, etc.).
- Seguimiento y reportes de utilidad por intención y por carrera.

## 5. Base externa segura

- Migrar de CSV/SQLite local a **PostgreSQL / Supabase** (u hoja de cálculo
  institucional gobernada) siguiendo `docs/arquitectura_datos.md`.
- Control de acceso, integridad referencial y consultas agregadas.

## 6. Integración WhatsApp

- Canal conversacional adicional, respetando privacidad y consentimiento.
- Requiere backend persistente y gestión de sesiones.

## 7. ML / analítica de patrones

- Clasificación de intención aprendida (en vez de solo heurística).
- Tableros agregados de uso, siempre sobre datos anónimos.

---

> Prioridad recomendada: **1 → 2 → 3** antes de cualquier canal externo, rol real
> o componente de ML. La calidad de los datos, la privacidad y la estabilidad van
> primero.
