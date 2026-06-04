## Context

Este change implementa el módulo de **Padrón de Alumnos** — la base para todos los módulos posteriores del flujo central (calificaciones, atrasados, comunicaciones). Depende de **C-07** (usuarios y asignaciones) porque las entradas del padrón referencian `usuario_id` y operan sobre materias/cohortes ya existentes.

Actualmente no existe ningún mecanismo de padrón. Este módulo introduce:
- Modelo versionado (`VersionPadron` → `EntradaPadron`) con activación única por materia×cohorte.
- Importación manual (.xlsx/.csv) con vista previa.
- Integración automática via Moodle Web Services.
- Endpoint para vaciar datos de una materia (F1.5, RN-04).

## Goals / Non-Goals

**Goals:**
- Crear los modelos `VersionPadron` y `EntradaPadron` con versionado completo.
- Implementar importación manual (xlsx/csv) con detección de columnas y vista previa antes de confirmar.
- Implementar cliente Moodle Web Services para sincronización on-demand y nocturna.
- Endpoint para consultar el padrón activo de una materia×cohorte.
- Endpoint para vaciar datos de materia con su debida auditoría.
- Registrar auditoría con código `PADRON_CARGAR`.
- Proteger endpoints con permiso `padron:importar`.

**Non-Goals:**
- No se implementa la sincronización nocturna automática (solo el cliente y el endpoint on-demand; el scheduler se define en C-12 o cambio de infraestructura).
- No se implementa UI frontend (eso va en C-22/C-23).
- No se implementan calificaciones ni análisis (C-10, C-11).

## Decisions

### D1 — Versionado explícito vs. reemplazo directo
**Decisión**: modelo versionado con `VersionPadron.activa` booleano. Cada importación crea una nueva `VersionPadron`; al activar la nueva, la anterior se desactiva automáticamente en la misma transacción. Esto preserva histórico completo (supuesto base §3 del modelo de datos) y permite auditoría.
**Alternativa rechazada**: reemplazo directo (UPDATE sobre la misma versión). Se descarta porque perdería la trazabilidad de cambios, violando el principio "todo audita".
**Alternativa rechazada**: soft-delete de la versión anterior. No es necesario porque `activa = false` es semánticamente correcto (la versión existe pero no está vigente).

### D2 — Integración Moodle WS como adaptador
**Decisión**: cliente Moodle WS encapsulado en `integrations/moodle_ws.py` como clase `MoodleWSClient` que recibe configuración por tenant (URL + token). Implementa método `sync_padron(materia_id, cohorte_id)` que retorna datos normalizados. Los errores de conexión se mapean a HTTP 502 con metadata de reintento.
**Fundamento**: aislar la lógica de integración del core de negocio. Si Moodle cambia su API, solo se modifica este archivo. Si Moodle no responde, el sistema cae gracefulmente al fallback manual.
**Alternativa rechazada**: integrar la lógica WS directamente en el Service de padrón. Se descarta porque mezcla responsabilidades (transporte + negocio).

### D3 — Import xlsx/csv con pipeline de dos pasos (preview → confirm)
**Decisión**: el endpoint `POST /api/padron/importar` acepta el archivo, lo parsea, detecta columnas (nombre, apellido, email, comisión) y devuelve una vista previa con metadatos (cantidad de filas, columnas detectadas, duplicados potenciales). El usuario confirma con un segundo llamado que incluye un `preview_token` (hash del contenido) para asegurar idempotencia.
**Fundamento**: evitar importaciones accidentales. El preview es mandatorio antes de persistir.
**Librería**: `openpyxl` para xlsx, `csv` estándar para csv.

### D4 — Vaciar datos con verificación de permiso y auditoría
**Decisión**: `DELETE /api/padron/{materia_id}/vaciar` desactiva todas las versiones activas de la materia (soft-delete lógico marcando `activa = false`) y limpia las calificaciones asociadas. Solo el PROFESOR de esa materia o COORDINADOR/ADMIN pueden ejecutarlo. Genera audit `PADRON_VACIAR`.
**Regla RN-04**: no afecta otras materias ni datos de otros docentes.

### D5 — Permiso `padron:importar` con scope
**Decisión**: permiso `padron:importar` con scope `(propio)` para PROFESOR (solo sus materias asignadas) y scope global para COORDINADOR/ADMIN. Se reusa la lógica de resolución de permisos de C-04.

## Risks / Trade-offs

- **[Riesgo] Dependencia de Moodle WS puede fallar**: si Moodle está caído, la sincronización automática falla → el sistema cae a importación manual. **Mitigación**: el fallback manual siempre está disponible. Timeout configurable y reintento con backoff.
- **[Riesgo] Archivos xlsx mal formados**: usuarios pueden subir archivos con estructura inesperada. **Mitigación**: validación estricta de columnas esperadas, errores descriptivos, vista previa obligatoria antes de confirmar.
- **[Riesgo] Versión activa por materia×cohorte**: si dos usuarios importan simultáneamente, puede haber race condition. **Mitigación**: transacción atómica que verifica y desactiva versiones anteriores dentro de la misma operación. Optimistic locking opcional.
- **[Trade-off] Preview_token como hash de contenido**: asegura idempotencia pero no evita que el archivo original cambie entre preview y confirm. **Aceptado**: es un riesgo bajo porque el preview_token incluye el hash del contenido completo; si cambia, el confirm rechaza.
