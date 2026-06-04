## Why

El sistema actual no tiene un mecanismo para importar, versionar y mantener el padrón de alumnos por materia y cohorte. Sin un padrón confiable, los módulos posteriores (calificaciones, análisis de atrasados, comunicaciones) no tienen la base de alumnos sobre la cual operar. Además, la integración con Moodle Web Services permitirá automatizar la sincronización, reduciendo la carga manual del docente/coordinador.

Este change es el **C-09** del roadmap y depende de **C-07** (usuarios y asignaciones), ya que las entradas del padrón referencian `usuario_id` y operan dentro del contexto de materias y cohortes ya existentes.

## What Changes

1. **Modelos de dominio `VersionPadron` y `EntradaPadron`** — versionado completo: cada importación crea una nueva versión; al activar la nueva, la anterior se desactiva automáticamente. Conserva histórico completo.
2. **Importación manual de padrón** — endpoint que acepta archivos `.xlsx` y `.csv` con detección de columnas y vista previa antes de confirmar (F1.3, F1.4).
3. **Integración con Moodle Web Services** — cliente dedicado en `integrations/moodle_ws.py` para sincronización on-demand y nocturna de usuarios/actividades. Fallback a importación manual si Moodle no responde.
4. **Vaciar datos de materia** — endpoint para limpiar calificaciones y datos de ingesta de una materia (F1.5, RN-04), sin afectar otras materias.
5. **Auditoría** — código `PADRON_CARGAR` registrado en el log de auditoría (E-AUD).
6. **Rutas y permisos** — endpoints bajo `/api/padron/*` con guard `padron:importar`.
7. **Workflow post-implementación** — luego del verify exitoso, se listarán tests manuales en el chat para validación humana, y se actualizará el manifest.json vía Engram sync.

## Capabilities

### New Capabilities
- `padron-ingesta`: Capacidad de importar, versionar y consultar el padrón de alumnos por materia × cohorte. Incluye soporte manual (xlsx/csv) e integración automática vía Moodle Web Services.
- `integracion-moodle-ws`: Cliente para sincronización con Moodle via Web Services con reintentos y mapeo de errores a 502.

### Modified Capabilities
- *(ninguna — es el primer módulo que consume el padrón)*

## Impact

- **Modelos nuevos**: `VersionPadron`, `EntradaPadron` — migración Alembic nueva.
- **Nuevo archivo**: `integrations/moodle_ws.py` — cliente dedicado de Moodle WS.
- **Nuevos endpoints**: `POST /api/padron/importar` (vista previa + confirmar), `GET /api/padron/{materia_id}/{cohorte_id}` (consultar vigente), `DELETE /api/padron/{materia_id}/vaciar` (F1.5).
- **Permiso nuevo**: `padron:importar` para proteger los endpoints.
- **Dependencia externa**: Moodle Web Services URL + token por tenant (configuración).
- **Engram**: luego del verify, se actualizará el manifest.json vía Engram Sync Import.
- **Tests manuales**: se listarán en el chat luego del verify exitoso, antes del archive.
